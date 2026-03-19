import os
import asyncio
from typing import List, Dict, Any, Optional

try:
    from tavily import TavilyClient  # type: ignore
except Exception:  # graceful import
    TavilyClient = None  # type: ignore

# Preferred legal domains (Turkey) - varsayılan tam liste
DEFAULT_LEGAL_SOURCES = [
    "mevzuat.gov.tr",           # Resmi mevzuat portalı
    "resmigazete.gov.tr",       # Resmî Gazete
    "yargitay.gov.tr",          # Yargıtay duyurular/kararlar
    "danistay.gov.tr",          # Danıştay
    "kararara.com",             # Karar arşivi (ikincil)
    "lexpera.com.tr",           # Lexpera (özetler - bazıları ücretli olabilir)
    "hukukmedeniyeti.org",      # Makaleler (ikincil)
]

# Kısa (concise) mod için: sadece birincil resmi/yetkili kaynaklar.
# Mevzuat, Resmî Gazete, Yargıtay, Danıştay — ikincil/blog siteler hariç.
# Bu set: hız için küçük (max 4 sonuç), doğruluk için resmi kaynaklara odaklanır.
CONCISE_LEGAL_SOURCES = [
    "mevzuat.gov.tr",           # Türkiye mevzuat veritabanı — tebliğler, kanunlar, yönetmelikler
    "resmigazete.gov.tr",       # Resmî Gazete — yayımlanan tebliğ/karar metinleri
    "yargitay.gov.tr",          # Yargıtay içtihat ve duyuruları
    "danistay.gov.tr",          # Danıştay kararları (idare hukuku)
]

# ---------------------------------------------------------------------------
# HUKUK ALANI TESPİTİ VE DİNAMİK DOMAIN SEÇİMİ
# ---------------------------------------------------------------------------
# Problem: Tüm sorgulamalarda danistay.gov.tr dahil edilince aile/ticaret/ceza
# hukuku sorularında Danıştay idare mahkemesi kararları alakasız sonuç olarak
# dönüyor. Çözüm: Sorgudan hukuk alanını tespit et, uygun domain setini kullan.

_DOMAIN_SETS_BY_AREA: Dict[str, List[str]] = {
    # Fikri mülkiyet / FSEK → Danıştay hariç (FSEK Yargıtay yetki alanı)
    "fikir": [
        "mevzuat.gov.tr",
        "resmigazete.gov.tr",
        "yargitay.gov.tr",
        "kararara.com",
        "lexpera.com.tr",
    ],
    # Medeni hukuk (aile, kira, miras, borçlar) → Danıştay hariç
    "aile": [
        "mevzuat.gov.tr",
        "resmigazete.gov.tr",
        "yargitay.gov.tr",
        "kararara.com",
        "lexpera.com.tr",
        "hukukmedeniyeti.org",
    ],
    # İdare hukuku → Danıştay dahil, Yargıtay/kararara daha az
    "idare": [
        "mevzuat.gov.tr",
        "resmigazete.gov.tr",
        "danistay.gov.tr",
        "lexpera.com.tr",
        "hukukmedeniyeti.org",
    ],
    # Ticaret hukuku → Danıştay hariç
    "ticaret": [
        "mevzuat.gov.tr",
        "resmigazete.gov.tr",
        "yargitay.gov.tr",
        "kararara.com",
        "lexpera.com.tr",
    ],
    # Ceza hukuku → Danıştay hariç
    "ceza": [
        "mevzuat.gov.tr",
        "resmigazete.gov.tr",
        "yargitay.gov.tr",
        "kararara.com",
        "lexpera.com.tr",
    ],
    # İş hukuku → Danıştay hariç
    "is": [
        "mevzuat.gov.tr",
        "resmigazete.gov.tr",
        "yargitay.gov.tr",
        "kararara.com",
        "lexpera.com.tr",
    ],
    # Varsayılan: tam liste
    "default": DEFAULT_LEGAL_SOURCES,
}

# Hukuk alanı tespiti için anahtar kelimeler
# Her anahtar kelimenin ağırlığı: özel/bağlama özgü terimler daha yüksek ağırlık taşıyor.
# Değer 1 = normal, 2 = güçlü sinyal
_AREA_KEYWORDS: Dict[str, List[tuple]] = {
    "fikir": [
        ("fikir hırsızlığı", 2), ("eser hakkı", 2), ("telif hakkı", 2), ("fsek", 2),
        ("fikri mülkiyet", 2), ("bilgisayar programı", 2), ("yazılım eser", 2),
        ("mali hak", 2), ("manevi hak", 2), ("tecavüzün tespiti", 2),
        ("eser sahibi", 2), ("mali hakka tecavüz", 2), ("haksız rekabet", 1),
        ("marka ihlali", 2), ("patent", 2), ("faydalı model", 2), ("tasarım tescil", 2),
        ("fikir sanat eserleri", 2), ("telif", 1), ("yazılım", 1), ("kaynak kod", 2),
    ],
    "aile": [
        ("boşanma", 2), ("evlilik", 2), ("ziynet", 2), ("velayet", 2), ("nafaka", 2),
        ("mal rejimi", 2), ("aile konutu", 2), ("nişan bozma", 2), ("çeyiz", 2),
        ("miras", 1), ("mirasçı", 2), ("mirasbırakan", 2), ("veraset", 2),
        ("kira", 1), ("kiracı", 1), ("kiralayan", 1), ("tahliye", 1), ("kira artış", 2),
        ("aile", 1), ("eş", 1), ("çocuk", 1), ("düğün", 1), ("takı", 1), ("altın", 1),
    ],
    "idare": [
        ("idare mahkemesi", 2), ("danıştay", 2), ("yürütmenin durdurulması", 2),
        ("kamulaştırma", 2), ("ihale", 2), ("memur disiplin", 2), ("idari para cezası", 2),
        ("belediye encümeni", 2), ("imar planı", 2), ("ruhsat iptali", 2),
        ("idare", 1), ("belediye", 1), ("vergi", 1), ("idari", 1), ("yönetmelik", 1),
        ("kamu", 1), ("memur", 1), ("sicil", 1), ("ruhsat", 1), ("izin", 1), ("lisans", 1),
        ("tebliğ", 1), ("bakanlık", 1), ("sağlık tesisi", 2), ("hasta hakları", 2),
        ("hizmet yönetmeliği", 2), ("idari kurul", 2),
    ],
    "ticaret": [
        ("anonim şirket", 2), ("limited şirket", 2), ("iflas", 2), ("konkordato", 2),
        ("kıymetli evrak", 2), ("poliçe", 2), ("franchise", 2),
        ("şirket", 1), ("ticaret", 1), ("ticari", 1), ("çek", 1), ("senet", 1),
        ("pay", 1), ("hisse", 1), ("ortaklık", 1), ("ticari iş", 2),
    ],
    "ceza": [
        ("ağır ceza", 2), ("müessir fiil", 2), ("kasten yaralama", 2),
        ("kasten öldürme", 2), ("güveni kötüye kullanma", 2), ("dolandırıcılık", 2),
        ("suç", 1), ("ceza", 1), ("hapis", 1), ("hırsız", 1), ("yaralama", 1),
        ("öldürme", 1), ("tehdit", 1), ("hakaret", 1), ("iftira", 1), ("sahtecilik", 1),
        ("uyuşturucu", 1), ("silah", 1), ("zorla", 1), ("kovuşturma", 1),
        ("beraat", 1), ("mahkumiyet", 1), ("savcı", 1),
    ],
    "is": [
        ("kıdem tazminatı", 2), ("ihbar tazminatı", 2), ("iş akdi feshi", 2),
        ("sendika", 2), ("toplu iş sözleşmesi", 2), ("iş kazası", 2),
        ("işçi", 1), ("iş hukuku", 2), ("işveren", 1), ("çalışan", 1),
        ("mesai", 1), ("sgk", 1), ("iş akdi", 1), ("fesih", 1), ("ücret", 1), ("işyeri", 1),
    ],
}


def detect_law_area(query: str) -> str:
    """Sorgu metninden hukuk alanını tespit et — ağırlıklı skor kullanır.

    Her anahtar kelimenin (keyword, ağırlık) çifti vardır.
    Eşit skor durumunda 'default' döner (ambiguity → geniş domain seti).

    Returns:
        'aile' | 'idare' | 'ticaret' | 'ceza' | 'is' | 'default'
    """
    q = query.lower()
    scores: Dict[str, int] = {area: 0 for area in _AREA_KEYWORDS}
    for area, kw_list in _AREA_KEYWORDS.items():
        for kw, weight in kw_list:
            if kw in q:
                scores[area] += weight

    best_score = max(scores.values())
    if best_score == 0:
        return "default"

    # Birden fazla alan aynı en yüksek skoru taşıyorsa belirsizlik → default
    winners = [area for area, sc in scores.items() if sc == best_score]
    if len(winners) > 1:
        return "default"

    return winners[0]


def get_domains_for_area(law_area: str) -> List[str]:
    """Hukuk alanına göre uygun Tavily domain listesi döndür.

    Örnek: 'aile' → Danıştay hariç medeni hukuk siteleri
    """
    return _DOMAIN_SETS_BY_AREA.get(law_area, DEFAULT_LEGAL_SOURCES)


class WebContextFetcher:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.enabled = TavilyClient is not None and bool(self.api_key)
        self.client = TavilyClient(self.api_key) if self.enabled else None

    async def asearch(
        self,
        query: str,
        *,
        domains: Optional[List[str]] = None,
        max_results: int = 8,
        include_answer: bool = True,
        include_images: bool = False,
        search_depth: str = "advanced",
        days: Optional[int] = 3650,  # ~10 yıl
        min_score: float = 0.0,      # 0.0 = filtre yok; 0.35 = düşük alakalı at
        law_area: Optional[str] = None,  # Otomatik domain seçimi için
    ) -> Dict[str, Any]:
        """Async wrapper around Tavily search.

        Yeni parametreler:
          min_score: Bu değerin altındaki Tavily sonuçları filtrelenir.
          law_area: Belirtilirse uygun domain seti otomatik seçilir (domains override etmez).

        Returns empty structure if disabled or errors occur.
        """
        if not self.enabled:
            return {"enabled": False, "results": [], "answer": None}

        # Domain seçimi: açık domains > law_area tabanlı > varsayılan
        if domains is None:
            if law_area:
                domains = get_domains_for_area(law_area)
            else:
                domains = DEFAULT_LEGAL_SOURCES

        # Tavily client is sync; run in thread
        loop = asyncio.get_running_loop()
        try:
            def _run():
                return self.client.search(
                    query=query,
                    include_answer=include_answer,
                    include_images=include_images,
                    include_raw_content=True,  # Tam sayfa içeriği - snippet yetmez
                    max_results=max_results,
                    search_depth=search_depth,
                    days=days,
                    include_domains=domains,
                )
            data = await loop.run_in_executor(None, _run)
            # Normalize results list
            items = []
            filtered_count = 0
            for r in data.get("results", []) or []:
                score = r.get("score") or 0.0
                # Skor filtresi: min_score > 0 ise düşük alakalı sonuçları atla
                if min_score > 0 and isinstance(score, (int, float)) and score < min_score:
                    filtered_count += 1
                    print(f"🔍 [WebContext] Düşük skor ({score:.3f} < {min_score}) → atlandı: {r.get('url', '')[:60]}")
                    continue
                # raw_content: tam sayfa metni — hukuki belgelerde kritik bilgi
                # (süreler, oranlar, koşullar) metnin derinlerinde olabileceğinden
                # KRIPILMADAN tam metin olarak alınır — AI tam içeriğe erişsin
                raw = (r.get("raw_content") or "").strip()
                items.append({
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": r.get("content"),
                    "raw_content": raw,
                    "score": score,
                })
            if filtered_count:
                print(f"🔍 [WebContext] {filtered_count} sonuç düşük skor nedeniyle filtrelendi (min_score={min_score})")
            return {
                "enabled": True,
                "answer": data.get("answer"),
                "query": query,
                "results": items,
                "used_domains": domains,
                "law_area": law_area or "default",
            }
        except Exception as e:
            return {"enabled": False, "error": str(e), "results": [], "answer": None}

    @staticmethod
    def build_law_query(user_question: str, case_summary: str = "") -> str:
        base = user_question.strip()
        if case_summary:
            base += " " + case_summary[:300]
        # Domain filtreleme include_domains parametresiyle yapılıyor;
        # site: operatörü ekleme - Tavily semantic search'ünü bozuyor
        return base

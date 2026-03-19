#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5 Sentetik Hukuk Sorusu — Tam Pipeline Testi
Her soru için:
  - Bedesten emsal çekimi
  - Pinecone semantik arama
  - AI cevap üretimi (tam context ile)
  - Emsal kullanım analizi
  - Doğruluk ve kalite değerlendirmesi
"""
import asyncio
import os
import sys
import time
import re
import json
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "yargi_gpt5_tavil_final_part_Final"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "yargi_gpt5_tavil_final_part_Final", ".env"))

# ──────────────────────────────────────────────────────────────────────
# 5 SENTETİK HUKUK SORUSU + BEKLENEN CEVAP (uzman bilgisiyle)
# ──────────────────────────────────────────────────────────────────────
SORULAR = [
    {
        "no": 1,
        "soru": "İşçinin haklı nedenle iş sözleşmesini feshetmesi halinde kıdem tazminatına hak kazanır mı? Hangi haklı nedenler geçerlidir?",
        "alan": "İş Hukuku",
        "beklenen": (
            "İŞÇİNİN HAKLI NEDENLE FESHİ VE KIDEM TAZMİNATI\n\n"
            "1) Temel Kural: İşçinin haklı nedenle feshi kıdem tazminatına hak kazandırır.\n"
            "   - 1475 sayılı İş Kanunu md.14 ve 4857 sayılı İş Kanunu md.24'e göre işçi haklı nedenle "
            "feshederse kıdem tazminatı alır.\n\n"
            "2) Haklı Fesih Nedenleri (İK md.24):\n"
            "   a) Sağlık Nedenleri: İşin işçinin sağlığını veya yaşam koşullarını tehdit etmesi\n"
            "   b) Ahlak ve İyiniyet Kurallarına Aykırılık:\n"
            "      - Yanıltma, cinsel taciz, saldırı, işçinin şeref/namusuna dokunma\n"
            "      - Ücretin ödenmemesi, fazla çalışma parasının verilmemesi\n"
            "      - Zorunlu çalışma saatlerini aşmak için zorlamak\n"
            "   c) Zorlayıcı Nedenler: 1 haftadan fazla süren işyeri durması\n\n"
            "3) Önemli Koşullar:\n"
            "   - Derhal fesih süresi: Ahlak ihlallerinde 6 iş günü (öğrenme), 1 yıl mutlak süre\n"
            "   - En az 1 yıl çalışmış olmak\n"
            "   - İhbar tazminatı hakkı yoktur (kıdem tazminatı vardır)\n\n"
            "4) Emsal: Yargıtay 9. HD kararlarında ücret ödenmemesi, mobbing, sağlık koşullarının "
            "bozulması tutarlı şekilde haklı fesih kabul edilmektedir."
        ),
    },
    {
        "no": 2,
        "soru": "Kat mülkiyetinde ortak alanların kullanımına ilişkin anlaşmazlıklarda hangi hukuki yollar mevcuttur ve kat malikleri kurulunun kararlarına nasıl itiraz edilir?",
        "alan": "Kat Mülkiyeti Hukuku",
        "beklenen": (
            "KAT MÜLKİYETİNDE ORTAK ALAN ANLAŞMAZLIKLARI\n\n"
            "1) Hukuki Dayanak: 634 sayılı Kat Mülkiyeti Kanunu\n\n"
            "2) Başvurulabilecek Yollar:\n"
            "   a) Kat Malikleri Kuruluna Başvuru: Kurulun toplanması, karar alması talep edilebilir\n"
            "   b) Yöneticiye Bildirim: Yönetici eliyle ihlal durdurulabilir\n"
            "   c) Sulh Hukuk Mahkemesi: Kat mülkiyeti davaları sulh hukuk mahkemesinde görülür\n"
            "   d) İhtiyati Tedbir: Acil durumlarda tedbir kararı istenebilir\n\n"
            "3) Kat Malikleri Kurulu Kararına İtiraz:\n"
            "   - KMK md.33: Karara katılmayan maliklerin 1 ay içinde sulh hukuk mahkemesine "
            "iptal davası açma hakkı\n"
            "   - Yoklukta alınan kararlara itiraz: öğrenme tarihinden itibaren 1 ay\n\n"
            "4) Önemli Noktalar:\n"
            "   - Toplantı yeter sayısı: 1/2+1 aranan kararlar için 2/3 çoğunluk\n"
            "   - Özel nisap isteyen kararlar: oy birliği (bağımsız bölüm sayısı ve arsa payı)"
        ),
    },
    {
        "no": 3,
        "soru": "Trafik kazası nedeniyle maddi ve manevi tazminat davası açmak isteyen mağdurun izlemesi gereken hukuki süreç nedir? Zamanaşımı süreleri ve zorunlu arabuluculuk uygulanır mı?",
        "alan": "Haksız Fiil / Trafik Hukuku",
        "beklenen": (
            "TRAFİK KAZASI TAZMİNAT DAVASI SÜRECİ\n\n"
            "1) Hukuki Dayanak: BK md.49 (haksız fiil), 2918 sayılı KTK, Sigortacılık Kanunu\n\n"
            "2) Hukuki Yollar:\n"
            "   a) Sigorta Şirketine Başvuru: Zorunlu trafik sigortası kapsamında şirkete başvuru "
            "(sigorta şirketi 15 gün içinde yanıt vermezse ret sayılır)\n"
            "   b) Güvence Hesabı: Sigortasız araç, kaçan araç için\n"
            "   c) Dava: Asliye Hukuk / Sulh Hukuk (2020'den itibaren Asliye Hukuk)\n\n"
            "3) Zamanaşımı:\n"
            "   - Genel: 2 yıl (zararın ve failin öğrenilmesinden), mutlak 10 yıl\n"
            "   - Cezayı gerektiriyorsa: ceza zamanaşımı uygulanır (daha uzun)\n\n"
            "4) Arabuluculuk:\n"
            "   - Ticari davalar hariç, trafik kazası maddi tazminat davalarında 01.01.2019'dan "
            "itibaren zorunlu arabuluculuk uygulanır (7036 sayılı Kanun)\n"
            "   - Arabuluculukta anlaşılamazsa dava açılır\n\n"
            "5) Manevi Tazminat: Cismani zararda hâkim takdir eder; kişilik hakkı ihlali gerekir"
        ),
    },
    {
        "no": 4,
        "soru": "Miras bırakanın ölümünden sonra vasiyet hükümlerinin iptali için hangi koşullar gereklidir ve dava kim tarafından açılabilir?",
        "alan": "Miras Hukuku",
        "beklenen": (
            "VASİYETNAMENİN İPTALİ DAVASI\n\n"
            "1) Hukuki Dayanak: TMK md.557-559\n\n"
            "2) İptal Nedenleri (TMK md.557):\n"
            "   a) Ehliyet yokluğu: Vasiyetname yapıldığında ayırt etme gücü yoktu\n"
            "   b) İrade sakatlığı: Yanılma, aldatma, korkutma, zorlama\n"
            "   c) Şekil eksikliği: Resmi, el yazılı veya sözlü vasiyet şartları yerine gelmedi\n"
            "   d) İçerik sakatlığı: Hukuka veya ahlaka aykırı koşul/yükümlülük içeriyor\n\n"
            "3) Davayı Açabilecekler:\n"
            "   - Yasal mirasçılar\n"
            "   - İptal halinde menfaat elde edecek atanmış mirasçılar veya vasiyet alacaklıları\n\n"
            "4) Zamanaşımı:\n"
            "   - İyi niyetli olana karşı: öğrenmeden 1 yıl, vasiyetnamenin açılmasından 10 yıl\n"
            "   - Kötü niyetli (zorlama/aldatma) olana karşı: 20 yıl\n\n"
            "5) Yetkili Mahkeme: Miras bırakanın son yerleşim yeri Sulh Hukuk Mahkemesi\n\n"
            "6) Saklı Pay İlişkisi: İptal yanında tenkis davası da açılabilir (saklı pay ihlali)"
        ),
    },
    {
        "no": 5,
        "soru": "İşveren tarafından haksız olarak feshedilen bir iş sözleşmesinde işe iade davası açmak için hangi koşullar aranmakta ve işe iade talebi kabul edilirse ne gibi sonuçlar doğar?",
        "alan": "İş Hukuku — İşe İade",
        "beklenen": (
            "İŞE İADE DAVASI KOŞULLARI VE SONUÇLARI\n\n"
            "1) Hukuki Dayanak: İK md.18-21\n\n"
            "2) Dava Açma Koşulları:\n"
            "   a) En az 30 işçi çalıştıran işyeri (işveren grubu dahil)\n"
            "   b) İşçinin en az 6 aylık kıdemi\n"
            "   c) Belirsiz süreli iş sözleşmesi\n"
            "   d) İşçinin işveren vekili olmayan konumda olması\n"
            "   e) ZORUNLU ARABULUCULUK: Dava öncesi 1 ay bekleme + anlaşamama tutanağı\n"
            "   f) Arabuluculuk sonrası 2 hafta içinde iş mahkemesinde dava\n\n"
            "3) İşverenin Geçerli Neden Yükümlülüğü:\n"
            "   - İşçinin yeterliliği/davranışları veya işletme gerekleri\n"
            "   - Soyut neden yetmez; somut gerekçe\n\n"
            "4) Sonuçlar (Karar işçi lehine olursa):\n"
            "   a) İşe iade kararı: İşçi 10 iş günü içinde başvuruda bulunmalı\n"
            "   b) İşverenin kabul etmemesi: 4-8 aylık brüt ücret iş güvencesi tazminatı\n"
            "   c) Boşta geçen süre ücreti: en fazla 4 aylık brüt ücret\n"
            "   d) İşe iadeyi kabul eden işveren: işçi çalışmak zorunda değil, tazminat alabilir\n\n"
            "5) Emsal: Yargıtay işe iade kararlarında geçerli nedeni dar yorumlar; belirsiz "
            "performans değerlendirmeleri tek başına yetmez"
        ),
    },
]

# ──────────────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ──────────────────────────────────────────────────────────────────────
def banner(t):
    print(f"\n{'='*68}\n  {t}\n{'='*68}")

def sub(t):
    print(f"\n  -- {t} --")

def _cosine(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot/(na*nb) if na and nb else 0.0

def emsal_kullanim_analizi(cevap: str, sem_chunks: list, selected: list) -> dict:
    """Cevapta hangi emsal kararların metni kullanılmış, skor hesapla."""
    cevap_lower = cevap.lower()
    kullanilan = []
    kullanilmayan = []

    for p in selected:
        doc_id = str(p.get("documentId") or p.get("documentID") or p.get("id") or "")
        birim = p.get("birimAdi", "")
        tarih = (p.get("kararTarihi") or "")[:10]
        content = (p.get("markdown_content") or "")

        # Karar numarasından yıl ve daire çıkar
        karar_no_m = re.search(r'(\d{4})/(\d+)\s+E\.\s*,\s*(\d{4})/(\d+)\s+K\.', content)
        karar_no = karar_no_m.group(0) if karar_no_m else f"ID:{doc_id}"
        yil = tarih[:4] if tarih else ""

        # Cevap içinde referans ara: birim adı veya yıl veya daire geçiyor mu
        birim_parcalar = (birim or "").lower().split()
        birim_sayac = sum(1 for p2 in birim_parcalar if len(p2) > 3 and p2 in cevap_lower)
        yil_var = yil and yil in cevap

        # İçerik kelimelerinden örnekleme yaparak örtüşme hesapla
        content_kelimeler = [w for w in re.findall(r'[A-Za-zÇĞİÖŞÜçğıöşü]{6,}', content) if len(w) > 6]
        cevap_kelimeler = set(re.findall(r'[A-Za-zÇĞİÖŞÜçğıöşü]{6,}', cevap_lower))
        ortak = sum(1 for k in content_kelimeler[:200] if k.lower() in cevap_kelimeler)
        oran = ortak / min(len(content_kelimeler[:200]), 200) * 100 if content_kelimeler else 0

        entry = {
            "doc_id": doc_id,
            "birim": birim,
            "tarih": tarih,
            "karar_no": karar_no,
            "birim_ref_sayaci": birim_sayac,
            "yil_var": yil_var,
            "icerik_ortusme": round(oran, 1),
        }
        if birim_sayac >= 1 or yil_var or oran >= 8:
            kullanilan.append(entry)
        else:
            kullanilmayan.append(entry)

    # Semantik chunk eşleşme skoru
    chunk_skorlar = []
    for c in sem_chunks[:5]:
        chunk_text = (c.get("chunk_text") or "").lower()
        chunk_kelimeler = set(re.findall(r'[A-Za-zÇĞİÖŞÜçğıöşü]{5,}', chunk_text))
        cevap_kelimeler2 = set(re.findall(r'[A-Za-zÇĞİÖŞÜçğıöşü]{5,}', cevap_lower))
        ortak2 = len(chunk_kelimeler & cevap_kelimeler2)
        oran2 = ortak2 / max(len(chunk_kelimeler), 1) * 100
        chunk_skorlar.append({
            "pdf_id": c.get("pdf_id", ""),
            "chunk_id": c.get("chunk_id"),
            "distance": c.get("distance", 0),
            "cevap_icerik_ortusme": round(oran2, 1),
            "ilk100": (c.get("chunk_text") or "")[:100],
        })

    return {
        "kullanilan": kullanilan,
        "kullanilmayan": kullanilmayan,
        "chunk_skorlar": chunk_skorlar,
    }

def dogruluk_analizi(beklenen: str, cevap: str) -> dict:
    """Beklenen cevap ile API cevabını karşılaştırarak doğruluk skoru hesapla."""
    beklenen_lower = beklenen.lower()
    cevap_lower = cevap.lower()

    # Önemli anahtar kavramları çıkar
    anahtar_kavramlar = re.findall(r'[A-Za-zÇĞİÖŞÜçğıöşü]{5,}', beklenen_lower)
    anahtar_kavramlar = list(dict.fromkeys(anahtar_kavramlar))  # unique, order preserved

    # Cevaptaki örtüşme
    kapsanan = [k for k in anahtar_kavramlar[:80] if k in cevap_lower]
    oran = len(kapsanan) / min(len(anahtar_kavramlar[:80]), 80) * 100 if anahtar_kavramlar else 0

    # Madde sayılarını beklenen + cevapta ara
    madde_pattern = re.compile(r'(md\.?\s*\d+|madde\s*\d+|\d+\.\s*madde)', re.IGNORECASE)
    beklenen_maddeler = set(madde_pattern.findall(beklenen_lower))
    cevap_maddeler = set(madde_pattern.findall(cevap_lower))
    madde_kapsama = len(beklenen_maddeler & cevap_maddeler) / max(len(beklenen_maddeler), 1) * 100

    return {
        "genel_oran": round(oran, 1),
        "madde_kapsama": round(madde_kapsama, 1),
        "beklenen_maddeler": list(beklenen_maddeler),
        "bulunan_maddeler": list(cevap_maddeler & beklenen_maddeler),
        "eksik_maddeler": list(beklenen_maddeler - cevap_maddeler),
    }

# ──────────────────────────────────────────────────────────────────────
# ASIL TEST: Tek Soru
# ──────────────────────────────────────────────────────────────────────
async def test_soru(soru_obj: dict) -> dict:
    no = soru_obj["no"]
    soru = soru_obj["soru"]
    alan = soru_obj["alan"]
    beklenen = soru_obj["beklenen"]
    session_id = f"test5s_{no}_{os.urandom(3).hex()}"

    banner(f"SORU {no}: {alan}")
    print(f"  {soru}")

    result = {
        "no": no, "alan": alan, "soru": soru, "beklenen": beklenen,
        "session_id": session_id,
        "search_query": None,
        "emsal_cekilen": 0, "emsal_yuklenen": 0,
        "sem_chunks": 0,
        "selected": [],
        "sem_chunks_list": [],
        "api_cevap": "",
        "cevap_karakter": 0,
        "emsal_kullanim": {},
        "dogruluk": {},
        "sure": 0.0,
        "hata": None,
    }

    t_start = time.time()

    try:
        from precedent_service import (
            prepare_precedents_for_detailed_answer,
            summarize_precedents_for_prompt,
            summarize_precedents_ai,
            build_semantic_precedents_block,
            build_full_precedents_block,
        )
        from vector_store import get_vector_store
        from prompts import build_legal_analysis_prompt
        from legal_advisor_ai import SingleLegalAdvisor
        from ai_guard import safe_main_ai_request
        from formatting import standardize_output

        store = get_vector_store()

        # ── 1. Emsal hazırla ──────────────────────────────────────────
        sub("1) Bedesten + Pinecone yükleme")
        meta = await prepare_precedents_for_detailed_answer(
            session_id=session_id,
            user_question=soru,
        )
        selected = meta.get("selected", [])
        result["search_query"] = meta.get("search_query")
        result["emsal_cekilen"] = meta.get("total_fetched", 0)
        result["emsal_yuklenen"] = len(selected)
        result["selected"] = selected

        ham_toplam = sum(len(p.get("markdown_content") or "") for p in selected)
        print(f"  Arama: {result['search_query']!r}")
        print(f"  Cekildi: {result['emsal_cekilen']} | Yuklendi: {result['emsal_yuklenen']} | Ham: {ham_toplam}ch")

        if not selected:
            result["hata"] = "Emsal bulunamadi"
            result["api_cevap"] = "(Emsal bulunamadi — cevap kısmi olabilir)"
            return result

        # ── 2. Prompt bağlamı oluştur ─────────────────────────────────
        sub("2) Prompt baglamı")
        static_block = summarize_precedents_for_prompt(selected)
        ai_short = await summarize_precedents_ai(selected)

        sem_chunks = await store.a_precedent_similarity_search(
            session_id=session_id,
            query=soru,
            k=12,
        )
        result["sem_chunks"] = len(sem_chunks)
        result["sem_chunks_list"] = sem_chunks

        if sem_chunks:
            emsal_blok = build_semantic_precedents_block(sem_chunks, selected, max_chunks=12)
            emsal_etiket = "-- SEMANTİK EMSAL PARÇALARI (SORGUYLA EN İLGİLİ, ANALİZDE ZORUNLU KULLANIM) --"
        else:
            emsal_blok = build_full_precedents_block(selected, max_chars=18000)
            emsal_etiket = "-- TAM EMSAL İÇERİKLERİ (ANALİZDE ZORUNLU KULLANIM) -- [fallback: semantik sonuç yok]"
            print(f"  ! Semantik araması bos; fallback build_full_precedents_block")

        precedent_context = (
            "\n" + static_block
            + "\n\n-- KISA EMSAL OZETLERI --\n" + ai_short
            + f"\n\n{emsal_etiket}\n" + emsal_blok
        )

        print(f"  sem_chunks: {len(sem_chunks)} | emsal_blok: {len(emsal_blok)}ch | total_ctx: {len(precedent_context)}ch")

        # ── 3. AI cevabı üret ─────────────────────────────────────────
        sub("3) AI cevabı uretiliyor...")
        prompt = build_legal_analysis_prompt(
            user_question=soru,
            context_snippet=precedent_context,
            detail_level="detaylı",
            mode="flex_detailed",
        )

        ai_result = await safe_main_ai_request(
            system_prompt=prompt,
            user_message="Yukarıdaki esnek yönergelere göre cevabı üret.",
            model="gpt-5",
        )

        if isinstance(ai_result, dict) and "error" in ai_result:
            result["api_cevap"] = f"AI HATASI: {ai_result['error']}"
            result["hata"] = ai_result["error"]
        else:
            raw = (ai_result.get("response") if isinstance(ai_result, dict) else str(ai_result)).strip()
            result["api_cevap"] = standardize_output(raw, kind="advisor")

        result["cevap_karakter"] = len(result["api_cevap"])
        print(f"  Cevap alindi: {result['cevap_karakter']} karakter")

        # ── 4. Emsal kullanım analizi ─────────────────────────────────
        sub("4) Emsal kullanim analizi")
        result["emsal_kullanim"] = emsal_kullanim_analizi(
            result["api_cevap"], sem_chunks, selected
        )
        ku = result["emsal_kullanim"]
        print(f"  Kullanilan emsal: {len(ku['kullanilan'])} / {len(selected)}")
        for e in ku["kullanilan"]:
            print(f"    [{e['karar_no'][:50]}] birim_ref={e['birim_ref_sayaci']} ortusme={e['icerik_ortusme']}%")

        # ── 5. Doğruluk analizi ───────────────────────────────────────
        sub("5) Dogruluk analizi")
        result["dogruluk"] = dogruluk_analizi(beklenen, result["api_cevap"])
        d = result["dogruluk"]
        print(f"  Genel oran: %{d['genel_oran']} | Madde kapsama: %{d['madde_kapsama']}")
        if d["eksik_maddeler"]:
            print(f"  Eksik maddeler: {d['eksik_maddeler']}")

    except Exception as e:
        import traceback
        result["hata"] = str(e)
        print(f"  HATA: {e}")
        traceback.print_exc()

    result["sure"] = round(time.time() - t_start, 1)
    print(f"  Sure: {result['sure']}s")
    return result


# ──────────────────────────────────────────────────────────────────────
# RAPOR YAZICI
# ──────────────────────────────────────────────────────────────────────
def yaz_rapor(sonuclar: list, dosya: str):
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# 5 SENTETİK HUKUK SORUSU — EMSAL VE DOĞRULUK TEST RAPORU",
        f"",
        f"**Tarih:** {now}  ",
        f"**Yöntem:** Direkt Python pipeline (Bedesten + Pinecone + AI)  ",
        f"**Mod:** Detaylı analiz + emsal tarama açık  ",
        "",
        "---",
        "",
    ]

    for r in sonuclar:
        no = r["no"]
        alan = r["alan"]
        soru = r["soru"]
        beklenen = r["beklenen"]
        cevap = r["api_cevap"]
        ku = r.get("emsal_kullanim", {})
        d = r.get("dogruluk", {})
        selected = r.get("selected", [])
        sem_chunks = r.get("sem_chunks_list", [])

        lines += [
            f"---",
            f"",
            f"## SORU {no}: {soru}",
            f"",
            f"**Alan:** {alan}  ",
            f"**Arama sorgusu:** `{r.get('search_query')}`  ",
            f"**Süre:** {r.get('sure')}s  ",
            "",
            "### BEKLENEN CEVAP",
            "",
            "```",
            beklenen,
            "```",
            "",
            "### API CEVABI",
            "",
            cevap[:3000] + ("...[KISALTILDI]" if len(cevap) > 3000 else ""),
            "",
            "### EMSAL KULLANIMI",
            "",
            f"- **Kaç emsal çekildi:** {r['emsal_cekilen']} bulundu, {r['emsal_yuklenen']} seçilip yüklendi",
            f"- **Semantik chunk sayısı:** {r['sem_chunks']}",
            f"- **Kaç emsal kullanıldı:** {len(ku.get('kullanilan', []))} / {r['emsal_yuklenen']}",
            "",
            "**Çekilen emsal listesi:**",
            "",
        ]
        for i, p in enumerate(selected, 1):
            doc_id = str(p.get("documentId") or p.get("documentID") or "?")
            birim = p.get("birimAdi", "?")
            tarih = (p.get("kararTarihi") or "")[:10]
            icerik_len = len(p.get("markdown_content") or "")
            lines.append(f"- [{i}] {birim} | {tarih} | {icerik_len}ch | ID:{doc_id}")

        lines += ["", "**Kullanılan emsaller ve semantik eşleşme skoru:**", ""]
        for e in ku.get("kullanilan", []):
            lines.append(
                f"  * `{e['karar_no'][:60]}` — {e['birim']} ({e['tarih']}) "
                f"— içerik örtüşme: **%{e['icerik_ortusme']}** "
                f"— birim referans sayısı: {e['birim_ref_sayaci']}"
            )
        if not ku.get("kullanilan"):
            lines.append("  * (Hiçbir emsal referansı tespit edilemedi)")

        lines += ["", "**Kullanılmayan emsaller:**", ""]
        for e in ku.get("kullanilmayan", []):
            lines.append(f"  * `{e['karar_no'][:60]}` — {e['birim']} — örtüşme: %{e['icerik_ortusme']}")
        if not ku.get("kullanilmayan"):
            lines.append("  * (Tüm emsaller kullanıldı)")

        lines += ["", "**Semantik chunk skorları (ilk 5):**", ""]
        for c in r.get("emsal_kullanim", {}).get("chunk_skorlar", [])[:5]:
            lines.append(
                f"  * chunk#{c.get('chunk_id')} | dist={c.get('distance',0):.4f} "
                f"| cevap_örtüşme=%{c.get('cevap_icerik_ortusme',0)} "
                f"| `{c.get('ilk100','')[:80]}...`"
            )

        lines += [
            "",
            "### DOĞRULUK ANALİZİ",
            "",
            f"- **Kullanılan kaynaklara göre doğruluk oranı:** %{d.get('genel_oran', 0)}",
            f"- **Kanun maddesi kapsama oranı:** %{d.get('madde_kapsama', 0)}",
            f"- **Beklenen maddeler:** {d.get('beklenen_maddeler', [])}",
            f"- **Cevapta bulunan:** {d.get('bulunan_maddeler', [])}",
            f"- **Eksik maddeler:** {d.get('eksik_maddeler', [])}",
            "",
        ]

        # Cevap eksikleri/hataları — basit kural
        eksikler = []
        hatalar = []
        beklenen_lower = beklenen.lower()
        cevap_lower = cevap.lower()

        # Anahtar terim kontrolü
        kritik_terimler = {
            "haklı fesih": ["haklı fesih", "haklı neden"],
            "zamanaşımı": ["zamanaşımı", "süre"],
            "arabuluculuk": ["arabuluculuk"],
            "ihbar tazminatı": ["ihbar tazminatı"],
            "kıdem tazminatı": ["kıdem tazminatı"],
            "iş güvencesi": ["iş güvencesi"],
            "iptal davası": ["iptal dava"],
            "sulh hukuk": ["sulh hukuk"],
        }
        for terim, sinonimler in kritik_terimler.items():
            beklenen_var = any(s in beklenen_lower for s in sinonimler)
            cevap_var = any(s in cevap_lower for s in sinonimler)
            if beklenen_var and not cevap_var:
                eksikler.append(f"'{terim}' beklenen cevapta var ama API cevabında geçmiyor")

        if r.get("hata"):
            hatalar.append(f"Sistem hatası: {r['hata']}")

        lines += [
            f"- **Cevaptaki eksikler:**",
        ]
        for e2 in eksikler or ["(Belirgin eksik tespit edilmedi)"]:
            lines.append(f"  - {e2}")

        lines += [f"- **Cevaptaki hatalar:**"]
        for h in hatalar or ["(Açık hata tespit edilmedi)"]:
            lines.append(f"  - {h}")

        lines += [
            "",
            "### KAYNAK KALİTESİ",
            "",
        ]
        # Kaynak kalitesi değerlendirmesi
        kisa_emsaller = [p for p in selected if len(p.get("markdown_content") or "") < 500]
        yanlis_alan = []
        for p in selected:
            birim_str = (p.get("birimAdi") or "").lower()
            content_str = (p.get("markdown_content") or "").lower()
            if alan == "Kat Mülkiyeti Hukuku" and "danistay" in birim_str:
                yanlis_alan.append(f"{p.get('birimAdi')} — idare/vergi kararı, kat mülkiyeti sorusuna uygun değil")
            elif alan in ("Haksız Fiil / Trafik Hukuku",) and "danistay" in birim_str:
                yanlis_alan.append(f"{p.get('birimAdi')} — idare kararı, haksız fiil sorusuna uygun değil")

        tutarsizlik_var = bool(kisa_emsaller) or bool(yanlis_alan)
        lines.append(f"- **Hata/tutarsızlık var mı:** {'EVET' if tutarsizlik_var else 'HAYIR'}")

        if kisa_emsaller:
            lines.append(f"  - Çok kısa emsal kararlar ({len(kisa_emsaller)} adet < 500 karakter): içerik yetersiz olabilir")
            for p in kisa_emsaller:
                lines.append(f"    * {p.get('birimAdi')} | {(p.get('kararTarihi',''))[:10]} | {len(p.get('markdown_content',''))} ch")
        if yanlis_alan:
            lines.append(f"  - Yanlış mahkeme alanı:")
            for y in yanlis_alan:
                lines.append(f"    * {y}")
        if not tutarsizlik_var:
            lines.append("  - Emsal kararlar alan ve içerik açısından uygun görünüyor")

        lines += [""]

    # ── Özet Tablo ──────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## ÖZET TABLO",
        "",
        "| Soru | Alan | Emsal Çekilen | Emsal Kullanılan | Doğruluk % | Madde % | Sem Chunk | Kritik Hata |",
        "|------|------|:---:|:---:|:---:|:---:|:---:|-----|",
    ]
    for r in sonuclar:
        ku = r.get("emsal_kullanim", {})
        d = r.get("dogruluk", {})
        kritik = r.get("hata") or ("Yanlış alan" if any(
            "Danıştay" in (p.get("birimAdi") or "") and r["alan"] not in ("Haksız Fiil / Trafik Hukuku",)
            for p in r.get("selected", [])
        ) else "-")
        lines.append(
            f"| S{r['no']} | {r['alan']} | {r['emsal_yuklenen']} | "
            f"{len(ku.get('kullanilan',[]))} | "
            f"%{d.get('genel_oran',0)} | %{d.get('madde_kapsama',0)} | "
            f"{r.get('sem_chunks',0)} | {str(kritik)[:40]} |"
        )

    lines += [
        "",
        "---",
        f"*Rapor otomatik oluşturuldu — {now}*",
    ]

    with open(dosya, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nRapor yazildi: {dosya}")


# ──────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────
async def main():
    banner("5 SENTETİK HUKUK SORUSU TAM PIPELINE TESTİ")
    print("  Bedesten + Pinecone (semantik) + AI cevap + emsal analizi")

    sonuclar = []
    for soru_obj in SORULAR:
        r = await test_soru(soru_obj)
        sonuclar.append(r)
        await asyncio.sleep(3)  # Pinecone propagation + rate limit

    rapor = os.path.join(os.path.dirname(__file__), "test_5soru_rapor.md")
    yaz_rapor(sonuclar, rapor)

    banner("ÖZET")
    print(f"\n  {'No':<3} {'Alan':<30} {'Çekilen':>8} {'Kullanan':>9} {'Doğruluk':>9} {'Sem':>5}")
    print(f"  {'-'*65}")
    for r in sonuclar:
        ku = r.get("emsal_kullanim", {})
        d = r.get("dogruluk", {})
        print(
            f"  S{r['no']:<2} {r['alan']:<30} {r['emsal_yuklenen']:>8} "
            f"{len(ku.get('kullanilan',[])):>9} "
            f"{d.get('genel_oran',0):>8}% "
            f"{r.get('sem_chunks',0):>5}"
        )
    print(f"\n  Tam rapor: test_5soru_rapor.md")


if __name__ == "__main__":
    asyncio.run(main())

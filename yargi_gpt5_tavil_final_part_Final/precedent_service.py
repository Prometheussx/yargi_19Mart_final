"""Precedent (Emsal) arama ve sıralama servisi.

Detaylı analiz modunda kullanılmak üzere:
1. Soru/bağlamdan arama cümlesi üretir
2. Bedesten API ile en fazla 3 karar çeker
3. Embedding benzerliği ile en ilgili ilk 10 kararı seçer
4. Vector store'a (kind=precedent) kaydeder ve kimliklerini döner

Kısa (concise) cevap modunda bu akış tetiklenmez.
"""
from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime
from typing import List, Dict, Any

from ai_guard import safe_search_ai_request
from ai_guard import safe_case_analysis_ai_request
from vector_store import get_vector_store

try:
    from bedesten_mcp_module.client import BedestenApiClient  # type: ignore
    BEDESTEN_AVAILABLE = True
except Exception:
    BedestenApiClient = None  # type: ignore
    BEDESTEN_AVAILABLE = False

# -------------------- Search Query --------------------
SEARCH_SYSTEM_PROMPT = """
Sen deneyimli Türk hukuk uzmanısın. Görev: Aşağıdaki bilgilerden UYAP / Bedesten emsal karar araması için ETKİLİ bir Türkçe arama cümlesi üretmek.

KURALLAR:
- 5-9 kelime, Türkçe
- Gereksiz bağlaç yok
- Olay + hukuki nitelik + konu (örn: "yazılım eser hakkı ihlali FSEK tazminat", "iş akdi fesih ihbar kıdem tazminat")
- Kullanıcı sorusu "dosyayı özetle", "belgeden anlat", "dosyadaki konuyu" gibi METASORUysa: SORUYU DEĞİL, BAĞLAM/DOSYA içeriğindeki asıl hukuki uyuşmazlığı çıkar ve ona göre arama cümlesi yaz
- Bağlam verilmemişse sorudan en iyi tahmini yap

SADECE JSON formatı döndür: {"search_query": "..."}
""".strip()


async def generate_precedent_search_query(user_question: str, context_snippet: str = "") -> str | None:
    ctx_part = ""
    if context_snippet.strip():
        ctx_part = f"\n\nDava/Dosya Bağlamı (asıl hukuki konuyu buradan çıkar):\n{context_snippet[:2000]}"
    try:
        result = await safe_search_ai_request(
            system_prompt=SEARCH_SYSTEM_PROMPT,
            user_message=f"Kullanıcı Sorusu: {user_question[:1500]}{ctx_part}",
            model="gpt-4o-mini"  # Arama cümlesi için hızlı model yeterli
        )
        if "error" in result:
            return None
        raw = (result.get("response") or "").strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(raw)
            return data.get("search_query") or None
        except json.JSONDecodeError:
            return None
    except Exception:
        return None


# -------------------- Fetch Precedents --------------------
async def fetch_precedents(search_query: str, limit: int = 5) -> List[Dict[str, Any]]:
    print(f"📚 [PRECEDENT] Fetching precedents for query: '{search_query}' (limit: {limit})")
    if not BEDESTEN_AVAILABLE or not BedestenApiClient:
        print("📚 [PRECEDENT] BedestenApiClient not available")
        return []
    client = BedestenApiClient()
    try:
        print(f"📚 [PRECEDENT] Calling search_documents_phrase_only...")
        raw = await client.search_documents_phrase_only(search_query)
        items = []
        try:
            items = raw.get("data", {}).get("emsalKararList", []) or []
            print(f"📚 [PRECEDENT] Found {len(items)} items from search")
        except Exception:
            items = []
        # İlk limit kadar karar için markdown içeriklerini paralel al
        selected = items[:limit]
        print(f"📚 [PRECEDENT] Processing {len(selected)} selected items")
        async def _fetch(case: Dict[str, Any]):
            doc_id = case.get("documentId") or case.get("documentID") or case.get("id")
            if not doc_id:
                case["markdown_content"] = ""
                return case
            try:
                md = await client.get_document_as_markdown(doc_id)
                case["markdown_content"] = md.markdown_content or ""
            except Exception as e:  # pragma: no cover
                case["markdown_content"] = f"İçerik alınamadı: {e}"
            return case
        # Limitli eş zamanlılık: 3 paralel — Bedesten API rate-limit koruması
        sem = asyncio.Semaphore(3)
        async def _guarded(c):
            async with sem:
                return await _fetch(c)
        fetched = await asyncio.gather(*[_guarded(dict(c)) for c in selected])
        # Sıra ekle
        for i, c in enumerate(fetched, 1):
            c["rank"] = i
        print(f"📚 [PRECEDENT] Successfully fetched and processed {len(fetched)} precedents")
        return fetched
    except Exception as e:  # pragma: no cover
        print(f"📚 [PRECEDENT] Error in fetch_precedents: {e}")
        return []
    finally:
        try:
            await client.close_client_session()  # type: ignore
        except Exception:
            pass


# -------------------- Court Priority Scoring --------------------
def _court_priority_score(birim: str, question: str) -> float:
    """Soru konusuna göre mahkeme türü uyumunu puanlar.

    Doğru Yargıtay dairesi → +0.12 bonus, genel Yargıtay → +0.03,
    İlk derece mahkeme → -0.05, yanlış alanda Danıştay → -0.12.
    Bu puan cosine similarity'e EKLENİR; puanı düşük ama alakalı
    daire kararlarının üst sıralarda yer almasını sağlar.
    """
    birim_lower = (birim or "").lower()
    q_lower = (question or "").lower()

    # İlk derece mahkemeler: hafif ceza puanı
    if any(x in birim_lower for x in ["asliye", "sulh", "ağır ceza", "idare mahkemesi", "ticaret mahkemesi"]):
        return -0.05

    # Danıştay: idare/vergi uyumlu, diğer konularda güçlü ceza
    if "danıştay" in birim_lower or "danistay" in birim_lower:
        if any(x in q_lower for x in ["idare", "vergi", "kamulaştırma", "devlet", "memur", "kamu"]):
            return 0.05
        return -0.12

    # Yargıtay kararları — daire uyum analizi
    if "yargıtay" in birim_lower or "hukuk dairesi" in birim_lower or "ceza dairesi" in birim_lower:
        # İş hukuku: 9. HD, 22. HD, 7. HD uygun — 15. HD (borçlar) uygun değil
        is_q = any(x in q_lower for x in ["işçi", "işveren", "iş akdi", "kıdem", "ihbar", "işe iade", "fesih"])
        if is_q:
            if any(d in birim_lower for d in ["9. hukuk", "22. hukuk", "7. hukuk"]):
                return 0.12
            if any(d in birim_lower for d in ["15. hukuk", "11. hukuk", "12. hukuk"]):
                return -0.05

        # Aile hukuku: 2. HD
        aile_q = any(x in q_lower for x in ["boşanma", "nafaka", "velayet", "evlilik", "aile"])
        if aile_q and "2. hukuk" in birim_lower:
            return 0.12

        # Kira / Gayrimenkul: 3. HD, 6. HD
        kira_q = any(x in q_lower for x in ["kira", "kiracı", "taşınmaz", "tapu", "gayrimenkul", "kat mülkiyet"])
        if kira_q and any(d in birim_lower for d in ["3. hukuk", "6. hukuk"]):
            return 0.12

        # Trafik / Haksız fiil: 17. HD, 4. HD
        trafik_q = any(x in q_lower for x in ["trafik", "kaza", "haksız fiil", "maddi tazminat", "manevi tazminat"])
        if trafik_q and any(d in birim_lower for d in ["17. hukuk", "4. hukuk"]):
            return 0.12

        # Miras hukuku: 2. HD, 3. HD
        miras_q = any(x in q_lower for x in ["miras", "vasiyet", "mirasçı", "tereke", "miras bırakan"])
        if miras_q and any(d in birim_lower for d in ["2. hukuk", "3. hukuk"]):
            return 0.12

        return 0.03  # genel Yargıtay bonusu (Hukuk Genel Kurulu dahil)

    return 0.0


# -------------------- Rank Precedents --------------------
async def rank_precedents(user_question: str, precedents: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    if not precedents:
        return []
    store = get_vector_store()
    try:
        # Embed question + each precedent (truncated)
        texts = [user_question[:4000]]
        for p in precedents:
            txt = (p.get("markdown_content") or "")[:8000]
            if not txt:
                txt = f"{p.get('birimAdi','')} {p.get('kararTarihi','')} {p.get('itemType','')}"
            texts.append(txt)
        embs = await store.a_embed_texts(texts)
        q_emb = embs[0]
        # Cosine similarity: dot(a,b) / (||a|| * ||b||)
        # Dot product yerine cosine similarity kullan — farklı uzunluktaki belgeler
        # arasında adil karşılaştırma sağlar; kısa ama çok alakalı kararların puanı
        # yüksek, uzun ama az alakalı kararların puanı düşük kalır.
        def _cosine(a: list, b: list) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0.0 or norm_b == 0.0:
                return 0.0
            return dot / (norm_a * norm_b)

        scored = []
        for emb, p in zip(embs[1:], precedents):
            sim = _cosine(q_emb, emb)
            court_bonus = _court_priority_score(p.get("birimAdi", ""), user_question)
            score = sim + court_bonus
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:top_k]]
    except Exception:
        # Hata durumunda ilk top_k
        return precedents[:top_k]


# -------------------- Store Precedents --------------------
async def store_precedents(session_id: str, precedents: List[Dict[str, Any]]) -> List[str]:
    """Seçilen emsal kararları vector store'a precedent türünde kaydeder.
    Her karar tek döküman olarak chunk'lanır. Geriye pdf_id listesi döner.
    """
    if not precedents:
        print("📚 [PRECEDENT] No precedents to store")
        return []
    store = get_vector_store()
    stored_ids: List[str] = []
    print(f"📚 [PRECEDENT] Storing {len(precedents)} precedents to vector store")
    for i, p in enumerate(precedents):
        try:
            doc_id = p.get("documentId") or p.get("documentID") or p.get("id") or "unknown"
            pdf_id = f"__precedent__{doc_id}"
            # Ham içerik: hiçbir başlık/biçim eklemeden aynen kaydet
            raw_text = (p.get("markdown_content") or "")
            print(f"📚 [PRECEDENT] Storing precedent {i+1}/{len(precedents)}: {pdf_id} ({len(raw_text)} chars, raw)")
            result = await store.a_add_precedent(session_id=session_id, precedent_id=pdf_id, text=raw_text, extra_meta=p)
            print(f"📚 [PRECEDENT] Store result: {result}")
            stored_ids.append(pdf_id)
        except Exception as e:  # pragma: no cover
            print(f"📚 [PRECEDENT] Error storing precedent {i+1}: {e}")
            continue
    print(f"📚 [PRECEDENT] Successfully stored {len(stored_ids)} precedents")
    return stored_ids


# -------------------- High-level Orchestrator --------------------
async def prepare_precedents_for_detailed_answer(session_id: str, user_question: str, context_snippet: str = "") -> Dict[str, Any]:
    """Detaylı yanıt öncesi tüm süreci orchestrate eder.
    Dönen sözlük: { 'search_query': str|None, 'selected': [...], 'stored_ids': [...]}

    context_snippet: Doküman/dosya içeriği. Kullanıcı sorusu meta ("dosyayı özetle") ise
                     bu bağlamdan asıl hukuki konu çıkarılarak arama yapılır.
    """
    print(f"📚 [PRECEDENT] Starting precedent preparation for session: {session_id}")
    search_query = await generate_precedent_search_query(user_question, context_snippet)
    print(f"📚 [PRECEDENT] Generated search query: '{search_query}'")
    fallback_used = False
    fallback_reason = None
    if not search_query:
        # Heuristik fallback: önce bağlamdan, yoksa sorudan anlamlı anahtar kelimeleri çıkar
        print("📚 [PRECEDENT] No AI search query, building heuristic fallback query")
        import re as _re
        # Temel Türkçe durak kelimeler
        STOP = {"ve","veya","ile","da","de","bir","bu","şu","ile","için","olan","hakkında","olan","göre","mı","mi","mu","mü","ki",
                "dosyada","dosyadaki","dosyayı","bana","beni","benim","konuyu","konuda","özetle","anlat","söyle","hakkında"}
        # Bağlam varsa ve soru metaysa bağlamdan token çıkar, yoksa sorudan
        _meta_words = {"özetle", "anlat", "dosya", "belge", "dosyadaki", "yol göster", "özet"}
        _use_ctx = context_snippet.strip() and any(w in user_question.lower() for w in _meta_words)
        heuristic_text = context_snippet[:1500] if _use_ctx else user_question
        tokens = [_t.lower() for _t in _re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{3,}", heuristic_text)][:60]
        keywords = []
        for t in tokens:
            if t in STOP: continue
            if t.endswith("leri") or t.endswith("ları"): t = t[:-3]
            if t.endswith("ler") or t.endswith("lar"): t = t[:-3]
            if t not in keywords:
                keywords.append(t)
            if len(keywords) >= 8:
                break
        search_query = " ".join(keywords) if keywords else None
        fallback_used = True
        fallback_reason = "ai_query_none"
        print(f"📚 [PRECEDENT] Heuristic fallback query: '{search_query}' (from={'context' if _use_ctx else 'question'})")
    if not search_query:
        print("📚 [PRECEDENT] Fallback query also empty; returning empty set")
        return {"search_query": None, "selected": [], "stored_ids": [], "fallback_used": fallback_used, "fallback_reason": fallback_reason}
    all_precedents = await fetch_precedents(search_query, limit=5)
    print(f"📚 [PRECEDENT] Fetched {len(all_precedents)} precedents")
    if not all_precedents and not fallback_used:
        # İkinci bir fallback: query'yi kısaltıp tekrar dene
        short_q = (search_query or '')[:40].rsplit(' ',1)[0]
        if short_q and short_q != search_query:
            print(f"📚 [PRECEDENT] Empty result, retrying with shortened query: '{short_q}'")
            retry = await fetch_precedents(short_q, limit=5)
            if retry:
                all_precedents = retry
                fallback_used = True
                fallback_reason = "shortened_query"
                search_query = short_q
    ranked = await rank_precedents(user_question, all_precedents, top_k=10)
    print(f"📚 [PRECEDENT] Ranked to {len(ranked)} top precedents (pre-limit)")
    # En ilgili 5 emsal kullan (2'den artırıldı - daha kapsamlı analiz için)
    ranked = ranked[:5]
    print(f"📚 [PRECEDENT] Limiting to top {len(ranked)} precedents for detailed mode")
    if not ranked and all_precedents:
        print("📚 [PRECEDENT] Ranking empty, taking first 5 as fallback")
        ranked = all_precedents[:5]
        fallback_used = True
        fallback_reason = fallback_reason or "ranking_empty"
    stored_ids = await store_precedents(session_id, ranked)
    print(f"📚 [PRECEDENT] Stored {len(stored_ids)} precedents to vector store")
    result = {
        "search_query": search_query,
        "selected": ranked,
        "stored_ids": stored_ids,
        "total_fetched": len(all_precedents),
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason
    }
    print(f"📚 [PRECEDENT] Preparation complete: {len(ranked)} selected, {len(stored_ids)} stored")
    return result


def summarize_precedents_for_prompt(precedents: List[Dict[str, Any]]) -> str:
    """Prompt'a eklenecek kısa özet listesi üretir."""
    parts = ["-- SEÇİLEN EMSAL KARARLAR (TOPLAM: {} ) --".format(len(precedents))]
    for i, p in enumerate(precedents, 1):
        doc_id = p.get("documentId") or p.get("documentID") or p.get("id") or f"DOC{i}"
        birim = p.get("birimAdi", "?")
        tarih = p.get("kararTarihi", "?")
        item_type = p.get("itemType", "Karar")
        content = (p.get("markdown_content") or "").strip().replace("\n", " ")[:350]
        parts.append(f"[{i}] {doc_id} | {birim} | {tarih} | {item_type} :: {content}...")
    # Talimat güncellendi: Metin içinde parantezli veya köşeli kaynak vermeyin.
    # Emsal referanslarını anlatı içinde doğal şekilde ifade edin (ör: mahkeme, daire, yıl, kısa konteks). 'Kaynak:' başlıkları kullanmayın.
    parts.append(
        "YÖNERGE: Metin içinde parantezli/köşeli kaynak etiketleri vermeyin. Emsalleri anlatı içinde doğal biçimde (mahkeme/daire/yıl gibi) anın; ayrıca 'Kaynak:' veya liste oluşturmayın."
    )
    return "\n".join(parts)


def build_full_precedents_block(precedents: List[Dict[str, Any]], max_chars: int = 200000) -> str:
    """Her emsal kararın markdown içeriğini bloklar halinde döndürür.

    Bütçe emsaller arasında eşit dağıtılır: her emsal max_chars // len(precedents) karakter
    alır. Bu sayede tek büyük karar tüm bütçeyi tüketip diğerlerini kesmez.
    """
    if not precedents:
        return "(Emsal yok)"
    per_case_budget = max_chars // len(precedents)
    parts: List[str] = [f"-- TAM EMSAL METİNLERİ (ADET={len(precedents)}) --"]
    for i, p in enumerate(precedents, 1):
        doc_id = p.get("documentId") or p.get("documentID") or p.get("id") or f"DOC{i}"
        body = p.get("markdown_content") or ""
        header_lines = [
            f"# EMSAL {i} - ID: {doc_id}",
            f"Birim: {p.get('birimAdi','N/A')} | Tarih: {p.get('kararTarihi','N/A')} | Tür: {p.get('itemType','Karar')}",
            "",
        ]
        header_str = "\n".join(header_lines)
        header_len = len(header_str)
        body_budget = per_case_budget - header_len
        if body_budget <= 0:
            body_budget = 200  # minimum: en az 200 karakter gövde göster
        if len(body) > body_budget:
            body = body[:body_budget] + f"\n... [+{len(p.get('markdown_content','')) - body_budget} karakter kesildi]"
        block = header_str + body
        parts.append(block)
    return "\n\n".join(parts)


def build_semantic_precedents_block(
    chunks: List[Dict[str, Any]],
    precedents: List[Dict[str, Any]],
    max_chunks: int = 12,
) -> str:
    """Pinecone semantik aramasından dönen chunk'ları kaynak karar bilgisiyle birleştirerek
    prompt'a gönderilecek bağlam bloğunu oluşturur.

    Parametreler:
        chunks: a_precedent_similarity_search() çıktısı — pdf_id, chunk_id, chunk_text, distance
        precedents: prepare_precedents_for_detailed_answer() 'selected' listesi — meta bilgiler
        max_chunks: prompt'a girecek maksimum chunk sayısı

    Dönen metin: Her chunk "KAYNAK: ..." başlığıyla birlikte, mesafeye göre sıralı
    """
    if not chunks:
        return "(Semantik emsal eşleşmesi yok)"

    # pdf_id → meta eşlemesi (birim, tarih, tür)
    meta_map: Dict[str, Dict[str, Any]] = {}
    for p in precedents:
        doc_id = p.get("documentId") or p.get("documentID") or p.get("id") or ""
        safe_id = f"precedent_{doc_id}"
        meta_map[safe_id] = p
        meta_map[f"__precedent__{doc_id}"] = p
        # sanitized versiyonlar da olabilir — doc_id ile prefix match yeterli

    selected_chunks = chunks[:max_chunks]
    parts: List[str] = [f"-- SEMANTİK EMSAL PARÇALARI (ADET={len(selected_chunks)}, sorguyla en ilgili) --"]
    seen_ids: set = set()

    for c in selected_chunks:
        pdf_id = c.get("pdf_id") or ""
        chunk_text = c.get("chunk_text") or ""
        distance = c.get("distance", 0.0)

        # Meta bilgisini bul
        meta = meta_map.get(pdf_id)
        if meta is None:
            # Kısmi eşleşme: pdf_id içinde doc_id geçiyor mu?
            for key, val in meta_map.items():
                if key and pdf_id and (key in pdf_id or pdf_id in key):
                    meta = val
                    break

        if meta:
            birim = meta.get("birimAdi", "Bilinmeyen Mahkeme")
            tarih = (meta.get("kararTarihi") or "")[:10]  # sadece YYYY-MM-DD
            tur = meta.get("itemType", {})
            tur_str = tur.get("description", "Karar") if isinstance(tur, dict) else str(tur)
            doc_id = meta.get("documentId") or meta.get("documentID") or meta.get("id") or pdf_id
            kaynak = f"Kaynak: {birim} | {tarih} | {tur_str} (ID:{doc_id})"
        else:
            kaynak = f"Kaynak: {pdf_id}"

        unique_key = f"{pdf_id}:{c.get('chunk_id')}"
        if unique_key in seen_ids:
            continue
        seen_ids.add(unique_key)

        block = f"[EMSAL PARÇA — {kaynak}]\n{chunk_text}"
        parts.append(block)

    return "\n\n".join(parts)


async def summarize_precedents_ai(precedents: List[Dict[str, Any]]) -> str:
    """Model ile kompakt özet listesi (#i - kısa cümle) oluşturur.
    Eksik/hata durumunda fallback olarak statik özet fonksiyonu kullanılır."""
    if not precedents:
        return "(Emsal yok)"
    # Prepare condensed text
    chunks = []
    for i, p in enumerate(precedents, 1):
        doc_id = p.get("documentId") or p.get("documentID") or p.get("id") or f"DOC{i}"
        content = (p.get("markdown_content") or "")[:800]
        chunks.append(f"## EMSAL {i}\nID: {doc_id}\nİçerik:\n{content}\n")
    prompt = (
        "Aşağıdaki emsal karar parçalarını her biri için tek satır, 15 kelimeyi geçmeyen özet üret.\n"
        "Not: Köşeli parantez, numara ya da 'Kaynak' ibaresi kullanma; yalnızca anlatı.\n\n" + "\n".join(chunks)
    )
    try:
        result = await safe_case_analysis_ai_request(
            system_prompt="Türk hukuk emsal özetleyici.",
            user_message=prompt,
            model="gpt-5"
        )
        if "error" in result:
            return summarize_precedents_for_prompt(precedents)
        return result.get("response", "").strip()
    except Exception:
        return summarize_precedents_for_prompt(precedents)


def enforce_citations(answer: str, precedent_count: int) -> str:
    """Artık otomatik '#n' kaynak etiketi eklemiyoruz. Metni olduğu gibi döndür."""
    return answer

def convert_numeric_citations_to_docids(answer: str, precedents: List[Dict[str, Any]]) -> str:
    """Metin içinde '(Kaynak: #1,#4)' gibi numaraları varsa bunları cümle/paragraf içine [DOCID] olarak dönüştürür.
    Basit strateji: Etiketin bulunduğu yere, sıradaki numaralara karşılık gelen [DOCID] dizisini koyup etiketi kaldır.
    """
    if not answer or not precedents:
        return answer
    import re
    # index->docid haritası
    id_map = {}
    for i, p in enumerate(precedents, 1):
        _id = p.get("documentId") or p.get("documentID") or p.get("id") or f"DOC{i}"
        id_map[i] = str(_id)
    def repl(m: re.Match):
        nums = m.group(1)
        idxs = []
        for part in re.split(r"[\s,]+", nums.strip()):
            if not part:
                continue
            try:
                idxs.append(int(part))
            except ValueError:
                pass
        tags = [f"[{id_map[i]}]" for i in idxs if i in id_map]
        return (" "+" ".join(tags)).strip()
    # '(Kaynak: #1,#2)' veya '(Kaynak: #1 , #2)'
    pattern = re.compile(r"\(\s*Kaynak\s*:\s*#([0-9\s,]+)\s*\)")
    text = re.sub(pattern, repl, answer)
    return text

# CLAUDE.md — Yargı AI Hukuki Danışman Projesi

## Proje Özeti
Türk hukuku için FastAPI tabanlı AI danışmanlık sistemi.
- **Backend:** FastAPI (app.py)
- **AI Katmanı:** OpenAI multi-token (ai_guard.py)
- **Vektör DB:** Pinecone (vector_store.py)
- **Emsal Arama:** Bedesten API (bedesten_mcp_module/)
- **Web Araması:** Tavily (web_context.py)
- **Frontend:** Streamlit (ui.py)

## KISITLAMALAR — DEĞİŞTİRİLMEYECEKLER
- Mevcut API endpoint imzaları değiştirilemez
- API entegrasyonları değiştirilemez (OpenAI, Pinecone, Bedesten, Tavily)
- Çağrı akışları (pipeline) değiştirilemez
- Model isimleri (`gpt-5`, `gpt-4o-mini`, `gpt-4o`) değiştirilemez — kullanıcı tercihidir
- Yalnızca performans ve doğruluk bazlı düzeltmeler yapılabilir

---

## TESPIT EDİLEN HATALAR VE ÇÖZÜM DURUMU

### ✅ DÜZELTİLDİ

#### 1. vector_store.py:185 — Yanlış zaman fonksiyonu
**Problem:** `asyncio.get_event_loop().time()` kullanımı yanlış.
- `asyncio...time()` event loop başlangıcından itibaren monotonic süre döndürür; Unix timestamp değildir.
- SQLite `created_at INTEGER` sütununa yanlış değer yazılır → cache geçerlilik kontrolü bozulur.
**Düzeltme:** `time.time()` kullanılmalı.

#### 2. precedent_service.py:128 — Dot product yerine cosine similarity
**Problem:** `score = sum(a*b for a,b in zip(q_emb, emb))` — bu dot product hesaplar.
- Embedding vektörleri normalize edilmemişse, uzun/kısa belgeler arasında adil karşılaştırma yapılamaz.
- text-embedding-3-large modeli birim küre üzerinde normalize değildir.
- Kısa ama alakalı kararlar, uzun ama az alakalı kararların gerisinde kalır.
**Düzeltme:** Cosine similarity = dot(a,b) / (||a|| * ||b||)

#### 3. case_analysis_ai_simple.py:256 — gather() exception yutma
**Problem:** `await asyncio.gather(*tasks)` — `return_exceptions=True` yok.
- Paralel fetch'lerden herhangi biri exception fırlatırsa TÜM analiz çöker.
- 7 belgeden 1'i hata verse bile kullanıcı hiç sonuç göremez.
**Düzeltme:** `return_exceptions=True` eklenmeli; None/Exception olanlar skip edilmeli.

#### 4. prompts.py:291 — Escape hatası: disclaimer modele ulaşmıyor
**Problem:** `_BASE_DYNAMIC_PROMPT` template'inde `{{disclaimer}}` yazılı.
- Python str.format() ile `{{X}}` → literal `{X}` üretir, değişken yerine geçmez.
- `build_dynamic_party_case_prompt()` `disclaimer=disclaimer` geçiyor ama template `{{disclaimer}}` (çift süslü) olduğu için format() tarafından ASLA işlenmiyor.
- Model `{disclaimer}` metnini olduğu gibi görüyor; yasal uyarı promptuna girmiyor.
**Düzeltme:** `{{disclaimer}}` → `{disclaimer}` (tek süslü).

#### 5. vector_store.py — async batch upsert sıralı çalışıyor
**Problem:** `_a_batched_upsert` içinde `for` döngüsünde `await asyncio.to_thread(...)` sıralı bekliyor.
- 200 chunk = 4 batch varsa 4 ayrı round-trip peş peşe yapılır.
- `asyncio.gather()` ile paralel yapılabilir.
**Düzeltme:** Tüm batch'leri `asyncio.gather()` ile eş zamanlı gönder.

#### 6. vector_store.py:224,261 — None filtrelemesi konum kayması
**Problem:** `[e for e in out if e is not None]`
- Eğer bir embedding API çağrısı kısmen başarısız olursa `out` listesinde None kalabilir.
- None'lar filtrelenince liste kısalır → chunk-embedding eşleşmesi bozulur.
- Yanlış embedding yanlış chunk'a upsert edilir → retrieval accuracy'si düşer.
**Düzeltme:** None olan konumları tespit et, uyar ve sıfır vektörle doldur ya da exception fırlat.

---

### ⚠️ NOTLAR (Değiştirilmeyecek / Önemsiz)

#### session_chat_precedents memory büyümesi (app.py:61)
- Uzun çalışmada dict büyür. Ama içerik küçük metadata (büyük veriler Pinecone'da).
- Bellek sorunu yaratması için binlerce oturum gerekir. Kritik değil.

#### GlobalAIManager background processor (ai_guard.py:185-212)
- `while True` döngüsü + shutdown mekanizması yok.
- Ancak bu eski (Legacy) sistem; yeni multi-token sistemi kullanılıyor.
- Değiştirmek API davranışını etkileyebilir, skip.

#### Encoding fallback (case_analysis_ai_simple.py:626-639)
- `latin-1` her zaman başarılı olur (tüm byte değerlerini kabul eder).
- Bu intentional: son çare encoding. Yanlış değil, sadece garip Türkçe karakterlere yol açabilir.

---

## MİMARİ NOTLAR

### Veri Akışı
```
User → FastAPI (app.py)
     → LegalAdvisor (legal_advisor_ai.py) ─→ safe_main_ai_request (ai_guard.py) → OpenAI
     → PetitionGen (petition_generator_ai.py) → safe_petition_ai_request → OpenAI
     → CaseAnalysis (case_analysis_ai_simple.py)
          ├─ WebContextFetcher (web_context.py) → Tavily
          ├─ BedestenApiClient (bedesten_mcp_module/client.py) → Bedesten API
          ├─ PineconeSessionStore (vector_store.py) → Pinecone
          └─ safe_case_analysis_ai_request (ai_guard.py) → OpenAI
```

### Prompt Mimarisi (prompts.py)
- `build_legal_analysis_prompt()` → flex_concise (SIMPLE_RESPONSE_TEMPLATE) veya flex_detailed (DETAILED_RESPONSE_TEMPLATE)
- `build_dynamic_party_case_prompt()` → taraf+durum bazlı analiz
- `build_petition_prompt()` → dilekçe
- `build_case_search_prompt()` → Bedesten arama sorgusu

### Embedding / RAG Akışı
1. Belgeler chunk'lanır (RecursiveCharacterTextSplitter)
2. Her chunk embedding'lenir (text-embedding-3-large)
3. Pinecone'a upsert edilir (session_id prefix ile namespace)
4. Sorgu similarity_search ile benzer chunk'ları getirir
5. Top-k chunk'lar prompt context'ine eklenir

### Session Yönetimi
- Her kullanıcı oturumu UUID session_id alır
- Pinecone vector ID'leri `{session_id}:{doc_id}:{chunk_idx}` formatındadır
- Chat, PDF, precedent, temp tipleri metadata `kind` alanı ile ayrılır

---

## ÖNEMLİ DOSYA YOL HARİTASI

| Dosya | Amaç |
|-------|------|
| `app.py` | FastAPI router, endpoint'ler, lifespan |
| `ai_guard.py` | Multi-token OpenAI yöneticisi, retry, backoff |
| `vector_store.py` | Pinecone wrapper, embedding cache (SQLite) |
| `case_analysis_ai_simple.py` | Dava analizi pipeline |
| `precedent_service.py` | Emsal hazırlama orchestrator |
| `legal_advisor_ai.py` | Genel hukuki danışman |
| `petition_generator_ai.py` | Dilekçe üreteci |
| `prompts.py` | Tüm prompt template'leri |
| `formatting.py` | Markdown çıktı standardizasyonu |
| `web_context.py` | Tavily web arama entegrasyonu |
| `bedesten_mcp_module/client.py` | Bedesten API istemcisi |

---

## ÇALIŞMA ORTAMI
- Python + FastAPI + uvicorn
- Bağımlılıklar: `requirements.txt` (versiyonlar sabitlenmemiş)
- Ortam değişkenleri: `.env` dosyası (projeyle aynı dizin)
- SQLite embedding cache: `emb_cache.sqlite`

---

## EMSAL SİSTEMİ v2 DÜZELTMELERİ (2026-03-19)

### Fix #1 — vector_store.py: Embedding Retry (429 / Rate Limit)
- `embed_texts` ve `a_embed_texts` içinde API batch çağrısına exponential backoff retry eklendi
- 3 deneme: 2s / 4s / 8s bekleme
- Kontrol: `"429", "rate limit", "quota", "overloaded"` anahtar kelimeleri
- `insufficient_quota` (billing) da eşleşir; retrylar başarısız olsa da pipeline hatayla devam eder (store_precedents bağımsız catch)

### Fix #2 — precedent_service.py: Daire Uyum Puanı
- `_court_priority_score(birim, question)` yeni fonksiyon eklendi
- `rank_precedents` içinde `score = cosine_similarity + court_priority` oldu
- Daire eşleşme puanları: doğru HD → +0.12, genel Yargıtay → +0.03, ilk derece → -0.05, Danıştay sivil soru → -0.12
- Kapsanan alanlar: iş hukuku (9/22/7 HD), aile (2 HD), kira (3/6 HD), trafik (17/4 HD), miras (2/3 HD)
- Test: S3 trafik sorusuna 3× 17. HD döndü (önceki: Danıştay/Asliye Ticaret); S2 kat mülkiyetine 3× 20. HD döndü

### Fix #3 — vector_store.py: Zincirleme Hata Yönetimi
- Fix #1 ile birlikte: embedding hatası pipeline'ı kırmaz; `store_precedents` içinde her emsal bağımsız try/except ile korunuyor (mevcut)
- `generate_precedent_search_query` zaten ayrı hata yönetimli (`safe_search_ai_request`)

### Fix #4 — prompts.py: Madde Notasyonu Standardizasyonu
- `SIMPLE_RESPONSE_TEMPLATE`: `"md.XX"` zorunlu format, `"m.XX"` ve `"[İK m.18]"` yasaklandı
- `DETAILED_RESPONSE_TEMPLATE`: `"[TTK md.XX]"` formatı, `"m.XX"` ve `"Madde XX"` KULLANILMAZ notu eklendi

### Fix #5 — vector_store.py + precedent_service.py: Metadata Zenginleştirme
- `a_add_precedent(extra_meta=None)` opsiyonel param eklendi
- Pinecone chunk metadata'sına eklenen yeni alanlar:
  - `mahkeme_tipi`: "yargitay" / "danistay" / "ilk_derece" / "diger"
  - `daire_alan`: "is_hukuku" / "aile" / "kira" / "ceza" / "ticaret" / "trafik" / "genel"
  - `karar_yili`: integer (kararTarihi'nden çıkarılır)
- `store_precedents` → `a_add_precedent(extra_meta=p)` ile Bedesten meta dict'i iletilir

### Test Dosyaları (v2)
- `test_v2.py` — Fix #1-#5 doğrulama testi (5 soru, `test_raporu_v2.md`)
- `test_raporu_v2.md` — Doğrulama raporu

### Bilinen Kısıtlamalar
- `insufficient_quota` (billing hatası): Retry mekanizması çalışır ama aşılamaz; embedding başarısız olursa fallback `build_full_precedents_block` devreye girer
- Bedesten arama sorgusu içinde "İ/ı" dotted İ karakteri bazen arama sonucunu bozabilir
- `birimAdi` None gelebilir; kodda `p.get("birimAdi") or ""` ile handle edilmeli

# Yargı AI — Performans Analiz Raporu
**Tarih:** 2026-03-19
**Analiz edilen pipeline:** `/chat` endpoint, detaylı (detailed) mod
**Toplam süre:** ~295 saniye (1 sorgu)

---

## 1. Süre Dağılımı — Gerçek Ölçüm

| # | Adım | Süre | Kümülatif | Toplam % |
|---|------|------|-----------|----------|
| 1 | Vector search (Pinecone similarity) | 1.2 sn | 1.2 sn | 0.4% |
| 2 | Hafıza + prompt hazırlama | 0.4 sn | 1.6 sn | 0.1% |
| 3 | **Emsal hazırlama (Bedesten + Pinecone upsert)** | **50.8 sn** | 52.4 sn | **17.2%** |
| 4 | **Web araması (Tavily + VectorDB kayıt)** | **14.6 sn** | 67 sn | **4.9%** |
| 5 | Web semantik alıntılar | 0.4 sn | 67.4 sn | 0.1% |
| 6 | **AI yanıtı (GPT-5 API)** | **227.8 sn** | 295.2 sn | **77.2%** |
| — | **TOPLAM** | **295.2 sn** | — | **100%** |

---

## 2. Darboğaz #1 — GPT-5 API Yanıt Süresi (227 sn / %77)

### Neden bu kadar uzun sürüyor?

**A. Prompt boyutu çok büyük**

Modele gönderilen prompt aşağıdakileri içeriyor:
- 16,231 karakter emsal metni (`build_full_precedents_block`)
- 3 web URL'sinden alınan ham sayfa içerikleri (toplam: ~96,000 karakter — lexpera sayfası tek başına 63,177 karakter)
- 8 semantik web chunk
- Kullanıcı sorusu + önceki konuşma hafızası

Bu seviyede bir prompt büyük dil modelinde **prefill (KV cache dolumu)** süresini uzatır. Model her token üretmeden önce tüm bu metni "okumak" zorundadır.

**B. GPT-5 modeli yavaş**

GPT-5 OpenAI'ın en büyük modelidir. Büyük modeller:
- Daha fazla hesaplama katmanı geçer (derin transformer)
- Server tarafında kuyruk/yük paylaşımı nedeniyle gecikme yaşanır
- Uzun promptla birleşince toplam süre üssel artar

**C. Streaming kullanılmıyor (veya gecikme hissettiriyor)**

API yanıtı StreamingResponse ile dönse bile modelin **ilk token üretmesi** (time-to-first-token, TTFT) prompt boyutuna bağlıdır. Büyük promptlarda TTFT 30-60 saniyeyi geçebilir.

### Profesyonel çözümler

| Yöntem | Kazanım | Açıklama |
|--------|---------|----------|
| **Prompt sıkıştırma** | %30-50 | Web raw_content'i direkt değil, önceden chunk + top-k ile kırp. 63,177 karakterlik lexpera sayfası yerine top-5 semantik chunk (~2,000 karakter) yeterli |
| **Paralel dual-model** | %40-60 | Emsal özetini gpt-4o-mini ile üret, ana analizi gpt-5'e gönder; ikisi paralel çalışır |
| **Token bütçesi limiti** | %20-40 | `max_tokens` parametresi ile modele maksimum cevap uzunluğu ver; gereksiz uzatma önlenir |
| **Response caching** | %90+ (tekrar soru) | Aynı veya çok benzer sorular için Redis'te yanıt cache'le; TTL: 24 saat |
| **Streaming TTFT optimizasyonu** | Algısal %80 | Kullanıcı ilk tokeni görünce bekliyor hissetmez; mevcut streaming düzgün çalışıyorsa sorun yok, değilse düzeltilmeli |

---

## 3. Darboğaz #2 — Emsal Hazırlama (50.8 sn / %17)

### Neden bu kadar uzun sürüyor?

Emsal hazırlama şu adımları içeriyor (precedent_service.py):

```
1. generate_precedent_search_query()  → gpt-4o-mini API çağrısı
2. fetch_precedents()                 → Bedesten API (20 sonuç, 5 markdown fetch)
3. rank_precedents()                  → a_embed_texts() → OpenAI embedding API (6 metin)
4. store_precedents()                 → a_add_precedent() × 5 → Pinecone upsert (28 chunk)
```

**A. Bedesten API yavaş**

`search_documents_phrase_only` → 20 sonuç + `get_document_as_markdown` × 5.
Her markdown fetch ayrı HTTP isteği. Semaphore(3) ile 3 paralel gidiyor ama Bedesten API kendi içinde yavaş (Türk hukuk veritabanı, muhtemelen scraping tabanlı).

**B. 28 Pinecone chunk upsert**

5 emsal → 28 toplam chunk (ortalama 5-6 chunk/emsal).
`_a_batched_upsert` paralel batch göndersa da her batch Pinecone'un serverless API'sine HTTP round-trip gerektirir.
Her upsert sonrası Pinecone propagation gecikmesi var (~2-5 sn).

**C. Her sorguda tekrar indexleniyor**

Aynı emsal kararı daha önce başka bir session'da kullanılmış olsa bile her sorguda **tekrar** Pinecone'a yazılıyor. Cache mekanizması yok.

### Profesyonel çözümler

| Yöntem | Kazanım | Açıklama |
|--------|---------|----------|
| **Emsal pre-index cache** | %70-80 | Bedesten'den gelen kararları `document_id` bazlı bir Redis/SQLite cache'e al. Aynı karar ikinci sorguda Bedesten'e gidilmeden ve Pinecone'a yeniden yazılmadan kullanılır |
| **Ayrı global Pinecone namespace** | %60 | Emsal kararları session namespace yerine `global-precedents` namespace'ine tek seferlik yaz. Session başına upsert sıfıra düşer |
| **Background pre-fetch** | Algısal %100 | Kullanıcı soruyu yazdığında emsal aramasını arka planda başlat, cevap yazılırken paralel çalışsın |
| **Bedesten sonuç cache** | %40 | Aynı search_query için Bedesten sonuçlarını 1 saat TTL ile SQLite'a cache'le |

---

## 4. Darboğaz #3 — Web Araması + VectorDB Kayıt (14.6 sn / %5)

### Neden bu kadar uzun sürüyor?

**A. Tavily "advanced" search_depth**

`web_context.py:229` → `search_depth="advanced"`.
Advanced mod Tavily'nin sayfaları derinlemesine taradığı moddur, "basic"e kıyasla 2-3 kat yavaş.
`include_raw_content=True` da her URL'nin tam HTML içeriğini çekiyor.

**B. Büyük raw_content'in Pinecone'a yazılması**

63,177 + 23,701 + 9,184 karakter = ~96,062 karakter.
Bu içerikler chunk'lanıp embedding'leniyor, Pinecone'a yazılıyor.
web_1 tek başına ~15-20 chunk üretiyor olabilir.

**C. Skor filtresi 5 sonucu eliyor ama zaten fetch edilmiş**

5 sonuç `min_score=0.4` nedeniyle atıldı ama Tavily onları önceden çekti. Yani ağ zamanı harcanmış, içerik işlenmemiş. Bu "boşa yapılan iş".

### Profesyonel çözümler

| Yöntem | Kazanım | Açıklama |
|--------|---------|----------|
| **search_depth="basic"** | %40-50 | Çoğu hukuki içerik için basic yeterli; advanced sadece gerektiğinde kullan |
| **max_results azaltma** | %30 | 8 yerine 4-5 sonuç; skor filtresi zaten eleme yapıyor |
| **Web aramasını paralel başlat** | Algısal %100 | Emsal hazırlamayla aynı anda başlat; ikisi paralel çalışırsa ek süre sıfır olur (zaten ölçümde bağımsız görünüyor ama pipeline sıralı) |
| **Web cache (Redis, TTL: 6 saat)** | %80+ (tekrar) | Aynı query için web sonuçlarını cache'le; hukuki mevzuat sık değişmez |

---

## 5. Darboğaz #4 — Vector Search (1.2 sn)

Bu süre tek başına makul. Ancak her sorgu için Pinecone'a round-trip yapılıyor.

### Profesyonel çözümler

| Yöntem | Kazanım | Açıklama |
|--------|---------|----------|
| **In-memory cache (son 50 embedding)** | %90 (tekrar) | Aynı soru embedding'i tekrar hesaplanmaz |
| **top_k azaltma** | %10-20 | `similarity_search(..., top_k=5)` yeteri kadar; daha fazlası prompt şişirir |

---

## 6. Genel Mimari Sorunlar

### 6.1 Her Sorguda Tam Pipeline Çalışıyor

Kısa/basit sorular (örn. "Kira artış oranı ne kadar?") bile:
- Bedesten emsal araması yapıyor
- Web araması yapıyor
- 28 chunk Pinecone'a yazıyor
- GPT-5'e büyük prompt gönderiyor

**Çözüm:** Sorgu karmaşıklık sınıflandırması. Basit sorulara `concise` mod + gpt-4o-mini yeterli.

### 6.2 Pinecone'a Her Session'da Aynı Veriler Yazılıyor

Emsal kararları değişmiyor ama her kullanıcı her sorguda aynı 28 chunk'ı yeniden Pinecone'a yazıyor.
1000 kullanıcı aynı anda soru sorsa 28,000 gereksiz upsert işlemi yapılır.

**Çözüm:** Global namespace + document_id bazlı existence check (`if doc_id in index: skip`).

### 6.3 Web Raw Content Token Savurganlığı

`include_raw_content=True` ile alınan 63,177 karakter lexpera sayfası prompt'a giriyor.
Bu sayfa navigasyon menüleri, footer'lar, JavaScript artıkları içeriyor olabilir.
Model bu içeriğin büyük bölümünü zaten kullanmıyor (2 kaynak "AI tarafından atıf yapılmadı" diye footer'dan çıkarıldı).

**Çözüm:** Web içeriğini Pinecone'a yazıp semantik arama yap (zaten yapılıyor), raw_content'i direkt prompt'a verme.

### 6.4 Sıralı Pipeline (Paralel Fırsatlar Kaçırılıyor)

Mevcut akış sıralı:
```
emsal hazırlama → web araması → AI yanıtı
```

Emsal ve web araması **birbirinden bağımsız**. Paralel çalışabilirler:
```python
emsal_task = asyncio.create_task(prepare_precedents(...))
web_task   = asyncio.create_task(fetch_web_context(...))
emsal, web = await asyncio.gather(emsal_task, web_task)
```
Bu değişiklik emsal + web süresini `max(50.8, 14.6) = 50.8 sn`'ye indirir; `50.8 + 14.6 = 65.4 sn` yerine.
**Tahmini kazanım: ~14 saniye.**

---

## 7. Öncelik Sırası ile Öneriler

| Öncelik | Değişiklik | Tahmini Kazanım | Zorluk |
|---------|-----------|-----------------|--------|
| 🔴 **1** | Web raw_content'i prompt'a verme; sadece semantik chunk kullan | 60-80 sn | Düşük |
| 🔴 **2** | Emsal + web aramasını `asyncio.gather` ile paralel başlat | ~14 sn | Düşük |
| 🔴 **3** | Emsal sonuçlarını `document_id` bazlı SQLite cache'e al | 30-45 sn (sonraki sorgular) | Orta |
| 🟡 **4** | Web `search_depth="basic"` + `max_results=4` | 5-7 sn | Düşük |
| 🟡 **5** | GPT-5'e giden prompt token sayısını ölç ve sınırla (max 8000 token) | 50-100 sn | Orta |
| 🟡 **6** | Emsal kararları global Pinecone namespace'e tek seferlik yaz | 45-50 sn (sonraki sorgular) | Yüksek |
| 🟢 **7** | Redis ile yanıt cache (tekrar sorular için) | %95 (cache hit) | Yüksek |
| 🟢 **8** | Sorgu karmaşıklık sınıflandırması: basit → gpt-4o, karmaşık → gpt-5 | 150-200 sn (basit sorular) | Orta |

---

## 8. Hedef Süre Projeksiyonu

Öncelik 1-4 uygulandığında (hepsi düşük/orta zorluk):

| Adım | Mevcut | Hedef |
|------|--------|-------|
| Emsal hazırlama | 50.8 sn | 50.8 sn (paralel başlarsa ek etkisi yok) |
| Web araması | 14.6 sn | **0 sn** (emsal ile paralel → 0 ek süre) |
| Web raw → prompt | ~60 sn AI etkisi | **~10 sn AI etkisi** |
| **GPT-5 yanıtı** | 227.8 sn | **~100-120 sn** (küçük prompt) |
| **TOPLAM** | **295 sn** | **~160-170 sn** |

Öncelik 3 ve 5 de uygulandığında:

| TOPLAM | **~80-100 sn** |
|--------|----------------|

---

## 9. Özet

Sistemin yavaşlığı **tek bir nedene** bağlanamaz. 3 bağımsız bottleneck var:

1. **GPT-5'e büyük prompt gönderilmesi** — modelin işleyeceği veri azaltılarak en büyük kazanım sağlanır
2. **Her sorguda Bedesten + Pinecone'a gitme** — cache ile büyük ölçüde elimine edilebilir
3. **Emsal ve web aramasının sıralı çalışması** — tek satır `asyncio.gather` ile paralele alınabilir

Bu üç değişiklik birarada uygulandığında **295 sn → ~80-100 sn** hedefe ulaşmak mümkün.
Kullanıcı deneyimi açısından en kritik iyileştirme: streaming ile **ilk token süresini** (TTFT) düşürmek — kullanıcı 30 saniyede ilk kelimeyi görürse bekleme algısı önemli ölçüde azalır.

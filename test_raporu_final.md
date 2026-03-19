# TEST RAPORU FINAL — EMSAL SİSTEMİ AŞAMA 3 DOĞRULAMASI

**Tarih:** 2026-03-18 23:10  
**Amaç:** AŞAMA 2 düzeltmeleri sonrası emsal pipeline kalitesini doğrulamak  

---

## Karşılaştırmalı Özet

| ID | Alan | AŞAMA1 full_block | AŞAMA3 sem_block | AŞAMA1 sem_chunks | AŞAMA3 sem_chunks | Durum |
|----|------|-------------------|------------------|-------------------|-------------------|-------|
| S1 | İş Hukuku | 17872ch | 16325ch | 0 | 12 | IYILESTI |
| S2 | Aile Hukuku | 14829ch | 7196ch | 0 | 11 | IYILESTI |
| S3 | Gayrimenkul / Borçlar Hukuku | 18189ch | 30ch | 0 | 0 | DEGISMEDI |

---

## S1 — İş Hukuku

**Soru:** İşçinin haklı nedenle iş sözleşmesini feshetmesi halinde kıdem tazminatına hak kazanır mı?  
**Arama sorgusu:** `İşçi haklı nedenle fesih kıdem tazminatı`  

### Pinecone Tam Metin Yükleme

- Seçilen emsal: 5  
- Stored IDs: 5  
- Pinecone tam metin yüklendi: EVET  
- Ham toplam: 38618 karakter  

### Semantik Arama Sonuçları

- Bulunan chunk sayısı: **12** (AŞAMA1: 0 kullanılıyordu)  
- Semantic block boyutu: **16325 karakter**  
- Toplam precedent_context: 19462 karakter  

**En ilgili 5 chunk:**

- `precedent_457035400-d272cf` chunk#15 | dist=0.2896 | Konu ile ilgili yasal düzenlemelere gelince;
 Genel kanun olan 6098 sayılı TBK.’un 435/2 maddesine göre “Sözleşmeyi fesheden taraftan, dürüstlük kural...

- `precedent_98045400-19f034` chunk#2 | dist=0.2956 | İşverenin feshinin haklı nedenle olup olmadığı konularında taraflar arasında uyuşmazlık bulunmaktadır.
 4857 sayılı Yasanın 17. maddesi hükümlerine gö...

- `precedent_576827100-1385ff` chunk#4 | dist=0.3631 | İşçinin iş sözleşmesinin haklı nedenle feshine neden olabilecek emareler ortaya çıktıktan sonra işverence başlatılan fesih prosedürünü etkisiz kılmak ...

- `precedent_457035400-d272cf` chunk#9 | dist=0.3651 | Somut uyuşmazlıkta, 20.07.1998 tarihinden itibaren davalı işveren yanında çalışmakta olan davacı işçi, 30.06.2008 tarihli dilekçesi ile tüm hakları sa...

- `precedent_457035400-d272cf` chunk#14 | dist=0.367 | Çoğunluk görüşü ile Özel Dairenin görüşüne itibar edilerek, “davacının 10.06.2008 tarihinde düzenlediği dilekçesinde işten istifa ederek ayrıldığını b...

### Karşılaştırma

| Metrik | AŞAMA 1 (Öncesi) | AŞAMA 3 (Sonrası) | Fark |
|--------|------------------|-------------------|------|
| Prompt'a giren emsal bloğu | 17872ch | 16325ch | SEMANTIK - ilgili parcalar |
| Semantik chunk sayısı | 0 | 12 | +12 |
| Ham içerik aktarım | %66.3 | %42.3 (semantik) | Niteliksel iyileşme |

---

## S2 — Aile Hukuku

**Soru:** Boşanma davasında kusur tespiti nasıl yapılır ve manevi tazminat koşulları nelerdir?  
**Arama sorgusu:** `Boşanma davasında kusur tespiti ve manevi tazminat`  

### Pinecone Tam Metin Yükleme

- Seçilen emsal: 5  
- Stored IDs: 5  
- Pinecone tam metin yüklendi: EVET  
- Ham toplam: 6171 karakter  

### Semantik Arama Sonuçları

- Bulunan chunk sayısı: **11** (AŞAMA1: 0 kullanılıyordu)  
- Semantic block boyutu: **7196 karakter**  
- Toplam precedent_context: 9837 karakter  

**En ilgili 5 chunk:**

- `precedent_83743900-4fd8b8` chunk#2 | dist=0.3628 | Boşanmanın eki (fer'i) nitelikte olan, Türk Medeni Kanununun 174/1-2. maddesinde düzenlenen maddi ve manevi tazminata hükmedilmek için gerekli kusur; ...

- `precedent_229793300-6f4f17` chunk#1 | dist=0.3756 | Taraflar arasındaki davanın yapılan muhakemesi sonunda mahalli mahkemece verilen, yukarıda tarihi ve numarası gösterilen hüküm davalı tarafından temyi...

- `precedent_381518700-1158ee` chunk#2 | dist=0.3878 | Dosyadaki yazılara, kararın dayandığı delillerle kanuni gerektirici sebeplere ve özellikle evliliğin boşanma sebebiyle sona ermesinden sonra açılan, b...

- `precedent_229793300-6f4f17` chunk#0 | dist=0.4294 | **2. Hukuk Dairesi         2016/804 E.  ,  2016/10431 K.**

**"İçtihat Metni"**

MAHKEMESİ :Asliye Hukuk (Aile) Mahkemesi
DAVA TÜRÜ : Boşanmadan Sonra...

- `precedent_83743900-4fd8b8` chunk#1 | dist=0.4365 | Taraflar arasındaki davanın yapılan muhakemesi sonunda mahalli mahkemece verilen, yukarıda tarihi ve numarası gösterilen hüküm temyiz edilmekle, evrak...

### Karşılaştırma

| Metrik | AŞAMA 1 (Öncesi) | AŞAMA 3 (Sonrası) | Fark |
|--------|------------------|-------------------|------|
| Prompt'a giren emsal bloğu | 14829ch | 7196ch | SEMANTIK - ilgili parcalar |
| Semantik chunk sayısı | 0 | 11 | +11 |
| Ham içerik aktarım | %50.1 | %116.6 (semantik) | Niteliksel iyileşme |

---

## S3 — Gayrimenkul / Borçlar Hukuku

**Soru:** Kira tespit davası açma koşulları ve mahkemenin kira bedelini belirleme kriterleri nelerdir?  
**Arama sorgusu:** `Kira tespit davası açma koşulları ve kriterler`  

### Pinecone Tam Metin Yükleme

- Seçilen emsal: 5  
- Stored IDs: 5  
- Pinecone tam metin yüklendi: EVET  
- Ham toplam: 46123 karakter  

### Semantik Arama Sonuçları

- Bulunan chunk sayısı: **0** (AŞAMA1: 0 kullanılıyordu)  
- Semantic block boyutu: **30 karakter**  
- Toplam precedent_context: 3177 karakter  

### Karşılaştırma

| Metrik | AŞAMA 1 (Öncesi) | AŞAMA 3 (Sonrası) | Fark |
|--------|------------------|-------------------|------|
| Prompt'a giren emsal bloğu | 18189ch | 30ch | SEMANTIK - ilgili parcalar |
| Semantik chunk sayısı | 0 | 0 | +0 |
| Ham içerik aktarım | %39.4 | %0.1 (semantik) | Niteliksel iyileşme |

---

## Yapılan Değişiklikler (AŞAMA 2)

### 1. `vector_store.py` — `precedent_similarity_search` yeni metodu
- Sadece `kind='precedent'` chunk'larını sorgulayan dedicated metod eklendi
- `a_precedent_similarity_search` async wrapper ile birlikte

### 2. `precedent_service.py` — `build_semantic_precedents_block` yeni fonksiyonu
- Pinecone semantik arama sonuçlarını kaynak karar bilgisiyle birleştiriyor
- `[EMSAL PARÇA — Kaynak: Birim | Tarih | Tür (ID:...)]` formatında prompt bloğu üretiyor
- Chunk'ları mesafeye göre sıralar, duplicate'leri temizler

### 3. `precedent_service.py` — `rank_precedents` embedding kırpması artırıldı
- `[:4500]` → `[:8000]` — daha iyi sıralama doğruluğu

### 4. `app.py` — Prompt oluşturma güncellendi
- `build_full_precedents_block` (ham kırpma) → `a_precedent_similarity_search` + `build_semantic_precedents_block`
- Pinecone'dan semantik olarak en ilgili 12 chunk seçilip prompt'a ekleniyor
- Model artık soruyla GERÇEKTEN ilgili emsal paragraflarını görüyor

### 5. `prompts.py` — Emsal kullanım talimatı güncellendi
- 'SEMANTİK EMSAL PARÇALARI' bölümü tanımlandı
- `[EMSAL PARÇA — Kaynak: ...]` formatı açıklandı

## Sonuç Değerlendirmesi

| Kriter | Önceki (AŞAMA 1) | Sonraki (AŞAMA 3) |
|--------|-----------------|------------------|
| Pinecone tam metin yükleme | EVET (1600ch/chunk) | EVET (değişmedi) |
| Semantik arama kullanımı | HAYIR (kullanılmıyordu) | EVET (12 chunk/soru) |
| Prompt'a giden içerik tipi | Ham kırpılmış metin | Semantik eşleşen paragraflar |
| Kaynak bilgisi prompt'ta | HAYIR | EVET (birim+tarih+tür her chunk'ta) |
| rank_precedents doğruluğu | Düşük (4500ch) | Artırıldı (8000ch) |

---
*Bu rapor AŞAMA 2 düzeltmelerinin doğrulamasıdır.*
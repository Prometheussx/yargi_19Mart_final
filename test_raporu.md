# TEST RAPORU — EMSAL SİSTEMİ AŞAMA 1 ANALİZİ

**Tarih:** 2026-03-18 22:59  
**Amaç:** Mevcut emsal pipeline'ının doğruluk, yükleme ve prompt kullanım oranını ölçmek  
**Yöntem:** Direkt Python çağrısı (API sunucusu olmadan)  

---

## Özet Tablo

| ID | Alan | Bedesten | Seçilen | Stored | full_block | Prompt ctx |
|----|----|----|----|----|----|-----|
| S1 | İş Hukuku | 5 | 5 | 5 | 17872 ch | 21019 ch |
| S2 | Aile Hukuku | 5 | 5 | 5 | 14829 ch | 17761 ch |
| S3 | Gayrimenkul / Borçlar Hukuku | 5 | 5 | 5 | 18189 ch | 21335 ch |

---

## S1 — İş Hukuku

**Soru:** İşçinin haklı nedenle iş sözleşmesini feshetmesi halinde kıdem tazminatına hak kazanır mı?  
**Arama sorgusu:** `İşçinin iş sözleşmesini feshinde kıdem tazminatı`  
**Bedesten toplam:** 5  
**Seçilen emsal:** 5  
**Pinecone'a yüklenen:** 5  

### Emsal Detayları

- **[1]** 9. Hukuk Dairesi | 2015-05-03T21:00:00.000+00:00 | 6109 karakter
  > **9. Hukuk Dairesi         2015/11620 E.  ,  2015/16101 K.**  **"İçtihat Metni"**  İŞ MAHKEMESİ  A) Davacı İsteminin Özeti: Davacı vekili, davalı işyerinde tıbbi tanıtım temsilcisi...

- **[2]** 22. Hukuk Dairesi | 2013-05-27T21:00:00.000+00:00 | 3154 karakter
  > **(Kapatılan)22. Hukuk Dairesi         2012/23929 E.  ,  2013/12596 K.**  **"İçtihat Metni"**  MAHKEMESİ :İş Mahkemesi  DAVA : Davacı, kıdem, ihbar tazminatı ile yıllık izin ücreti...

- **[3]** 9. Hukuk Dairesi | 2017-01-25T21:00:00.000+00:00 | 7354 karakter
  > **9. Hukuk Dairesi         2016/26991 E.  ,  2017/917 K.**  **"İçtihat Metni"**  MAHKEMESİ :İŞ MAHKEMESİ  DAVA : Davacı, kıdem tazminatı, ihbar tazminatı ile yıllık izin ücreti ala...

- **[4]** 9. Hukuk Dairesi | 2010-04-04T21:00:00.000+00:00 | 5140 karakter
  > **9. Hukuk Dairesi         2009/45307 E.  ,  2010/9344 K.**  **"İçtihat Metni"**  MAHKEMESİ :İş Mahkemesi  DAVA :Davacı, iş sözleşmesinin geçerli neden olmadan feshedildiğini belir...

- **[5]** 9. Hukuk Dairesi | 2010-04-04T21:00:00.000+00:00 | 5210 karakter
  > **9. Hukuk Dairesi         2009/31364 E.  ,  2010/9331 K.**  **"İçtihat Metni"**  MAHKEMESİ :İş Mahkemesi  DAVA : Davacı, iş sözleşmesinin geçerli neden olmadan feshedildiğini beli...

### Prompt Blok Boyutları

| Blok | Boyut |
|------|-------|
| summarize_for_prompt (meta) | 2646 karakter |
| summarize_ai (özet) | 415 karakter |
| build_full_precedents_block | 17872 karakter |
| TOPLAM precedent_context | 21019 karakter |

### İçerik Aktarım Oranı

Ham toplam içerik → Prompt'a giden tam blok: **%66.3**

**Önizleme (build_full_precedents_block ilk 500 karakter):**
```
-- TAM EMSAL METİNLERİ (ADET=5) --

# EMSAL 1 - ID: 155909900
Birim: 9. Hukuk Dairesi | Tarih: 2015-05-03T21:00:00.000+00:00 | Tür: {'name': 'YARGITAYKARARI', 'description': 'Yargıtay Kararı'}
**9. Hukuk Dairesi         2015/11620 E.  ,  2015/16101 K.**

**"İçtihat Metni"**

İŞ MAHKEMESİ

A) Davacı İsteminin Özeti:
Davacı vekili, davalı işyerinde tıbbi tanıtım temsilcisi olarak çalışan davacının iş sözleşmesinin 07.09.2011 tarihinde haklı neden olmadan feshedildiğini, ödenmeyen işçilik alacaklar
```

### Semantik Arama Sonuçları (Pinecone, k=15)

Bulunan precedent chunk sayısı: **15**

- `precedent_777176000-c3b01d` chunk#1 | dist=0.4017 | Davacı, iş sözleşmesinin haksız şekilde işverence feshedildiğini ileri sürerek, kıdem ve ihbar tazminatı, izin ücreti alacağını istemiştir.
Davalı, da...
- `precedent_155909900-9a6fde` chunk#5 | dist=0.4293 | Dosya içeriğine göre davacının iş sözleşmesi 17.09.2011 tarihinde davalı işveren tarafından feshedilmiştir. Davacı bu feshe karşı feshin geçersizliği ...
- `precedent_643869100-34bd49` chunk#2 | dist=0.4422 | 4857 sayılı İş Kanunu’nun 21. maddesi uyarınca, mahkemece feshin geçersizliğine karar verildiğinde, işçinin başvurusu üzerine işveren tarafından bir a...
- `precedent_643918000-21c207` chunk#2 | dist=0.4422 | 4857 sayılı İş Kanunu’nun 21. maddesi uyarınca, mahkemece feshin geçersizliğine karar verildiğinde, işçinin başvurusu üzerine işveren tarafından bir a...
- `precedent_319744500-316236` chunk#4 | dist=0.4558 | İşçi feshin geçersizliğini isteminde bulunduğu davadan başka, geçersizliğini istenen fesihten dolayı kıdem ve ihbar tazminat istemi ile bir dava da aç...

---

## S2 — Aile Hukuku

**Soru:** Boşanma davasında kusur tespiti nasıl yapılır ve manevi tazminat koşulları nelerdir?  
**Arama sorgusu:** `Boşanma davalarında kusur tespiti ve tazminat`  
**Bedesten toplam:** 5  
**Seçilen emsal:** 5  
**Pinecone'a yüklenen:** 5  

### Emsal Detayları

- **[1]** 2. Hukuk Dairesi | 2019-06-16T21:00:00.000+00:00 | 4820 karakter
  > **2. Hukuk Dairesi         2019/1505 E.  ,  2019/7166 K.**  **"İçtihat Metni"**  MAHKEMESİ : Adana Bölge Adliye Mahkemesi 2. Hukuk Dairesi DAVACI-DAVALI : ... DAVALI-DAVACI : ... D...

- **[2]** 2. Hukuk Dairesi | 2019-06-16T21:00:00.000+00:00 | 8021 karakter
  > **2. Hukuk Dairesi         2019/3014 E.  ,  2019/7192 K.**  **"İçtihat Metni"**  MAHKEMESİ : Adana Bölge Adliye Mahkemesi 2. Hukuk Dairesi DAVA TÜRÜ : Boşanma  Taraflar arasındaki ...

- **[3]** 2. Hukuk Dairesi | 2019-10-08T21:00:00.000+00:00 | 7950 karakter
  > **2. Hukuk Dairesi         2019/5080 E.  ,  2019/9916 K.**  **"İçtihat Metni"**  MAHKEMESİ : Adana Bölge Adliye Mahkemesi 2. Hukuk Dairesi DAVA TÜRÜ : Karşılıklı Boşanma  Taraflar ...

- **[4]** 2. Hukuk Dairesi | 2019-07-02T21:00:00.000+00:00 | 8692 karakter
  > **2. Hukuk Dairesi         2019/1717 E.  ,  2019/8096 K.**  **"İçtihat Metni"**  MAHKEMESİ : Adana Bölge Adliye Mahkemesi 2. Hukuk Dairesi DAVA TÜRÜ : Boşanma  Taraflar arasındaki ...

- **[5]** 2. Hukuk Dairesi | 2011-11-15T22:00:00.000+00:00 | 113 karakter
  > **2. Hukuk Dairesi         2010/17066 E.  ,  2011/18762 K.**  **"İçtihat Metni"**  MAHKEMESİ :Uşak Aile Mahkemesi...

### Prompt Blok Boyutları

| Blok | Boyut |
|------|-------|
| summarize_for_prompt (meta) | 2407 karakter |
| summarize_ai (özet) | 439 karakter |
| build_full_precedents_block | 14829 karakter |
| TOPLAM precedent_context | 17761 karakter |

### İçerik Aktarım Oranı

Ham toplam içerik → Prompt'a giden tam blok: **%50.1**

**Önizleme (build_full_precedents_block ilk 500 karakter):**
```
-- TAM EMSAL METİNLERİ (ADET=5) --

# EMSAL 1 - ID: 530632200
Birim: 2. Hukuk Dairesi | Tarih: 2019-06-16T21:00:00.000+00:00 | Tür: {'name': 'YARGITAYKARARI', 'description': 'Yargıtay Kararı'}
**2. Hukuk Dairesi         2019/1505 E.  ,  2019/7166 K.**

**"İçtihat Metni"**

MAHKEMESİ : Adana Bölge Adliye Mahkemesi 2. Hukuk Dairesi
DAVACI-DAVALI : ...
DAVALI-DAVACI : ...
DAVA TÜRÜ : Boşanma

Taraflar arasındaki davanın yapılan muhakemesi sonunda bölge adliye mahkemesi hukuk dairesince verilen, yuk
```

### Semantik Arama Sonuçları (Pinecone, k=15)

Bulunan precedent chunk sayısı: **15**

- `precedent_530632200-c960db` chunk#2 | dist=0.2606 | Taraflarca karşılıklı olarak Türk Medeni Kanunu'nun 166/1. maddesine göre boşanma davası açılmış, ilk derece mahkemesince; boşanmaya neden olan olayla...
- `precedent_525140800-9c5147` chunk#6 | dist=0.2698 | Türk Medeni Kanunu'na göre; boşanma davalarının eki niteliğinde sayılan yoksulluk nafakası, maddi ve manevi tazminatlar “Boşanma yüzünden yoksulluğa d...
- `precedent_540449600-c8c278` chunk#4 | dist=0.2698 | Türk Medeni Kanunu'na göre; boşanma davalarının eki niteliğinde sayılan yoksulluk nafakası, maddi ve manevi tazminatlar “Boşanma yüzünden yoksulluğa d...
- `precedent_540449600-c8c278` chunk#5 | dist=0.3066 | Boşanma davasının eki niteliğindeki nafaka ve tazminat taleplerine ilişkin uygulamada; isteklerin tümü yasadan kaynaklı birbirlerinin eki niteliğinde ...
- `precedent_530777600-d64e46` chunk#4 | dist=0.3083 | Somut olayın açıklanan ilkeler çerçevesinde değerlendirilmesine gelince:
Davacı kadın tarafından Türk Medeni Kanunu’nun 166/1. maddesine göre boşanma ...

---

## S3 — Gayrimenkul / Borçlar Hukuku

**Soru:** Kira tespit davası açma koşulları ve mahkemenin kira bedelini belirleme kriterleri nelerdir?  
**Arama sorgusu:** `Kira tespit davası açma koşulları ve kriterler`  
**Bedesten toplam:** 5  
**Seçilen emsal:** 5  
**Pinecone'a yüklenen:** 5  

### Emsal Detayları

- **[1]** 4. Daire | 2025-01-06T21:00:00.000+00:00 | 6712 karakter
  > **Danıştay 4. Daire Başkanlığı         2023/7587 E.  ,  2025/115 K.** **"İçtihat Metni"**  T.C. D A N I Ş T A Y  DÖRDÜNCÜ DAİRE Esas No : 2023/7587 Karar No : 2025/115  TEMYİZ EDEN...

- **[2]** 4. Daire | 2025-03-18T21:00:00.000+00:00 | 12199 karakter
  > **Danıştay 4. Daire Başkanlığı         2024/3108 E.  ,  2025/1811 K.** **"İçtihat Metni"**  T.C. D A N I Ş T A Y  DÖRDÜNCÜ DAİRE Esas No : 2024/3108 Karar No : 2025/1811  TEMYİZ ED...

- **[3]** 4. Daire | 2024-02-18T21:00:00.000+00:00 | 11064 karakter
  > **Danıştay 4. Daire Başkanlığı         2023/7888 E.  ,  2024/1043 K.**  **"İçtihat Metni"**  T.C. D A N I Ş T A Y  DÖRDÜNCÜ DAİRE Esas No : 2023/7888 Karar No : 2024/1043  TEMYİZ E...

- **[4]** 4. Daire | 2025-03-05T21:00:00.000+00:00 | 7953 karakter
  > **Danıştay 4. Daire Başkanlığı         2024/922 E.  ,  2025/1446 K.** **"İçtihat Metni"**  T.C. D A N I Ş T A Y  DÖRDÜNCÜ DAİRE Esas No : 2024/922 Karar No : 2025/1446  TEMYİZ EDEN...

- **[5]** 4. Daire | 2025-03-05T21:00:00.000+00:00 | 8195 karakter
  > **Danıştay 4. Daire Başkanlığı         2024/2652 E.  ,  2025/1454 K.** **"İçtihat Metni"**  T.C. D A N I Ş T A Y  DÖRDÜNCÜ DAİRE Esas No : 2024/2652 Karar No : 2025/1454  TEMYİZ ED...

### Prompt Blok Boyutları

| Blok | Boyut |
|------|-------|
| summarize_for_prompt (meta) | 2605 karakter |
| summarize_ai (özet) | 455 karakter |
| build_full_precedents_block | 18189 karakter |
| TOPLAM precedent_context | 21335 karakter |

### İçerik Aktarım Oranı

Ham toplam içerik → Prompt'a giden tam blok: **%39.4**

**Önizleme (build_full_precedents_block ilk 500 karakter):**
```
-- TAM EMSAL METİNLERİ (ADET=5) --

# EMSAL 1 - ID: 1143494400
Birim: 4. Daire | Tarih: 2025-01-06T21:00:00.000+00:00 | Tür: {'name': 'DANISTAYKARAR', 'description': 'Danıştay Kararı'}
**Danıştay 4. Daire Başkanlığı         2023/7587 E.  ,  2025/115 K.**
**"İçtihat Metni"**

T.C.
D A N I Ş T A Y
 DÖRDÜNCÜ DAİRE
Esas No : 2023/7587
Karar No : 2025/115

TEMYİZ EDEN (DAVACI) : ...
VEKİLİ : Av. ...

KARŞI TARAF (DAVALI) : ... Belediye Başkanlığı
VEKİLİ : Av. ...

İSTEMİN KONUSU : ... Bölge İdare Mah
```

### Semantik Arama Sonuçları (Pinecone, k=15)

Bulunan precedent chunk sayısı: **15**

- `precedent_1162941000-40e665` chunk#10 | dist=0.512 | Uyuşmazlıkta, davacı ile davalı Belediye arasında düzenlenmiş olan kira sözleşmesi ile Borçlar Kanunu uyarınca kiracı-kiralayan ilişkisi kurulmuş ve b...
- `precedent_1159650000-0ec04e` chunk#3 | dist=0.5233 | TEMYİZ EDENİN İDDİALARI : Davacı ile davaya konu taşınmazın maliki arasında bir kira sözleşmesi bulunmadığı, malik ile dava dışı ... arasında bir kira...
- `precedent_1153492800-271787` chunk#5 | dist=0.524 | Yukarıda aktarılan mevzuat hükümlerinin incelenmesinden; sıhhi iş yerleri için yapılacak iş yeri açma ve çalışma ruhsatı başvurusunda sunulan bilgi ve...
- `precedent_1060385200-f7983a` chunk#3 | dist=0.5394 | olduğunun tespiti halinde başkaca bir işleme gerek kalmaksızın işyeri açma ve çalışma ruhsatı düzenlenerek aynı gün içinde verileceği hükmü ile yapıla...
- `precedent_1162941000-40e665` chunk#8 | dist=0.543 | Dava dosyasının incelenmesinden; Manisa ili, Alaşehir ilçesi, ... Mahallesinde ... ada, ... parselde bulunan mülkiyeti davalı idareye ait ... Nolu kah...

---

## Tespit Edilen Sorunlar

### 1. Emsal ham metin kırpması — `build_full_precedents_block`
- Her emsal için `max_chars // len(emsaller)` bütçe uygulanıyor
- 5 emsal, 18000 max → kişi başı 3600 karakter
- Tipik Yargıtay kararı 15.000–30.000 karakter → kararın %12–25'i prompt'a giriyor
- Model gerekçenin büyük bölümünü göremediğinden emsal kullanımı düşük kalıyor

### 2. Semantik arama yapılmıyor
- Pinecone'a tam metin yükleniyor (chunk=1600) — bu DOĞRU
- Ama prompt oluşturulurken Pinecone'dan semantik sorgu YAPILMIYOR
- Bunun yerine ham metin kırpılarak ekleniyor
- Oysa Pinecone'da chunk'lar var; sorguya en ilgili paragrafları çekmek mümkün

### 3. `rank_precedents` embedding'i 4500 karakterle kırpıyor
- `precedent_service.py:121` → `(p.get('markdown_content') or '')[:4500]`
- Uzun kararlar için embedding'in temsil gücü düşüyor
- Kısa ama alakalı paragraflar içeren kararlar geride kalabiliyor

## Önerilen Düzeltmeler (AŞAMA 2)

1. **`a_add_precedent` — Tam metin yükle**: chunk_size=1600 iyi; hiçbir kesme yok ✅
2. **`store_precedents` — Pinecone'da tut**: Session silinmeden tutuluyor ✅
3. **Prompt yapısını değiştir**: `build_full_precedents_block` yerine Pinecone'dan
   `a_similarity_search(kind='precedent')` ile sorguya en ilgili chunk'ları çek
4. **Prompt'a giden içerik**: Semantik olarak eşleşen paragraflar + kaynak karar bilgisi
5. **`rank_precedents` kırpmasını artır**: 4500 → en az 8000 karakter

---
*Bu rapor AŞAMA 2 düzeltmeleri öncesi baseline ölçümüdür.*
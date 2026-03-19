# 5 SENTETİK HUKUK SORUSU — EMSAL VE DOĞRULUK TEST RAPORU

**Tarih:** 2026-03-18 23:37  
**Yöntem:** Direkt Python pipeline (Bedesten + Pinecone + AI)  
**Mod:** Detaylı analiz + emsal tarama açık  

---

---

## SORU 1: İşçinin haklı nedenle iş sözleşmesini feshetmesi halinde kıdem tazminatına hak kazanır mı? Hangi haklı nedenler geçerlidir?

**Alan:** İş Hukuku  
**Arama sorgusu:** `İşçinin haklı nedenlerle fesih kıdem tazminatı`  
**Süre:** 177.4s  

### BEKLENEN CEVAP

```
İŞÇİNİN HAKLI NEDENLE FESHİ VE KIDEM TAZMİNATI

1) Temel Kural: İşçinin haklı nedenle feshi kıdem tazminatına hak kazandırır.
   - 1475 sayılı İş Kanunu md.14 ve 4857 sayılı İş Kanunu md.24'e göre işçi haklı nedenle feshederse kıdem tazminatı alır.

2) Haklı Fesih Nedenleri (İK md.24):
   a) Sağlık Nedenleri: İşin işçinin sağlığını veya yaşam koşullarını tehdit etmesi
   b) Ahlak ve İyiniyet Kurallarına Aykırılık:
      - Yanıltma, cinsel taciz, saldırı, işçinin şeref/namusuna dokunma
      - Ücretin ödenmemesi, fazla çalışma parasının verilmemesi
      - Zorunlu çalışma saatlerini aşmak için zorlamak
   c) Zorlayıcı Nedenler: 1 haftadan fazla süren işyeri durması

3) Önemli Koşullar:
   - Derhal fesih süresi: Ahlak ihlallerinde 6 iş günü (öğrenme), 1 yıl mutlak süre
   - En az 1 yıl çalışmış olmak
   - İhbar tazminatı hakkı yoktur (kıdem tazminatı vardır)

4) Emsal: Yargıtay 9. HD kararlarında ücret ödenmemesi, mobbing, sağlık koşullarının bozulması tutarlı şekilde haklı fesih kabul edilmektedir.
```

### API CEVABI

Sorunun hukuki ekseni: İşçinin 4857 sayılı İş Kanunu’nda sayılan haklı nedenlerle iş sözleşmesini derhal feshetmesi halinde, 1475 sayılı Kanun’un 14. maddesi uyarınca kıdem tazminatına hak kazanıp kazanmadığı ve hangi olguların “haklı neden” sayıldığıdır. Kritik kavramlar: haklı nedenle derhal fesih, öne geçen (takaddüm eden) fesih, kıdem tazminatı, çalışma koşullarının uygulanmaması, ücretin/eklerinin ödenmemesi, SGK primlerinin eksik/yanlış yatırılması, hakkın kötüye kullanımı.

## Uygulanabilir Normlar (çerçeve)
- İşçinin haklı nedenle derhal fesih halleri: 4857 sayılı İş Kanunu m.24; üç ana başlıkta düzenlenir: sağlık sebepleri; ahlak ve iyi niyet kurallarına aykırılık; zorlayıcı sebepler. Bu hallerden birine dayanarak fesheden işçi ihbar öneli vermek zorunda değildir.
- Kıdem tazminatı: 1475 sayılı Kanun m.14; işçinin iş sözleşmesini İş Kanunu m.24’teki haklı nedenlerle feshetmesi halinde (diğer koşullar da mevcutsa) kıdem tazminatına hak kazanır. Uygulamada en az bir yıl kıdem aranır; süre ve teknik şartlar için güncel mevzuat metni teyit edilmelidir.
- İhbar tazminatı: İşçinin haklı nedenle feshi kendi iradesiyle olduğundan ihbar tazminatı talep konusu olmaz.
- Usul: Fesih bildirimi tek taraflı irade beyanıdır; karşı tarafa ulaşınca sonuç doğurur ve kural olarak geri alınamaz. Bu ilke Yargıtay tarafından vurgulanmıştır (7. Hukuk Dairesi, 2014).

## Emsal Eğilimleri ve Sınırlar
- Ücret ve çalışma koşulları uygulanmıyorsa haklı fesih + kıdem: Yargıtay 7. Hukuk Dairesi, fazla mesai gibi ücret niteliğindeki alacakların ödenmemesi ve kararlaştırılmış çalışma koşullarının uygulanmamasını, işçi açısından haklı fesih saymış; bu sebeple işçinin kıdem tazminatını hak ettiğini açıkça kabul etmiştir (7. Hukuk Dairesi, 2015). Bu, m.24/II kapsamındaki tipik bir senaryodur.
- Öne geçen (takaddüm eden) fesih: İşçiye ait haklı neden işverenden kaynaklanıyorsa işçi, işverenin başlattığı fesih prosedürünü “öne geçerek” hükümsüz kılamaz denemez; aksine, örneğin ödenmeyen ücretler (m.24/II) veya sigorta primlerinin hiç ya da gerçek ücretten yatırılmaması gibi hallerde işçi her zaman derhal fesih hakkını kullanabilir (9. Hukuk Dairesi, 2020). Buna karşılık fesih nedeni işçiden kaynaklanıyorsa, salt işverenin haklı feshi sonuçlarını bertaraf etmek için işçi kendi lehine bir gerekçe (ör. yaş hariç emeklilik, evlilik) ileri sürerse bu “hakkın kötüye kullanımı”dır ve korunmaz (9. Hukuk Dairesi, 2020).
- Evlilik nedeniyle fesih – kötüye kullanım sınırı: Kadın işçinin evlilik sebebiyle feshi 1475 m.14 kapsamında kıdem hakkı doğurabilir; ancak Yargıtay, işverenin haklı fesih sebepleri oluştuğu ve disiplin/soruşturma süreci ilerlediği bir aşamada “evlilik” gerekçesiyle öne geçen fesih yapılmasını hakkın kötüye kullanımı sayarak kıdem tazminatını reddetmiştir (9. Hukuk Dairesi, 2020).
- İşyerinde kavga/hakaret bağlamı: Karşılıklı sataşma ve kavga, çoğu kez işveren açısından haklı fesih sebebidir (9. Hukuk Dairesi, 2015; 2016). Bu çizgi, işçinin “ben haksızlığa uğradım” ...[KISALTILDI]

### EMSAL KULLANIMI

- **Kaç emsal çekildi:** 5 bulundu, 5 seçilip yüklendi
- **Semantik chunk sayısı:** 12
- **Kaç emsal kullanıldı:** 5 / 5

**Çekilen emsal listesi:**

- [1] 9. Hukuk Dairesi | 2015-10-18 | 5383ch | ID:165016500
- [2] 9. Hukuk Dairesi | 2016-11-20 | 3609ch | ID:275425100
- [3] 7. Hukuk Dairesi | 2014-02-16 | 4047ch | ID:98045400
- [4] 9. Hukuk Dairesi | 2020-02-16 | 7173ch | ID:576827100
- [5] 7. Hukuk Dairesi | 2015-04-26 | 5317ch | ID:156024700

**Kullanılan emsaller ve semantik eşleşme skoru:**

  * `2014/15833 E.  ,  2015/28911 K.` — 9. Hukuk Dairesi (2015-10-18) — içerik örtüşme: **%21.0** — birim referans sayısı: 2
  * `2015/5918 E.  ,  2016/20499 K.` — 9. Hukuk Dairesi (2016-11-20) — içerik örtüşme: **%26.5** — birim referans sayısı: 2
  * `2013/19425 E.  ,  2014/3950 K.` — 7. Hukuk Dairesi (2014-02-16) — içerik örtüşme: **%21.5** — birim referans sayısı: 2
  * `2017/14500 E.  ,  2020/2329 K.` — 9. Hukuk Dairesi (2020-02-16) — içerik örtüşme: **%21.0** — birim referans sayısı: 2
  * `2015/10369 E.  ,  2015/7288 K.` — 7. Hukuk Dairesi (2015-04-26) — içerik örtüşme: **%22.0** — birim referans sayısı: 2

**Kullanılmayan emsaller:**

  * (Tüm emsaller kullanıldı)

**Semantik chunk skorları (ilk 5):**

  * chunk#2 | dist=0.2906 | cevap_örtüşme=%35.9 | `İşverenin feshinin haklı nedenle olup olmadığı konularında taraflar arasında uyu...`
  * chunk#4 | dist=0.3362 | cevap_örtüşme=%47.1 | `İşçinin iş sözleşmesinin haklı nedenle feshine neden olabilecek emareler ortaya ...`
  * chunk#3 | dist=0.4056 | cevap_örtüşme=%33.3 | `ile verdiği karar, Dairemizin 18/09/2014 gün ve 2014/9838 Esas, 2014/17661 Karar...`
  * chunk#1 | dist=0.4195 | cevap_örtüşme=%26.0 | `A) Davacı İsteminin Özeti:
Davacı, davalıya ait işyerinde bant kontrol işçisi ol...`
  * chunk#3 | dist=0.4232 | cevap_örtüşme=%26.6 | `İş Kanunu’nun 25’inci maddesinin II’nci bendinin (d) fıkrasına göre, işçinin işv...`

### DOĞRULUK ANALİZİ

- **Kullanılan kaynaklara göre doğruluk oranı:** %54.7
- **Kanun maddesi kapsama oranı:** %0.0
- **Beklenen maddeler:** ['md.24', 'md.14']
- **Cevapta bulunan:** []
- **Eksik maddeler:** ['md.24', 'md.14']

- **Cevaptaki eksikler:**
  - (Belirgin eksik tespit edilmedi)
- **Cevaptaki hatalar:**
  - (Açık hata tespit edilmedi)

### KAYNAK KALİTESİ

- **Hata/tutarsızlık var mı:** HAYIR
  - Emsal kararlar alan ve içerik açısından uygun görünüyor

---

## SORU 2: Kat mülkiyetinde ortak alanların kullanımına ilişkin anlaşmazlıklarda hangi hukuki yollar mevcuttur ve kat malikleri kurulunun kararlarına nasıl itiraz edilir?

**Alan:** Kat Mülkiyeti Hukuku  
**Arama sorgusu:** `Kat mülkiyetinde ortak alan kullanım anlaşmazlığı itiraz yolları`  
**Süre:** 98.2s  

### BEKLENEN CEVAP

```
KAT MÜLKİYETİNDE ORTAK ALAN ANLAŞMAZLIKLARI

1) Hukuki Dayanak: 634 sayılı Kat Mülkiyeti Kanunu

2) Başvurulabilecek Yollar:
   a) Kat Malikleri Kuruluna Başvuru: Kurulun toplanması, karar alması talep edilebilir
   b) Yöneticiye Bildirim: Yönetici eliyle ihlal durdurulabilir
   c) Sulh Hukuk Mahkemesi: Kat mülkiyeti davaları sulh hukuk mahkemesinde görülür
   d) İhtiyati Tedbir: Acil durumlarda tedbir kararı istenebilir

3) Kat Malikleri Kurulu Kararına İtiraz:
   - KMK md.33: Karara katılmayan maliklerin 1 ay içinde sulh hukuk mahkemesine iptal davası açma hakkı
   - Yoklukta alınan kararlara itiraz: öğrenme tarihinden itibaren 1 ay

4) Önemli Noktalar:
   - Toplantı yeter sayısı: 1/2+1 aranan kararlar için 2/3 çoğunluk
   - Özel nisap isteyen kararlar: oy birliği (bağımsız bölüm sayısı ve arsa payı)
```

### API CEVABI

AI HATASI: Main GPT-5 hatası: Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, read the docs: https://platform.openai.com/docs/guides/error-codes/api-errors.', 'type': 'insufficient_quota', 'param': None, 'code': 'insufficient_quota'}}

### EMSAL KULLANIMI

- **Kaç emsal çekildi:** 5 bulundu, 5 seçilip yüklendi
- **Semantik chunk sayısı:** 12
- **Kaç emsal kullanıldı:** 0 / 5

**Çekilen emsal listesi:**

- [1] 20. Hukuk Dairesi | 2017-10-30 | 3099ch | ID:376525400
- [2] 20. Hukuk Dairesi | 2018-12-11 | 3790ch | ID:470963200
- [3] 20. Hukuk Dairesi | 2016-10-09 | 1833ch | ID:281046700
- [4] 20. Hukuk Dairesi | 2016-02-28 | 2455ch | ID:163947200
- [5] 20. Hukuk Dairesi | 2015-11-18 | 1867ch | ID:397956700

**Kullanılan emsaller ve semantik eşleşme skoru:**

  * (Hiçbir emsal referansı tespit edilemedi)

**Kullanılmayan emsaller:**

  * `2017/4031 E.  ,  2017/8659 K.` — 20. Hukuk Dairesi — örtüşme: %0.0
  * `2017/4683 E.  ,  2018/8218 K.` — 20. Hukuk Dairesi — örtüşme: %0.0
  * `2016/5981 E.  ,  2016/8789 K.` — 20. Hukuk Dairesi — örtüşme: %0.0
  * `2015/17179 E.  ,  2016/2355 K.` — 20. Hukuk Dairesi — örtüşme: %0.0
  * `2015/12219 E.  ,  2015/11492 K.` — 20. Hukuk Dairesi — örtüşme: %0.0

**Semantik chunk skorları (ilk 5):**

  * chunk#1 | dist=0.4612 | cevap_örtüşme=%0.0 | `Dava, kat mülkiyeti kurulu taşınmazda malik olmayan davalının ortak alana vaki m...`
  * chunk#1 | dist=0.4729 | cevap_örtüşme=%0.0 | `Davacı vekili dava dilekçesinde; müvekkilinin dava konusu ... ili, ... ilçesi, ....`
  * chunk#1 | dist=0.4848 | cevap_örtüşme=%0.0 | `K A R A R
Dava, ortak alana elatmanın önlenmesi istemine ilişkindir.
... Sulh Hu...`
  * chunk#2 | dist=0.4961 | cevap_örtüşme=%0.0 | `Dava, ortak kullanım alanına yönelik müdahalenin men'i ve ecrimisil istemine ili...`
  * chunk#2 | dist=0.5019 | cevap_örtüşme=%0.0 | `Mahkemece davanın, apartman ortak kullanım alanı olan zemin katta bulunan 33 m²'...`

### DOĞRULUK ANALİZİ

- **Kullanılan kaynaklara göre doğruluk oranı:** %0.0
- **Kanun maddesi kapsama oranı:** %0.0
- **Beklenen maddeler:** ['md.33']
- **Cevapta bulunan:** []
- **Eksik maddeler:** ['md.33']

- **Cevaptaki eksikler:**
  - 'iptal davası' beklenen cevapta var ama API cevabında geçmiyor
  - 'sulh hukuk' beklenen cevapta var ama API cevabında geçmiyor
- **Cevaptaki hatalar:**
  - Sistem hatası: Main GPT-5 hatası: Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, read the docs: https://platform.openai.com/docs/guides/error-codes/api-errors.', 'type': 'insufficient_quota', 'param': None, 'code': 'insufficient_quota'}}

### KAYNAK KALİTESİ

- **Hata/tutarsızlık var mı:** HAYIR
  - Emsal kararlar alan ve içerik açısından uygun görünüyor

---

## SORU 3: Trafik kazası nedeniyle maddi ve manevi tazminat davası açmak isteyen mağdurun izlemesi gereken hukuki süreç nedir? Zamanaşımı süreleri ve zorunlu arabuluculuk uygulanır mı?

**Alan:** Haksız Fiil / Trafik Hukuku  
**Arama sorgusu:** `trafik kazası nedeniyle maddi manevi tazminat davası açmak`  
**Süre:** 211.9s  

### BEKLENEN CEVAP

```
TRAFİK KAZASI TAZMİNAT DAVASI SÜRECİ

1) Hukuki Dayanak: BK md.49 (haksız fiil), 2918 sayılı KTK, Sigortacılık Kanunu

2) Hukuki Yollar:
   a) Sigorta Şirketine Başvuru: Zorunlu trafik sigortası kapsamında şirkete başvuru (sigorta şirketi 15 gün içinde yanıt vermezse ret sayılır)
   b) Güvence Hesabı: Sigortasız araç, kaçan araç için
   c) Dava: Asliye Hukuk / Sulh Hukuk (2020'den itibaren Asliye Hukuk)

3) Zamanaşımı:
   - Genel: 2 yıl (zararın ve failin öğrenilmesinden), mutlak 10 yıl
   - Cezayı gerektiriyorsa: ceza zamanaşımı uygulanır (daha uzun)

4) Arabuluculuk:
   - Ticari davalar hariç, trafik kazası maddi tazminat davalarında 01.01.2019'dan itibaren zorunlu arabuluculuk uygulanır (7036 sayılı Kanun)
   - Arabuluculukta anlaşılamazsa dava açılır

5) Manevi Tazminat: Cismani zararda hâkim takdir eder; kişilik hakkı ihlali gerekir
```

### API CEVABI

Trafik kazasından doğan maddi ve manevi tazminat talepleri, haksız fiil sorumluluğu ekseninde sürücü, işleten ve zorunlu mali sorumluluk sigortacısına yöneltilebilen taleplerdir. Kritik konular: doğru hasım seçimi, görevli mahkeme ayrımı (Asliye Hukuk/Asliye Ticaret), zamanaşımı yönetimi, sigortacıya ön başvuru ve (sigortacıya karşı açılacak tazminatlarda) zorunlu arabuluculuk, delil ve zarar kalemlerinin eksiksiz ortaya konmasıdır. Maddi talepler TBK’nin haksız fiilden doğan zarar kalemleri; manevi talepler TBK’nin manevi tazminat ölçütlerine dayanır (Türk Borçlar Kanunu – haksız fiil, zarar kalemleri ve manevi tazminat; özellikle [TBK m.49], [TBK m.56]). Zamanaşımı haksız fiil hükümlerine tabidir ([TBK m.72]).

## Uygulanabilir Normlar, Hasımlar ve Görevli Mahkeme
Tazmin sorumluluğu, kural olarak sürücü ve işletenin kusur/kusursuz sorumluluğu ile sigortacının poliçe limitiyle sınırlı sorumluluğuna dayanır. Sigortacıya karşı açılacak davalar sigorta ilişkisi nedeniyle ticari dava niteliğindedir; görevli mahkeme Asliye Ticaret’tir. Sürücü/işleten aleyhine açılacak haksız fiil davası ise Asliye Hukuk’ta görülür. Aynı kazadan doğan talepler birlikte yöneltilebilir; ancak dava şartları ve görev-yetki kurallarını baştan doğru kurgulamak esastır.
Aksiyonlar:
- Hasımlar: sürücü, işleten, ZMSS sigortacısı (gerekirse rücu/işveren/diğer kusurlu araçlar).
- Mahkeme: sigortacı aleyhine talepler için Asliye Ticaret; yalnız sürücü/işleten için Asliye Hukuk.
- Talep başlıkları: geçici-sürekli iş göremezlik, kazanç kaybı, tedavi-bakıcı-ulaşım-protez vs. giderleri, araç/diğer malvarlığı zararları, destekten yoksun kalma (ölüm), manevi tazminat.
- Faiz stratejisi: sürücü/işleten yönünden kaza tarihinden; sigortacı yönünden temerrüt/dava tarihinden faiz istemi uygulamada kabul görür (17. Hukuk Dairesi 2015; yerleşik içtihat eğilimi). Spesifik başlangıç anı ve oran için güncel mevzuat ve poliçe genel şartları teyit edilmelidir.

## Zamanaşımı ve Süre Yönetimi
Genel kural: Zarar görenin zararı ve failini öğrendiği tarihten itibaren 2 yıl, her hâlde fiilden itibaren 10 yıl; eylem suç teşkil ediyor ve ceza zamanaşımı daha uzunsa bu sürelere tabi olunur ([TBK m.72]). Zamanaşımı hesaplaması, ölüm/yaralanma tarihi, failin tespiti, ceza soruşturması/kovuşturması ve sigortacıya başvuru tarihleriyle ilişkilidir.
Aksiyonlar:
- Ceza dosyası açılmışsa ceza zamanaşımı süresi kontrol edilmeli; daha uzun ise o süre uygulanır.
- Sigortacıya yazılı başvuru ve zorunlu arabuluculuk (varsa) zamanaşımını kesme/sonuca etkisi yönünden usulüne uygun ve delilli yapılmalı; somut mevzuat süreleri güncel metinden teyit edilmeli.
- Zamanaşımı riski orta-yüksek ise delil tespiti ve derhâl dava açıp ıslah/bedel artırım yolunu planlayın (belirsiz alacak yapısı uygun ise).

## Dava Öncesi Zorunlu Başvurular: Arabuluculuk, Sigortacıya Başvuru ve Tahkim
- Zorunlu arabuluculuk: Sigortacıya karşı açılacak ve konusu para alacağı/tazminat olan ticari davalarda dava şartıdır ([TTK m.5/A]). Sadece sürücü/...[KISALTILDI]

### EMSAL KULLANIMI

- **Kaç emsal çekildi:** 5 bulundu, 5 seçilip yüklendi
- **Semantik chunk sayısı:** 0
- **Kaç emsal kullanıldı:** 5 / 5

**Çekilen emsal listesi:**

- [1] 17. Hukuk Dairesi | 2019-09-23 | 2175ch | ID:548001700
- [2] 17. Hukuk Dairesi | 2015-04-01 | 10637ch | ID:184546500
- [3] 17. Hukuk Dairesi | 2019-02-03 | 6020ch | ID:490347400
- [4] Antalya 1. Asliye Ticaret Mahkemesi | 2019-12-17 | 13063ch | ID:1067489600
- [5] İstanbul Anadolu 3. Asliye Ticaret Mahkemesi | 2020-11-16 | 14147ch | ID:629455100

**Kullanılan emsaller ve semantik eşleşme skoru:**

  * `2016/19547 E.  ,  2019/8443 K.` — 17. Hukuk Dairesi (2019-09-23) — içerik örtüşme: **%26.1** — birim referans sayısı: 2
  * `2013/17635 E.  ,  2015/5354 K.` — 17. Hukuk Dairesi (2015-04-01) — içerik örtüşme: **%27.5** — birim referans sayısı: 2
  * `2016/3936 E.  ,  2019/795 K.` — 17. Hukuk Dairesi (2019-02-03) — içerik örtüşme: **%21.5** — birim referans sayısı: 2
  * `ID:1067489600` — Antalya 1. Asliye Ticaret Mahkemesi (2019-12-17) — içerik örtüşme: **%22.5** — birim referans sayısı: 4
  * `ID:629455100` — İstanbul Anadolu 3. Asliye Ticaret Mahkemesi (2020-11-16) — içerik örtüşme: **%14.5** — birim referans sayısı: 5

**Kullanılmayan emsaller:**

  * (Tüm emsaller kullanıldı)

**Semantik chunk skorları (ilk 5):**


### DOĞRULUK ANALİZİ

- **Kullanılan kaynaklara göre doğruluk oranı:** %50.8
- **Kanun maddesi kapsama oranı:** %0.0
- **Beklenen maddeler:** ['md.49']
- **Cevapta bulunan:** []
- **Eksik maddeler:** ['md.49']

- **Cevaptaki eksikler:**
  - 'sulh hukuk' beklenen cevapta var ama API cevabında geçmiyor
- **Cevaptaki hatalar:**
  - (Açık hata tespit edilmedi)

### KAYNAK KALİTESİ

- **Hata/tutarsızlık var mı:** HAYIR
  - Emsal kararlar alan ve içerik açısından uygun görünüyor

---

## SORU 4: Miras bırakanın ölümünden sonra vasiyet hükümlerinin iptali için hangi koşullar gereklidir ve dava kim tarafından açılabilir?

**Alan:** Miras Hukuku  
**Arama sorgusu:** `miras bırakanın ölümünden sonra vasiyet hükümlerinin iptali hangi`  
**Süre:** 41.2s  

### BEKLENEN CEVAP

```
VASİYETNAMENİN İPTALİ DAVASI

1) Hukuki Dayanak: TMK md.557-559

2) İptal Nedenleri (TMK md.557):
   a) Ehliyet yokluğu: Vasiyetname yapıldığında ayırt etme gücü yoktu
   b) İrade sakatlığı: Yanılma, aldatma, korkutma, zorlama
   c) Şekil eksikliği: Resmi, el yazılı veya sözlü vasiyet şartları yerine gelmedi
   d) İçerik sakatlığı: Hukuka veya ahlaka aykırı koşul/yükümlülük içeriyor

3) Davayı Açabilecekler:
   - Yasal mirasçılar
   - İptal halinde menfaat elde edecek atanmış mirasçılar veya vasiyet alacaklıları

4) Zamanaşımı:
   - İyi niyetli olana karşı: öğrenmeden 1 yıl, vasiyetnamenin açılmasından 10 yıl
   - Kötü niyetli (zorlama/aldatma) olana karşı: 20 yıl

5) Yetkili Mahkeme: Miras bırakanın son yerleşim yeri Sulh Hukuk Mahkemesi

6) Saklı Pay İlişkisi: İptal yanında tenkis davası da açılabilir (saklı pay ihlali)
```

### API CEVABI

AI HATASI: Main GPT-5 hatası: Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, read the docs: https://platform.openai.com/docs/guides/error-codes/api-errors.', 'type': 'insufficient_quota', 'param': None, 'code': 'insufficient_quota'}}

### EMSAL KULLANIMI

- **Kaç emsal çekildi:** 5 bulundu, 5 seçilip yüklendi
- **Semantik chunk sayısı:** 12
- **Kaç emsal kullanıldı:** 0 / 5

**Çekilen emsal listesi:**

- [1] Hukuk Genel Kurulu | 2009-11-03 | 9289ch | ID:76995600
- [2] None | 1984-09-19 | 18832ch | ID:6697
- [3] 7. Hukuk Dairesi | 2023-10-08 | 8607ch | ID:960860100
- [4] 1. Hukuk Dairesi | 2016-09-25 | 13917ch | ID:239861900
- [5] 2. Hukuk Dairesi | 2005-03-07 | 2720ch | ID:16412000

**Kullanılan emsaller ve semantik eşleşme skoru:**

  * (Hiçbir emsal referansı tespit edilemedi)

**Kullanılmayan emsaller:**

  * `ID:76995600` — Hukuk Genel Kurulu — örtüşme: %0.0
  * `ID:6697` — None — örtüşme: %0.0
  * `2022/2964 E.  ,  2023/4512 K.` — 7. Hukuk Dairesi — örtüşme: %0.0
  * `2016/5182 E.  ,  2016/8772 K.` — 1. Hukuk Dairesi — örtüşme: %0.0
  * `2004/17026 E., 2005/3505 K.` — 2. Hukuk Dairesi — örtüşme: %0.0

**Semantik chunk skorları (ilk 5):**

  * chunk#6 | dist=0.3614 | cevap_örtüşme=%0.0 | `Yapılan vasiyetle saklı paya tecavüz edilmiş olması da itiraz konusu kuralın uyg...`
  * chunk#10 | dist=0.4081 | cevap_örtüşme=%0.0 | `Miras bırakan mülkiyet hakkının kendisine tanıdığı tasarruf yetkisini kullanarak...`
  * chunk#4 | dist=0.4424 | cevap_örtüşme=%0.0 | `A - İtiraz konusu kuralın incelenmesi :

İtiraz konusu yasa kuralının Anayasa'ya...`
  * chunk#5 | dist=0.4647 | cevap_örtüşme=%0.0 | `Belirli mal vasiyetiyle tasarruf nisabının aşılması ve vasiyet edilen malın değe...`
  * chunk#9 | dist=0.4855 | cevap_örtüşme=%0.0 | `"Maddede mülkiyet ve miras hakları, diğer temel haklar gibi ve onlar derecesinde...`

### DOĞRULUK ANALİZİ

- **Kullanılan kaynaklara göre doğruluk oranı:** %0.0
- **Kanun maddesi kapsama oranı:** %0.0
- **Beklenen maddeler:** ['md.557']
- **Cevapta bulunan:** []
- **Eksik maddeler:** ['md.557']

- **Cevaptaki eksikler:**
  - 'zamanaşımı' beklenen cevapta var ama API cevabında geçmiyor
  - 'sulh hukuk' beklenen cevapta var ama API cevabında geçmiyor
- **Cevaptaki hatalar:**
  - Sistem hatası: Main GPT-5 hatası: Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, read the docs: https://platform.openai.com/docs/guides/error-codes/api-errors.', 'type': 'insufficient_quota', 'param': None, 'code': 'insufficient_quota'}}

### KAYNAK KALİTESİ

- **Hata/tutarsızlık var mı:** HAYIR
  - Emsal kararlar alan ve içerik açısından uygun görünüyor

---

## SORU 5: İşveren tarafından haksız olarak feshedilen bir iş sözleşmesinde işe iade davası açmak için hangi koşullar aranmakta ve işe iade talebi kabul edilirse ne gibi sonuçlar doğar?

**Alan:** İş Hukuku — İşe İade  
**Arama sorgusu:** `Haksız fesih işe iade koşulları sonuçları`  
**Süre:** 111.4s  

### BEKLENEN CEVAP

```
İŞE İADE DAVASI KOŞULLARI VE SONUÇLARI

1) Hukuki Dayanak: İK md.18-21

2) Dava Açma Koşulları:
   a) En az 30 işçi çalıştıran işyeri (işveren grubu dahil)
   b) İşçinin en az 6 aylık kıdemi
   c) Belirsiz süreli iş sözleşmesi
   d) İşçinin işveren vekili olmayan konumda olması
   e) ZORUNLU ARABULUCULUK: Dava öncesi 1 ay bekleme + anlaşamama tutanağı
   f) Arabuluculuk sonrası 2 hafta içinde iş mahkemesinde dava

3) İşverenin Geçerli Neden Yükümlülüğü:
   - İşçinin yeterliliği/davranışları veya işletme gerekleri
   - Soyut neden yetmez; somut gerekçe

4) Sonuçlar (Karar işçi lehine olursa):
   a) İşe iade kararı: İşçi 10 iş günü içinde başvuruda bulunmalı
   b) İşverenin kabul etmemesi: 4-8 aylık brüt ücret iş güvencesi tazminatı
   c) Boşta geçen süre ücreti: en fazla 4 aylık brüt ücret
   d) İşe iadeyi kabul eden işveren: işçi çalışmak zorunda değil, tazminat alabilir

5) Emsal: Yargıtay işe iade kararlarında geçerli nedeni dar yorumlar; belirsiz performans değerlendirmeleri tek başına yetmez
```

### API CEVABI

İş güvencesi rejimi kapsamında işe iade davası, iş sözleşmesinin işveren tarafından geçerli/haklı bir neden olmadan feshedildiği iddiasına dayanır. Kritik eksen: 4857 sayılı İş Kanunu’nun iş güvencesi hükümleri, feshe ilişkin şekil- ispat kuralları ve işe iade kararı verildiğinde doğan başvuru, işe başlatma, tazminat ve “boşta geçen süre” sonuçlarıdır.

## Uygulanabilir Normlar ve Dava Şartları
İşe iade davasının açılabilmesi için çekirdek koşullar şunlardır:
- İş güvencesi kapsamı: İşyerinde belirli bir çalışan sayısının üzerinde istihdam, işçinin en az belirli kıdeme sahip olması ve belirsiz süreli sözleşme ile çalışma şartları aranır [İK m.18]. (Sayı ve süre limitleri güncel mevzuattan teyit edilmelidir.)
- Fesih olgusu: Dava için ön koşul, iş sözleşmesinin işveren tarafından feshedilmiş olmasıdır; salt “görevden uzaklaştırma/izin” fesih değildir. Nitekim Yargıtay 9. Hukuk Dairesi, fesih bulunmayan durumda işe iade davasının reddedileceğini açıkça vurgulamıştır (9. Hukuk Dairesi, 2013).
- Fesihte şekil ve gerekçe: Geçerli nedenle fesihte yazılı bildirim, somut ve açık fesih sebebi ve (davranış/performans gerekçelerinde) savunma alma yükümlülüğü aranır [İK m.19].
- Süre ve usul: Feshe karşı başvuru için kısa bir hak düşürücü süre ve zorunlu arabuluculuk dava şartı vardır; anlaşma olmazsa dava açılır [İK m.20, 7036 sayılı Kanun]. (Süreler güncel mevzuattan teyit edilmelidir.)

Kontrol listesi:
- Somut “fesih bildirimi” var mı? (yazı, e‑posta, çıkış kodu, SGK bildirimi)
- İş güvencesi kapsam kriterleri sağlanıyor mu? (çalışan sayısı, kıdem, sözleşme türü, işveren vekilliği istisnası)
- Fesih gerekçesi ve usulü mevzuata uygun mu? (yazılılık, somut neden, savunma)
- Hak düşürücü sürelere ve arabuluculuk aşamasına riayet edildi mi?

## Emsal Eğilimleri ve Şartların İspatı
- Fesih ön koşulu: Yargıtay 9. Hukuk Dairesi, sadece soruşturma/izin uygulamasının fesih sayılamayacağını; somut fesih ispatlanmadan işe iade talebinin dinlenmeyeceğini belirtir (9. Hukuk Dairesi, 2013). Bu, davayı açmadan önce “fesih” delillerini netleştirmeyi zorunlu kılar.
- Başvuru ve samimiyet: Kesinleşen işe iade kararından sonra işçi 10 iş günü içinde işverene işe başlamak için başvurmalı; işveren de 1 ay içinde işe başlatmalıdır. İşçi başvuruyu vekil/sendika aracılığıyla da yapabilir. Ancak işçi başvurup işveren davet ettiğinde işe başlamazsa, başvurunun “samimi olmadığı” kabul edilerek ilk fesih geçerli sayılır (9. Hukuk Dairesi, 2014). Bu, pratikte tazminat ve alacak dengesini kökten etkiler.
- Davetin içeriği ve eşdeğer iş: İşverenin daveti ciddi ve samimi olmalı; hangi işte, nerede, hangi şartlarla ve hangi tarihte işe başlanacağı açıkça yazılmalıdır. Kural olarak işçi, fesih tarihindeki iş ve koşullarda veya objektif olarak denk bir pozisyonda başlatılmalıdır; aksi halde işçinin “eşdeğer olmayan” görevi reddi haklı sayılabilir (22. Hukuk Dairesi, 2014).
- Paralel davalar ve bekletici mesele: İşe iade davası derdestken kıdem/ihbar tazminatı davası açılmışsa, işe iadenin...[KISALTILDI]

### EMSAL KULLANIMI

- **Kaç emsal çekildi:** 5 bulundu, 5 seçilip yüklendi
- **Semantik chunk sayısı:** 0
- **Kaç emsal kullanıldı:** 5 / 5

**Çekilen emsal listesi:**

- [1] 7. Hukuk Dairesi | 2013-11-13 | 2083ch | ID:84216200
- [2] 15. Hukuk Dairesi | 2018-12-05 | 4854ch | ID:464091800
- [3] 22. Hukuk Dairesi | 2014-09-16 | 6229ch | ID:108674600
- [4] 9. Hukuk Dairesi | 2014-05-20 | 5479ch | ID:100398600
- [5] 9. Hukuk Dairesi | 2013-01-20 | 5064ch | ID:244886600

**Kullanılan emsaller ve semantik eşleşme skoru:**

  * `2013/12849 E.  ,  2013/19293 K.` — 7. Hukuk Dairesi (2013-11-13) — içerik örtüşme: **%23.9** — birim referans sayısı: 2
  * `2017/357 E.  ,  2018/4899 K.` — 15. Hukuk Dairesi (2018-12-05) — içerik örtüşme: **%11.0** — birim referans sayısı: 2
  * `2013/16121 E.  ,  2014/24211 K.` — 22. Hukuk Dairesi (2014-09-16) — içerik örtüşme: **%22.0** — birim referans sayısı: 2
  * `2012/12227 E.  ,  2014/16370 K.` — 9. Hukuk Dairesi (2014-05-20) — içerik örtüşme: **%29.5** — birim referans sayısı: 2
  * `2012/26154 E.  ,  2013/2006 K.` — 9. Hukuk Dairesi (2013-01-20) — içerik örtüşme: **%17.0** — birim referans sayısı: 2

**Kullanılmayan emsaller:**

  * (Tüm emsaller kullanıldı)

**Semantik chunk skorları (ilk 5):**


### DOĞRULUK ANALİZİ

- **Kullanılan kaynaklara göre doğruluk oranı:** %50.7
- **Kanun maddesi kapsama oranı:** %0.0
- **Beklenen maddeler:** ['md.18']
- **Cevapta bulunan:** []
- **Eksik maddeler:** ['md.18']

- **Cevaptaki eksikler:**
  - (Belirgin eksik tespit edilmedi)
- **Cevaptaki hatalar:**
  - (Açık hata tespit edilmedi)

### KAYNAK KALİTESİ

- **Hata/tutarsızlık var mı:** HAYIR
  - Emsal kararlar alan ve içerik açısından uygun görünüyor

---

## ÖZET TABLO

| Soru | Alan | Emsal Çekilen | Emsal Kullanılan | Doğruluk % | Madde % | Sem Chunk | Kritik Hata |
|------|------|:---:|:---:|:---:|:---:|:---:|-----|
| S1 | İş Hukuku | 5 | 5 | %54.7 | %0.0 | 12 | - |
| S2 | Kat Mülkiyeti Hukuku | 5 | 0 | %0.0 | %0.0 | 12 | Main GPT-5 hatası: Error code: 429 - {'e |
| S3 | Haksız Fiil / Trafik Hukuku | 5 | 5 | %50.8 | %0.0 | 0 | - |
| S4 | Miras Hukuku | 5 | 0 | %0.0 | %0.0 | 12 | Main GPT-5 hatası: Error code: 429 - {'e |
| S5 | İş Hukuku — İşe İade | 5 | 5 | %50.7 | %0.0 | 0 | - |

---
*Rapor otomatik oluşturuldu — 2026-03-18 23:37*
# Ölçüm ve araştırma notları

## Veri ve birim

8 sentetik Türkçe belge, 24 bölüm. Varsayılan 110 kelime/20 örtüşme ile her bölüm tek
parçaya sığıyor; bu nedenle mevcut sonuçlar büyük belge chunking deneyi sayılmaz.
32 soru: dev 12 cevaplanabilir + 4 cevapsız, test 12 + 4. Corpus ile sorular bu pilot
için birlikte yazıldı; bağımsız uzman etiketlemesi veya gerçek kullanıcı örneklemesi yok.
Split ve relevance/evidence etiketleri ilk ölçümden önce sabitlendi. Retrieval parametreleri
test sonuçlarına bakılarak ayarlanmadı. Üç ayrı sınır korunur:

- `section_id`: dosya + kalıcı bölüm kimliği; relevance etiketi bu seviyededir.
- `chunk_id`: bölüm + kelime konumu + içerik hash'i; aynı başlangıçlı parçalar kaybolmaz.
- `corpus_sha256`: dosya içerikleri + chunk ayarları; belge/ayar değişimi ayrı sürümdür.

Soru kaydı örneği:

```json
{"id":"q01","split":"dev","category":"numeric","question":"GPU rezervasyonu kaç saat?","relevant":["01_erisim.md#rezervasyon"],"evidence":{"01_erisim.md#rezervasyon":"en fazla 2 saatlik"}}
```

Cevapsız soru `relevant: []` ve `evidence: {}` taşır. Eksik bölüm kimliği veya hiçbir
chunk'ta bulunmayan evidence alıntısı, yanlış metrik üretmek yerine hata verir.

## Metrikler

İlk `k` **chunk** retrieval sonucu değerlendirilir; aynı bölümün ikinci chunk'ı
rank pozisyonunu tüketir ama ikinci relevance kredisi alamaz.

| Alan | Hesap / anlam |
|---|---|
| `recall@k` | Bulunan ilgili benzersiz bölüm sayısı / tüm ilgili bölüm sayısı; answerable sorgular arasında macro ortalama. |
| `mrr@k` | İlk ilgili chunk'ın sırasının tersi; ilk k'da yoksa 0. |
| `ndcg@k` | Binary relevance, log2(rank+1) indirimi, ideal sıralamaya bölme. |
| `all_evidence_sections@k` | Sorunun bütün etiketli bölümleri bulundu mu? Özellikle çok konulu sorular için. |
| `evidence_recall@k` | Beklenen kısa kanıt alıntısı doğru bölümün getirilen chunk'ında gerçekten var mı? |
| `negative_candidate_rate` | Cevapsız soruların kaçında en az bir aday geldi? **Cevap uydurma oranı değil.** |
| `latency_p50/p95_ms` | Bir ısınma aramasından sonra tek geçiş, query planning + retrieval. HTTP/UI ve final generation hariç. |
| `llm_calls` | HyDE/decomposition çağrıları; baseline'da 0. Başarısız provider isteği ölçümü açık hata ile durdurur. |

Skorlar olasılık veya doğruluk güveni değildir. Dense ve karakter yöntemleri anlamsız
sorulara da aday getirebilir; otomatik cevaplanabilirlik eşiği kalibre edilmedi.
Retrieval değerlendirmesi final cevabı üretmez, dolayısıyla faithfulness ölçmez.
LLM hatasında tamamlanmış gibi kısmi skor kaydetmez; hata ve koşulları ayrıca deney
günlüğüne yazıp sağlıklı koşuda rapor üretin.

## Saklanan sonuçlar

| Split / yöntem | Recall@5 | MRR@5 | nDCG@5 | Kanıt alıntısı recall | Cevapsız aday |
|---|---:|---:|---:|---:|---:|
| Dev / BM25 | 1.0000 | 0.8056 | 0.8610 | 1.0000 | 2/4 |
| Dev / kelime+karakter | 1.0000 | 1.0000 | 0.9875 | 1.0000 | 4/4 |
| Test / BM25 | 0.8333 | 0.8333 | 0.8333 | 0.8333 | 1/4 |
| Test / kelime+karakter | 0.9167 | 0.9167 | 0.9100 | 0.9167 | 4/4 |

Kaynak: `reports/baseline-dev.json`, `reports/baseline-test.json`. Sorgu bazında sıralama,
metrikler ve corpus/code/query hash'leri bu dosyalarda mevcut. İşlemci zamanı milisaniyenin
altında olan bu 24 parçalık in-memory deneyin gecikmesi, LLM veya Spark benchmark'ı değildir.
Bu küçük örnekten istatistiksel anlamlılık iddiası çıkarılmadı.

Üç öğretici başarısızlık:

1. **t06 – “Yerel LLM servisine bağlanmak için ne ayarlanır?”** Her iki yöntem de doğru
   `05_inference.md#baglanti` bölümünü ilk beşe getiremedi. İlk sonuç hata rehberi oldu.
   Soru-belge ifade farkı dense embedding veya query expansion için somut araştırma vakasıdır.
2. **t12 – “Öğrencilerin numaralarını ve e-postalarını anonimleştirmeli miyiz?”** BM25
   aday bulamadı; karakter üçlüleri doğru bölümü getirdi. Ekli sözcüklerde yüzey biçimi farkı
   için işe yaradı; genel Türkçe başarısı sonucu çıkarılamaz.
3. **t14 – “NVIDIA Spark cihazında saniyede kaç token üretilir?”** Corpus'ta böyle bir
   ölçüm yok. Karakter yöntemi yine aday üretti. Kaynak dönmesi cevap kanıtı değildir;
   LLM varsa bu soruda çekimserlik ayrıca değerlendirilmelidir.

## Gerçek araştırmaya geçiş

1. Erişim izni olan 10–20 belge seçin. Bir bölüm sınırını aşmayan 60–100 gerçek soru
   yazın; en az %20 cevapsız, bir kısmı yakın konulu olsun. Farklı kişi relevance ve
   destekleyici kanıtı işaretlesin; çelişkiler uzlaştırılsın. Bu sayılar pilot önerisidir.
2. Soru aileleri/paraphrase'leri aynı split'te tutun. Test setini parametre seçiminden
   uzak tutun. Chunking deneyi için gerçekten uzun belge ve cevap sınırı örnekleri ekleyin.
3. Aynı corpus ve candidate budget ile BM25 → dense → hybrid → hybrid+reranker ölçün.
   HyDE ve decomposition'ı ayrı açın. Sonuç artışını latency ve çağrı sayısıyla birlikte okuyun.
4. Final LLM cevaplarını sabit retrieval bağlamında kıyaslayın. İnsanlar her olgusal iddiayı
   kaynak desteği açısından, her cevapsız soruyu çekimserlik açısından işaretlesin.
   Model-as-judge yardımcı olabilir; tek doğruluk kaynağı olmasın.
5. Hata günlüğünde sorgu, beklenen bölüm, gelen bölüm, hata aşaması ve tek düzeltme
   hipotezi bulunsun. Yanlış retrieval, eksik context ve yanlış generation ayrı sayılmalı.

Önerilen ilk saha kabul ölçütü: en az 50 bağımsız cevaplanabilir soru için Recall@5 ≥ 0.85,
cevapsız sorularda insan onaylı çekimserlik ≥ %90; p95 hedefi gerçek model/donanım seçildikten
sonra belirlenir. Bunlar **tasarım hedefidir**, mevcut pilotun başardığı iddiası değildir.

İlk öğrenci araştırma sorusu: “Karakter aramasının kazandırdığı Türkçe ek toleransını,
cevapsız sorgulara fazla aday getirmeden dense/hybrid sistemle koruyabilir miyiz?”

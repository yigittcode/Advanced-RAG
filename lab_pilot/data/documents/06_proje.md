# Öğrenci araştırma teslim rehberi

SENTETİK EĞİTİM BELGESİ. Gerçek ders veya değerlendirme kuralı değildir.

## surum | Deney sürümü
Her deneyde kod commit kimliği, corpus hash değeri, sorgu seti sürümü, model sürümü ve parametreler kaydedilir. Modelin yalnızca görünen adı yeterli değildir; ağırlık revizyonu veya dosya hash değeri de tutulur. Aynı sorgu farklı corpus sürümünde farklı sonuç verebilir. Deneyin tarihi ve Python sürümü rapora eklenir.

## karsilastirma | Kontrollü karşılaştırma
Önce yalnızca BM25 ölçülür, ardından dense retrieval ve hybrid retrieval karşılaştırılır. Reranker, HyDE ve soru ayrıştırma ayrı deneylerde tek tek açılır. Her adımda yalnızca bir değişken değiştirilir. Kalite artışı gecikme ve model çağrısı sayısıyla birlikte değerlendirilir. Ek bileşenin faydalı olduğu ölçmeden varsayılmaz.

## teslim | Proje teslimi
Her ekip çalıştırma komutlarını, kullanılan veri setini, ham ölçüm raporunu ve en az üç başarısız sorguyu teslim eder. Başarısız örnekler için beklenen kaynak ile getirilen kaynak karşılaştırılır. Yalnızca başarılı ekran görüntüleri yeterli değildir. Yeniden çalıştırma sırasında dış servis gerekiyorsa servis adresi ve kurulum adımları belgelenir.

# Retrieval değerlendirme protokolü

SENTETİK EĞİTİM BELGESİ. Başarı eşikleri araştırma için öneridir, ölçülmüş sonuç değildir.

## metrik | Recall MRR ve nDCG
Recall@5, soruyla ilgili etiketli bölümlerin ilk beş sonuçta ne kadarının bulunduğunu ölçer. MRR ilk ilgili sonucun sırasına odaklanır. nDCG ilgili sonuçların üst sıralarda olmasını ödüllendirir. Bu metrikler retrieval kalitesini ölçer; LLM cevabının doğruluğunu veya atıf sadakatini tek başına ölçmez. Gecikme p50 ve p95 olarak ayrıca raporlanır.

## bolme | Geliştirme ve test soruları
Sorgular geliştirme ve test olarak ayrılır. Parametre seçimi yalnızca geliştirme soruları üzerinde yapılır. Test soruları seçim bittikten sonra bir kez değerlendirilir. Test sonuçlarına göre ayar değiştirilirse o test artık bağımsız sayılmaz ve yeni bir test seti gerekir. Sentetik örneklerle alınan sonuç gerçek öğrenci sorularına genellenemez.

## olumsuz | Cevapsız sorular
Belgelerde karşılığı olmayan sorular ayrı bir grup olarak tutulur. Yakın konulu ama cevapsız sorular özellikle eklenir. Arama sonucu bulunması, sorunun cevaplanabildiğini göstermez. Cevapsız sorular için aday getirme oranı ayrıca raporlanır. Gerçek cevap uydurma oranını ölçmek için üretilen cevapların insanlar tarafından incelenmesi gerekir.

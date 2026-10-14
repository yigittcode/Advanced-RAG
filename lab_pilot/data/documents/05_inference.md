# Yerel LLM bağlantı deneyi

SENTETİK EĞİTİM BELGESİ. Donanımda denenmiş bir kurulum veya performans iddiası değildir.

## baglanti | Model sunucusuna bağlantı
Pilot uygulama OpenAI uyumlu Chat Completions HTTP arayüzüne bağlanır. Model sunucusu adresi ve model adı açıkça yapılandırılır. Önce model listesinden sunulan ad doğrulanır, sonra küçük bir sohbet isteği gönderilir. Varsayılan çalışma modu model API'si çağırmaz. Sunucu uzaktaysa SSH port yönlendirme kullanılabilir.

## bellek | Model ve bellek deneyi
İlk yerel model denemesi tek kullanıcı ve kısa bağlamla başlar. Bellek kullanımı yalnızca model ağırlıklarından oluşmaz; KV cache ve çalışma alanı da bellek tüketir. Bağlam uzunluğu ve eşzamanlı istek sayısı ayrı ayrı artırılır. Modelin cihaza sığması, yeterli gecikmeyle çalıştığını kanıtlamaz. Performans gerçek cihazda ölçülür.

## hata | Model isteği başarısız olursa
Model sunucusuna erişilemiyorsa uygulama bağlantı hatasını açıkça gösterir. HTTP 401 yanıtında erişim anahtarı kontrol edilir; HTTP 404 yanıtında adres ve model adı gözden geçirilir. Zaman aşımı ölçüm raporuna başarısız deney olarak işlenir. Başarısız yerel model isteği otomatik olarak ücretli bulut servisine yönlendirilmez.

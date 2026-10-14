# Teslim doğrulaması · 14 Ekim 2026

| Kontrol | Sonuç |
|---|---|
| `python -S -m unittest discover -s tests -v` | 14/14 geçti; `-S` ile üçüncü taraf site-packages yüklenmeden |
| CLI `ask`, varsayılan corpus ve BM25 | Kaynak, atıf kimliği, satırlar ve JSON çıktı doğrulandı |
| Dev + test retrieval değerlendirmesi | `reports/` içinde ham sonuçlar var |
| HTTP `/`, `/api/search`, `/api/evaluate` | Yerel HTTP sunucusunda otomatik test edildi |
| `node --check lab_rag/web/app.js` | Sözdizimi kontrolü geçti |
| Production diff | Yalnızca yeni `lab_pilot/` dosyaları; mevcut dosyalarda değişiklik yok |
| Gerçek tarayıcıyla görsel / etkileşim testi | Tamamlanamadı; browser binary yoktu, Chromium indirmesi geçersiz/eksik arşiv döndürdü |
| Gerçek embedding/reranker/LLM ağırlıkları | Çalıştırılmadı |
| NVIDIA Spark, ARM/CUDA, token/s, çok kullanıcı yükü | Donanım erişimi yok; çalıştırılmadı |

Testler: corpus etiketlerinin geçerliliği; chunk kimliğinin kararlılığı; içerik değişiminde
hash değişmesi; aynı başlangıçlı farklı parçaların ayrılması; sıfır/eksik arama; RRF'nin
skor ölçeğinden bağımsızlığı; tekrarlı bölümün metrikte ek kredi almaması; baseline'da
network çağrısı olmaması; pozitif/negatif değerlendirme sayımı; Chat Completions HTTP
istek/yanıt sözleşmesi; yanlış atıf; HTTP hata, timeout ve bozuk/kesilmiş yanıt;
HyDE'nin kanıta sızmaması; decomposition sınırı; API giriş ve origin doğrulaması.

HTTP testindeki “model” kontrollü fixture yanıtı üretir. Bu sonuçlar gerçek model
inference başarısı veya cevap kalitesi olarak sunulmamalıdır. Browser'a ilişkin kontroller
API/JS düzeyindedir; piksel görünümü, mobil görünüm ve gerçek indirme etkileşimi ayrıca
yerel tarayıcıda kontrol edilmelidir.

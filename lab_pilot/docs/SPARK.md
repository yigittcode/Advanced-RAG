# NVIDIA Spark'a geçiş

Bu uygulama gerçek laboratuvar erişimi olmadan çalıştırılabilir. Mevcut görev/erişim
durumu hakkında bir varsayım yapmaz. Burada yalnızca sonradan donanım üzerinde
doğrulanabilecek teknik yol tarif edilir.

## Ayrı süreç sınırı

Pilot laptop/CPU üzerinde kalabilir. Yerel LLM servisi Spark üzerinde ayrı süreç veya
container'da çalışır. Pilot yalnızca Chat Completions HTTP sözleşmesini bilir.
Bu sayede retrieval kodunu CUDA/ARM paketleriyle aynı ortamda başlatmak gerekmez.
GPU üzerinde embedding istenirse o yol ayrıca doğrulanır.

NVIDIA'nın [DGX Spark vLLM rehberi](https://build.nvidia.com/spark/vllm/instructions)
OpenAI uyumlu API, model listesi ve sohbet isteğiyle doğrulama akışı sunuyor.
[vLLM API dokümanı](https://docs.vllm.ai/en/stable/serving/online_serving/openai_compatible_server/)
Chat Completions desteğini açıklıyor. Bu nedenle bu pilot için **ilk entegrasyon adayı
vLLM'nin OpenAI uyumlu endpoint'i**. Bu bir uygulama tasarım tercihidir; herhangi bir
model/container kombinasyonunun laboratuvar cihazında çalıştığı anlamına gelmez.

## Donanım erişiminde yapılacaklar

| Aşama | Kaydedilecek kanıt | Geçiş koşulu |
|---|---|---|
| Envanter | Gerçek cihaz modeli, `uname -m`, OS, `nvidia-smi`, RAM/disk, sürücü/CUDA | Cihazın ve yazılım mimarisinin seçilen recipe ile eşleşmesi |
| Runtime | Resmî cihaz recipe'si, container image digest, model revision ve quantization | Container başlıyor, model yükleniyor; gerekli lisans/erişim koşulları karşılanıyor |
| API | `/v1/models` çıktısı ve küçük Chat Completions cevabı | Model adı doğru, chat template çalışıyor, cevap tamamlanıyor |
| RAG | Aynı corpus ve soruyla `ask --llm` çıktısı | Gerçek kaynaklara bağlı cevap; hatalı atıflar ve cevapsız sorular incelenmiş |
| Kapasite | Cold start, RAM/GPU bellek, bağlam uzunluğu, eşzamanlılık, hata/timeout | Belirlenen kullanım yükünde istikrarlı davranış |
| Kalite | Sabit sorularda insan destek kontrolü ve çekimserlik | Ekipçe kararlaştırılan kalite hedefi |

Container/model adları zamanla değiştiğinden bu depoya denenmemiş bir Docker “tek satır
kurulumu” sabitlenmedi. Cihaza erişildiği gün resmî recipe seçilip **tag yerine digest**,
model ağırlık revizyonu ve kurulum notu deney kaydına eklenmeli.
[NVIDIA porting kılavuzu](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/porting/dependencies.html)
paket/sürüm desteğini ayrıca takip ediyor; masaüstü Python wheel'lerinin hedef ARM/CUDA
ortamında çalışacağı varsayılmamalı.

## Endpoint hazır olduğunda

Pilot makinesinden, sunucunun gerçek adresine göre:

```bash
curl http://127.0.0.1:8000/v1/models
```

Servis API anahtarı istiyorsa bu isteğe uygun Authorization başlığı ekleyin. Production
API'si aynı makinede 8000 kullanıyorsa model servisine farklı port verin ve aşağıda onu yazın.

```bash
export RAG_LLM_BASE_URL=http://127.0.0.1:8000/v1
export RAG_LLM_MODEL=LISTED_MODEL_ID
python -m lab_rag ask "GPU rezervasyonu kaç saat?" --llm --output runs/spark-smoke.json
python -m lab_rag serve --llm
```

Uzak servisi yerel ağda herkese açmak yerine yetkili SSH/NVIDIA Sync port yönlendirmesiyle
erişmek bu küçük pilot için yeterlidir. UI anahtar istemez; bağlantı ayarları server
ortamındadır. Gerçek üniversite belgeleri kullanıldığında seçilen endpoint'in nerede
çalıştığı ve veri kullanım izni ayrıca belirlenmelidir.

## Ölçülecek performans

Bir kullanıcı + kısa context ile başlayın. Sonra context ve eşzamanlılığı tek tek artırın.
Uygulama generation süresini ölçer; streaming, TTFT veya token/s üretmez. Bunlar için
inference sunucusunun benchmark/telemetri aracı gerekir. Warm/cold koşulları, output token
sayısını, batch, quantization ve max context'i beraber kaydedin. “Belleğe sığıyor” sonucu
“etkileşimli kullanım için yeterince hızlı” sonucu değildir.

Bu teslimde doğrulanan: standard library baseline, yerel HTTP API sözleşmesi, hata yolları.
Doğrulanmayan: gerçek E5/CrossEncoder ağırlıkları, gerçek LLM cevap kalitesi, ARM/CUDA
paket kombinasyonu, Spark model belleği, token/s, TTFT ve çok kullanıcılı gecikme.

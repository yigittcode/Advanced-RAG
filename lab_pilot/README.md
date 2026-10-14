# Advanced-RAG · Laboratuvar Pilotu

**Belgeden getirilen kanıtı görün, retrieval kalitesini ölçün, sonra yerel LLM bağlayın.**

Bu klasör mevcut Advanced-RAG uygulamasından bağımsızdır. Production Python modüllerini,
`.env` dosyasını, veritabanlarını veya Compose servisini kullanmaz. Temel demo Python
3.11+ standard library ile çalışır; API anahtarı, GPU, Docker veya paket kurulumu gerekmez.

- 8 sentetik Türkçe belge, 24 bölüm/parça ve 32 etiketli soru.
- BM25; BM25 + karakter üçlüleri ile RRF (`lexical`). İkincisi semantik embedding değildir.
- İsteğe bağlı gerçek dense embedding, BM25+dense hybrid, cross-encoder reranking.
- Kaynak dosyası, bölüm, satırlar, parça kimliği ve retrieval skorları görünen yerel arayüz.
- Recall@k, MRR@k, nDCG@k, tam kanıt kapsamı, cevapsız sorgu analizi ve JSON raporları.
- OpenAI uyumlu Chat Completions endpoint adaptörü; isteğe bağlı HyDE ve decomposition.

**Varsayılan mod kaynak alıntılarını gösterir, LLM cevabı üretmez.** Gerçek üretken RAG
için aşağıdaki `--llm` bağlantısı gerekir. Bu teslimde gerçek LLM ağırlıkları, embedding
ağırlıkları veya NVIDIA Spark üzerinde inference çalıştırılmadı. Adaptörün HTTP sözleşmesi
yerel test sunucusuyla doğrulandı; bu, model kalitesi veya donanım uyumluluğu kanıtı değildir.

## Hemen çalıştır

Repo kökünden:

```bash
cd lab_pilot
python -m lab_rag serve
```

Tarayıcıda <http://127.0.0.1:8765> açılır. Python komutunuz `python3` ise komutlarda onu kullanın.
Windows PowerShell için de aynı komutlar geçerlidir. Ctrl+C ile durdurun.

```bash
python -m lab_rag ask "GPU rezervasyonu kaç saat sürebilir?" --method bm25 -k 3
python -m lab_rag evaluate --split dev --output runs/dev.json
python -m lab_rag evaluate --split test --output runs/test.json
python -m unittest discover -s tests -v
```

İsterseniz önce `python -m venv .venv` ile ayrı bir ortam oluşturun. Mevcut uygulamanın
`requirements.txt` dosyasını bu pilot için kurmayın. Örnek belgelerde yazan kurallar
eğitim amaçlı kurgudur; gerçek üniversite bilgisi değildir.

## İlk ölçüm: saklanan gerçek raporlar

İlk test geçişi, 12 cevaplanabilir + 4 cevapsız soru; `k=5`, aday havuzu 20,
110 kelime/parça, 20 kelime örtüşme. Parametreler test sonuçlarına göre değiştirilmedi.

| Yöntem | Recall@5 | MRR@5 | nDCG@5 | Cevapsız soruda aday getirme |
|---|---:|---:|---:|---:|
| BM25 | 0.8333 | 0.8333 | 0.8333 | 1/4 |
| BM25 + karakter RRF | 0.9167 | 0.9167 | 0.9100 | 4/4 |

Ham veriler: [geliştirme raporu](reports/baseline-dev.json), [test raporu](reports/baseline-test.json).
Yorum ve başarısız örnekler: [ölçüm notları](docs/EVALUATION.md).

Bu küçük sentetik set bağımsız production benchmark'ı değildir. Özellikle karakter araması
bir ekli Türkçe sorguyu kurtarırken cevapsız sorulara da aday getiriyor. Bu skorlar cevap
doğruluğu, hallucination oranı veya gerçek üniversite kullanım başarısı değildir.

## Gerçek LLM ile cevap üretimi

Uygulamanın erişebildiği bir OpenAI uyumlu sunucu hazır olduğunda:

```bash
export RAG_LLM_BASE_URL=http://127.0.0.1:8000/v1
export RAG_LLM_MODEL=SUNUCUNUN_DONDURDUGU_MODEL_ADI
# Yalnızca sunucu istiyorsa: export RAG_LLM_API_KEY=...
python -m lab_rag serve --llm
```

PowerShell:

```powershell
$env:RAG_LLM_BASE_URL = "http://127.0.0.1:8000/v1"
$env:RAG_LLM_MODEL = "SUNUCUNUN_DONDURDUGU_MODEL_ADI"
python -m lab_rag serve --llm
```

Adres, `/chat/completions` eklenmeden önceki API tabanıdır; çoğu sunucuda `/v1` ile biter.
Model adı örnek bir yer tutucudur; `/v1/models` yanıtındaki gerçek adı kullanın.
Anahtar tarayıcıya gönderilmez. `.env` otomatik okunmaz. `--llm` verilmeden hiçbir model
API'si çağrılmaz. Bağlantı hatası bulut servisine sessizce düşmez. Varsayılan timeout
30 saniyedir; `RAG_LLM_TIMEOUT` ile en fazla 120 saniye seçilebilir.

Üretilen cevapta [S1] gibi atıfların getirilen kaynaklara ait olup olmadığı kontrol edilir.
Yanlış/eksik kaynak kimliği olan cevap gösterilmez. **Atıf kimliğinin doğruluğu, iddianın
kaynak tarafından desteklendiğini kanıtlamaz.** Bu kontrol insan değerlendirmesinin yerini almaz.
Modelin bağlam limiti için 10.000 karakterlik kanıt bütçesi kullanılıyor; bu bir token
garantisi değildir. Küçük context window veya reasoning modellerinde bütçe/chat template
uyarlaması gerekebilir.

## Gerçek embedding ve reranker deneyi

Temel ortamdan ayrı bir sanal ortamda:

```bash
python -m pip install -r requirements-models.txt
python -m lab_rag evaluate --embedding-model /ABSOLUTE/PATH/TO/E5_MODEL --methods bm25 dense hybrid --split dev --output runs/dense-dev.json
python -m lab_rag evaluate --embedding-model /ABSOLUTE/PATH/TO/E5_MODEL --reranker-model /ABSOLUTE/PATH/TO/RERANKER --methods hybrid --split dev --output runs/rerank-dev.json
```

Yer tutucuları gerçekten indirilmiş model dizinleriyle değiştirin. Pilot hub'dan model indirmez;
ilk dense/rerank sorgusunda yerel ağırlıkları yükler (`local_files_only=True`, `trust_remote_code=False`).
`--device cpu` varsayılandır. GPU denemesi için hedef ortam doğrulandıktan sonra `--device cuda` kullanın.
E5 ailesi için `query: ` ve `passage: ` önekleri korunur, vektörler normalize edilir.
Başka modelin farklı prompt sözleşmesi varsa adaptörü uyarlayın; `--no-e5-prefix` yalnızca
bu iki öneki kapatır. Başlangıç adayı küçük E5 olabilir; mevcut E5-large da yerel dizinden
aynı adaptörle denenebilir. Türkçe reranker seçimini ölçüm belirlemelidir.

İsteğe bağlı paket aralığı bir ARM/CUDA lockfile değildir. Hedef makinede çalışan paketleri,
model revision/hash bilgisini ve `pip freeze` çıktısını deneyle birlikte kaydedin.

## HyDE ve soru ayrıştırma

```bash
python -m lab_rag evaluate --llm --hyde --methods bm25 --split dev --output runs/hyde-dev.json
python -m lab_rag evaluate --llm --decompose --methods bm25 --split dev --output runs/decomposition-dev.json
python -m lab_rag ask "GPU rezervasyonu kaç saat ve günlükler kaç gün saklanır?" --llm --decompose
```

İlk iki komut yalnızca query transformation için model çağırır; final cevap üretmez.
Sorgu başına çağrı sayısı ve dönüşmüş sorgular raporda görünür. En fazla üç alt soru
kabul edilir; özgün soru her zaman korunur. HyDE metni yalnızca arama sorgusudur,
cevaba verilen kanıt listesine eklenmez. HyDE'nin dense retrieval üzerindeki etkisini
araştırmak için aynı komuta `--embedding-model ... --methods hybrid` eklenebilir.

## Kendi belgelerin

```bash
python -m lab_rag serve --corpus /ABSOLUTE/PATH/TO/DOCUMENTS --queries /ABSOLUTE/PATH/TO/queries.jsonl
```

UTF-8 `.md` ve `.txt` desteklenir. Önerilen bölüm biçimi:

```markdown
# Belge adı
## sabit-bolum-id | İnsanların okuyacağı başlık
Kaynak metin...
```

Kimlik `dosya.md#sabit-bolum-id` olur. Bölüm başlıkları arasında parçalama yapılmaz;
uzun bölümler örtüşen kelime pencerelerine ayrılır. Üst başlığın altındaki giriş notları,
`##` bölümleri olan dosyalarda indekse alınmaz. Bölümsüz TXT bütünüyle parçalanır.
Dosya başına sınır 2 MB'dir. Yeni belgeler için yeni relevance/evidence etiketleri yazın;
örnek sorgu etiketlerini farklı corpus ile kullanmak hata verir. Sunucu belgeleri açılışta
indeksler; dosya değişince yeniden başlatın. Önceki indeks diskte tutulmaz.

## API ve kapsam

`GET /api/status`, `POST /api/search` (`question`, `method`, `k`) ve
`POST /api/evaluate` (`method`, `k`, `split`) arayüzle aynı yolları kullanır.
Sunucu 127.0.0.1'e bağlanır, eşzamanlı ikinci deneye 409 döner. Genel erişime açık bir
production sunucusu olarak tasarlanmadı; oturum, kullanıcı yönetimi veya yük dengeleme içermez.

İlk kapsam: retrieval deneyleri, izlenebilir kaynaklar, yerel LLM adaptörü.
Sonraki kapsam: gerçek izinli corpus, bağımsız soru etiketleme, tokenizer bütçesi,
cevap/atıf doğruluğu ölçümü. PDF/OCR, ses, kalıcı DB, training ve çok cihazlı dağıtım yok.

- [Mevcut kod incelemesi ve yeniden kullanım haritası](docs/CODE_REVIEW.md)
- [Ölçüm yöntemi ve araştırma planı](docs/EVALUATION.md)
- [Spark'a geçiş ve gerçek donanım doğrulaması](docs/SPARK.md)
- [45 dakikalık öğrenci gösterimi](docs/DEMO.md)
- [Test edilenler ve doğrulanmayanlar](docs/VALIDATION.md)

# Advanced-RAG kod incelemesi

İncelenen kaynak: [yigittcode/Advanced-RAG, 6861741](https://github.com/yigittcode/Advanced-RAG/tree/6861741e3b6193838c29b9b4da06ea65df903801), 14 Ekim 2026.
README yanında ingestion, embedding, search, query processing, context assembly,
generation, API startup, MongoDB ve ses modülleri incelendi. Production uygulaması
çalıştırılmadı; aşağıdaki somut davranışlar kaynak kodundan doğrulandı.
Kaliteye etkisi ayrıca ölçülmesi gereken noktalar hipotez olarak belirtilmiştir.

## Yeniden kullanım haritası

| Mevcut parça | Yararlı deneyim / bileşen | Pilot kararı |
|---|---|---|
| `document_processor.py`, `SemanticDocumentProcessor` | Madde/başlık sınırlarını koruma, source/article metadata | Başlıkları koruyan küçük Markdown/TXT chunker yazıldı. PDF parser doğrudan import edilmedi; pypdf, langchain, sentence-transformers ve config zinciri taşınmadı. |
| `embedding_engine.py`, `SemanticEmbeddingEngine` | Query/passage ayrımı, batch encoding, model injection | Yerel E5 adaptöründe açık query/passage prefix ve normalize edilmiş vektörler. Model boyutu/konumu parametre; `e5-large` zorunlu değil. |
| `search_engine.py`, `SearchEngine` | Dense + keyword aday üretme, reranking | BM25 baseline ve isteğe bağlı dense+BM25 RRF. Vektör DB gerektirmeyen küçük in-memory corpus. |
| `query_processor.py` | Soru ayrıştırma ve özgün soruyu koruma | En fazla üç alt sorulu, JSON doğrulamalı, opt-in decomposition; çağrı sayısı görünür. Kuruma özel terim sözlükleri taşınmadı. |
| `hyde_generator.py` | Soru ile belge dilini yakınlaştırma | Opt-in HyDE; varsayımsal metin yalnızca sorgu olur. Gerçek kaynak listesine girmez. |
| `context_assembler.py` | Source/article ile kanıtı biçimleme | Chunk ID + section ID + dosya/satır + [Sx] atıf eşlemesi. Karakter bütçesi açıkça belirtiliyor. |
| `response_generator.py` | Enjekte edilmiş istemci, bağlama dayalı cevap | Küçük Chat Completions HTTP adaptörü; endpoint/model açıkça ayarlanıyor. Model hatası ayrı; otomatik bulut fallback yok. |
| `rag_orchestrator.py` | Retrieve → assemble → generate ayrımı; alt soruların ayrı aranması | Bu aşamalar ayrı fonksiyonlar. Önce ölçülebilir baseline, sonra tek tek ablation. |
| `mongodb_manager.py` | Gerçek etkileşimlerden hata analizi yaklaşımı | Pilot ham JSON deney raporu üretir. Canlı sohbet verisi ve kullanıcı kayıtları kullanılmadı. |

Burada **algoritmik yaklaşım ve veri sözleşmeleri yeniden uygulandı; production sınıfları
doğrudan import edilmedi veya düzeltilmedi.** Bu ayrım kasıtlıdır: mevcut modüllerin çoğu
global config, üniversiteye özgü kurallar, servisler veya ağır paketlerle bağlıdır.
Başarılı pilot bileşenleri sonradan production'a ayrı bir değişiklik olarak taşınabilir.

## Laboratuvara taşımayı zorlaştıran bağımlılıklar

| Kod kanıtı | Doğrulanan davranış | Pilotta karşılığı |
|---|---|---|
| [`api_backend.py`, lifespan](https://github.com/yigittcode/Advanced-RAG/blob/6861741e3b6193838c29b9b4da06ea65df903801/api_backend.py#L166) | Startup SentenceTransformer, CrossEncoder, AsyncOpenAI, MongoDB, Weaviate ve SpeechProcessor açıyor. Text-only yolu bunları atlamıyor. | Temel modda ağır model veya servis yok; modeller ilk kullanımda yüklenir. |
| [`speech_integration.py`, constructor](https://github.com/yigittcode/Advanced-RAG/blob/6861741e3b6193838c29b9b4da06ea65df903801/speech_integration.py#L21) | Whisper small CPU'da yükleniyor; `pygame.mixer.init()` çalışıyor. | Ses kapsam dışı. Headless cihazda ses donanımı/FFmpeg/PyAudio yükü taşınmıyor. |
| [`config.py`](https://github.com/yigittcode/Advanced-RAG/blob/6861741e3b6193838c29b9b4da06ea65df903801/config.py) | `int(os.getenv("JWT_EXPIRE_MINUTES"))` import anında çalışıyor; değer yoksa import hatası. Model/adres ayarlarının bir bölümü sabit. | Production config/.env hiç okunmaz. Pilot ortam değişkenleri `RAG_LLM_*`. |
| [`mongodb_manager.py`](https://github.com/yigittcode/Advanced-RAG/blob/6861741e3b6193838c29b9b4da06ea65df903801/mongodb_manager.py#L26), [`docker-compose.yml`](https://github.com/yigittcode/Advanced-RAG/blob/6861741e3b6193838c29b9b4da06ea65df903801/docker-compose.yml) | Mongo constructor bağlantı ve ping yapıyor. Compose yalnızca Weaviate 1.25.4 açıyor; Mongo ayrı. | Dosyalar + bellekte indeks; haricî DB ihtiyacı yok. |
| [`query_processor.py`](https://github.com/yigittcode/Advanced-RAG/blob/6861741e3b6193838c29b9b4da06ea65df903801/query_processor.py#L114), `hyde_generator.py`, `response_generator.py` | Query analysis/paraphrase içinde `gpt-4o-mini` sabit; diğer model adları config'ten. | Tek açık Chat Completions sözleşmesi; endpoint/model parametre. Sadece cevap modelini değiştirmek bütün sistemi yerelleştirmeye yetmez. |
| `requirements.txt` | Çoğunlukla alt sınırlar, transitive lock yok; ML+ses+iki vector DB istemcisi birlikte. | Baseline üçüncü taraf paketsiz. Opsiyonel ML ortamı hedef cihazda ayrıca dondurulmalı. |

## Araştırmaya değer doğruluk noktaları

1. **Tekilleştirme:** `search_engine.py` satır 479/504/657 civarında `document[:100]`
   anahtar olarak kullanılıyor. İlk 100 karakteri aynı, devamı farklı parçalar birleştirilebilir.
   Pilot kimliği bölüm, konum ve içerik hash'inden üretir; bu senaryo test edildi.
2. **Mesafe sıfırsa fallback:** `_weaviate_semantic_search` içindeki
   `distance if distance else 0.5`, geçerli `0.0` mesafesini `0.5` yapar.
   Bu somut sınır durumudur; `is not None` kontrolü gerekir. Production dosyası değiştirilmedi.
3. **Skor ölçekleri:** `_intelligent_rerank`, cross-encoder ham skorunun %70'ini
   retrieval skorunun %30'uyla topluyor. Ayrıca bazı keyword sonuçlarına sabit skor
   veriliyor. Bunların kalibrasyonu gösterilmemiş. Kaliteye etkisi ölçülmeli;
   pilot fusion için RRF, reranking için ayrı sıralama kullanır.
4. **Türkçe reranker varsayımı:** config yorumunda Türkçe için uygunluk iddiası var;
   model kartı modeli İngilizce/MS MARCO olarak tanımlıyor. Bu, Türkçe işe yaramaz
   demek değildir; Türkçe qrels üzerinde çok dilli alternatifle kıyas gerektirir.
   [Resmî model kartı](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2).
   Eski `L-12` adresi inceleme sırasında `L12` adresine yönlendi; salt ad yazımı
   üzerinden kesin yükleme hatası iddia edilmedi.
5. **E5 prefix ve ek marker'lar:** E5 seçimi modelin string gösteriminden çıkarılıyor;
   bazı yollar prefix'in önüne `[EDUCATIONALsemantic]` gibi marker ekliyor.
   E5 model kartının query/passage başlangıç sözleşmesiyle sade baseline karşılaştırılmalı.
   Pilot E5 yolunda bu marker'lar yok.
6. **Alt soru izolasyonu:** `_process_individual_question`, üst sorudan gelen ilk HyDE
   varyantını her alt soruya ekliyor. İlgisiz konudan aday taşınması olası; etkisi henüz
   ölçülmedi. Pilot HyDE'yi her arama sorusu için ayrı üretip iz kaydına ekler.
7. **Kaynak listesi vs gerçekten kullanılan kanıt:** `_extract_source_metadata` ilk
   10 retrieval sonucundan dosya/bölüm topluyor. Bu liste, final context'te kullanılan
   parçaların veya üretilen iddiaların otomatik eşlemesi değil. Pilot sadece context'e
   konan parçaları `sources` alanında döndürür. Semantik atıf doğruluğu yine insan incelemesi ister.
8. **Cache/ölçüm:** Embedding cache anahtarı soru hash'ine dayanıyor; model/corpus sürümü
   içermiyor. Aynı süreçte model değişimi araştırılırsa yanıltıcı cache ihtimali var.
   Pilot dense belge cache'i yalnızca tek model nesnesine ait ve tam belge listesiyle
   geçersizleşir. Raporlar code/corpus/query SHA-256 içerir. Gerçek ağırlık revizyonu
   ayrıca deney manifestine yazılmalıdır.

Bu inceleme bir production güvenlik denetimi veya canlı servis performans testi değildir.
İlk pilot kararı: önce veri/etiket/ölçüm döngüsü kurmak; daha çok model çağrısını ancak
ölçülen fayda gösteriyorsa eklemek.

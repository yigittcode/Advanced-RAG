# 45 dakikalık ilk laboratuvar gösterimi

Amaç: öğrencinin soru → adaylar → kanıt → cevap zincirinde hatanın nerede oluştuğunu
gösterebilmesi. Model eğitimi veya donanım kurulumu bu oturumun ön koşulu değil.

| Süre | Uygulama | Beklenen tartışma |
|---|---|---|
| 0–5 dk | `python -m lab_rag serve`; sentetik belgeyi aç | Gerçek veri/politika ile örnek veriyi ayırma |
| 5–12 dk | “GPU rezervasyonu kaç saat?”; kaynak/satır/skor incele | Sıralama skoru neden doğruluk olasılığı değil? |
| 12–20 dk | “Öğrencilerin numaralarını ve e-postalarını anonimleştirmeli miyiz?”; iki yöntemi kıyasla | Türkçe ekler BM25 eşleşmesini nasıl etkiliyor? |
| 20–27 dk | “NVIDIA Spark cihazında saniyede kaç token üretilir?” | Aday var ama cevap yok: retrieval ile answerability ayrımı |
| 27–35 dk | Dev değerlendirmesi çalıştır, JSON indir | Recall/MRR/nDCG, negatifler ve çok konulu kapsam |
| 35–42 dk | `t06` hatasında beklenen/gelen kaynakları karşılaştır | Sonraki değişikliğin hipotezini veriyle kurma |
| 42–45 dk | Bir sonraki deney için tek değişken seç | Ölçüm yapılmadan HyDE/reranker faydasını varsaymama |

Yerel LLM daha sonra hazır olduğunda aynı gösterimi `--llm` ile tekrarlayın. Bir cevapta
her iddiayı kaynaktan işaretletin; [S1] yazmasının doğruluk garantisi olmadığını gösterin.
Bu ilk teslimde model olmadan görünen metinler alıntıdır; üretilmiş cevap gibi anlatılmamalı.

## İlk iki haftalık küçük pilot önerisi

1. İlk oturum: bu demo ve başarısızlıklar; iki öğrencinin ayrı relevance etiketlemesi.
2. İkinci oturum: izinli belgeler ve 60–100 soru; anlaşmazlıkların çözümü, dev/test ayrımı.
3. Üçüncü oturum: gerçek dense/hybrid/reranker ablation; sorgu başına kalite/latency karşılaştırması.
4. Dördüncü oturum: erişim varsa Spark inference bağlantısı; yoksa mevcut CPU retrieval
   araştırması sürer. Teslim: çalıştırma komutları, raw rapor, üç hata incelemesi ve tek sonraki hipotez.

Başarı ölçüsü çalışan sohbet ekranından ibaret değildir: başka bir öğrencinin aynı corpus
ve yapılandırmayla ölçümü yeniden üretebilmesi ve hangi soruların neden başarısız olduğunu
gösterebilmesidir.

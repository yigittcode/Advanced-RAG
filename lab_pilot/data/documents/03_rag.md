# RAG veri hazırlama deney yönergesi

SENTETİK EĞİTİM BELGESİ. Buradaki sayılar eğitim deneyinin tasarım tercihidir.

## parcalama | Belge parçalama deneyi
İlk parçalama deneyinde 100 ve 200 kelimelik pencereler karşılaştırılır. İki deneyde de 20 kelime örtüşme kullanılır. Başlık ve madde sınırları korunur; farklı başlıkların metinleri tek parçada birleştirilmez. Her parçaya dosya adı, bölüm kimliği ve içerik hash değeri eklenir. Büyük parçaların daha iyi sonuç verdiği önceden varsayılmaz.

## kaynak | Cevaplarda kaynak gösterme
LLM cevabındaki her olgusal iddia ilgili kaynak parçasına bağlanır. Kaynak metninde cevabı bulunmayan soru için bilgi bulunamadığı söylenir. Kaynak işaretinin mevcut olması iddianın doğru olduğunu tek başına kanıtlamaz. Bir araştırmacı kaynak ile iddiayı karşılaştırır. Varsayımsal HyDE metni asıl belge gibi kaynak gösterilemez.

## guncelleme | Belge güncellenince indeks
Bir belgenin içeriği değiştiğinde içerik hash değeri değişir ve indeks yeniden oluşturulur. Eski parçalar yeni sürümde arama sonucu olarak tutulmaz. Güncellenen bölümün relevance etiketleri ve beklenen kanıt alıntıları tekrar incelenir. Önceki rapor saklanır; yeni ölçüm ayrı corpus sürümü altında kaydedilir. Karşılaştırma aynı sorgu setiyle yapılır.

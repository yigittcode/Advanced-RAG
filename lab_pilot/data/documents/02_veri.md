# Örnek veri işleme rehberi

SENTETİK EĞİTİM BELGESİ. Kurumsal veri politikası değildir.

## kisisel | Kişisel veri ve anonimleştirme
İlk RAG pilotunda yalnızca sentetik veya paylaşım izni verilmiş belgeler kullanılır. Öğrenci numarası, telefon, e-posta ve kimlik numarası içeren alanlar anonimleştirilir. Anonimleştirilmemiş öğrenci kayıtları haricî model API'sine gönderilmez. Bir belgenin internette bulunması, onun deney veri setinde kullanılmasına otomatik izin vermez.

## saklama | Deney kayıtlarının saklanması
Örnek deney günlükleri 30 gün saklanır. Günlüklerde ham kullanıcı sorusu yerine deney kimliği ve hata türü tutulur. API anahtarları, erişim jetonları ve parolalar günlüklere yazılmaz. Otuz günlük sürenin sonunda kayıtlar silinir. Yayına eklenen toplulaştırılmış metrikler kişisel veri içermiyorsa proje arşivinde korunabilir.

## paylasim | Veri seti paylaşımı
Veri seti paylaşılmadan önce belge izinleri ve anonimleştirme kontrol edilir. Her belgeye kaynak, sürüm tarihi ve kullanım izni notu eklenir. İzin bilgisi bilinmeyen belge ortak veri setine alınmaz. Deney raporunda kullanılan corpus sürümünün özeti ve hash değeri belirtilir. Ekip dışına paylaşım proje sorumlusunun onayını gerektirir.

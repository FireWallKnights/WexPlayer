🎵 WexPlayer Pro - Ultimate Edition
Müziğin Gücünü Elinizin Altına Getirin! 🚀
WexPlayer Pro, modern müzik dinleme deneyimini yeniden tanımlayan, tamamen ücretsiz ve açık kaynaklı bir masaüstü müzik oynatıcısıdır. Spotify tarzı şık arayüzü, YouTube entegrasyonu ve güçlü özellikleriyle müzik koleksiyonunuzu yönetmenin en akıllı yolu!

✨ Özellikler
🎧 Çevrimiçi ve Çevrimdışı Dinleme

YouTube Entegrasyonu: YouTube'dan direkt şarkı arayın ve dinleyin
Akıllı İndirme: Sevdiğiniz şarkıları yüksek kalitede (192kbps MP3) indirin
Çevrimdışı Mod: İndirdiğiniz şarkıları internet olmadan dinleyin

📚 Gelişmiş Kütüphane Yönetimi

Akıllı Kategorilendirme: Albümler, playlistler ve favoriler
Güçlü Arama: Başlık, sanatçı ve türe göre hızlı arama
Otomatik Metadata: Şarkı bilgileri ve kapak resimleri otomatik kaydedilir

📊 İstatistikler ve Analiz

Dinleme Geçmişi: Son 30 günlük dinleme istatistiklerinizi görün
En Çok Dinlenenler: Favori şarkılarınızı keşfedin
Tür Dağılımı: Müzik zevkinizi grafiklerle analiz edin

🎨 Kişiselleştirilebilir Arayüz

5 Farklı Tema: Yeşil (Spotify), Mavi, Mor, Kırmızı, Turuncu
Karanlık Mod: Gözleriniz için rahat bir deneyim
Modern Tasarım: CustomTkinter ile oluşturulmuş şık ve akıcı arayüz

🎵 Profesyonel Müzik Özellikleri

Playlist Yönetimi: Sınırsız playlist oluşturun ve düzenleyin
Albüm Koleksiyonu: Şarkılarınızı albümlere organize edin
Şarkı Sözleri: Entegre lyrics API ile şarkı sözlerini görüntüleyin
Shuffle & Repeat: Karışık çalma ve tekrar modu

⚙️ Akıllı Özellikler

Uyku Zamanlayıcı: 15-60 dakika arası otomatik kapanma
Klavye Kısayolları: Hızlı kontrol için kısayollar

Space: Oynat/Duraklat
Ctrl+F: Arama
Ctrl+L: Kütüphane
←/→: Geri/İleri 10 saniye
↑/↓: Ses artır/azalt


Sağ Tık Menüsü: Şarkıları albüm ve playlist'lere hızlıca ekleyin


🖥️ Sistem Gereksinimleri
Minimum Gereksinimler:

İşletim Sistemi: Windows 10/11 (64-bit)
RAM: 2 GB
Depolama: 100 MB (program) + müzik koleksiyonunuz için alan
İnternet: YouTube'dan şarkı aramak için (çevrimdışı dinleme için gerekli değil)

Önerilen Gereksinimler:

İşletim Sistemi: Windows 11
RAM: 4 GB veya üzeri
Depolama: 500 MB + müzik için alan
İnternet: Stabil bağlantı (indirme için)


📥 Kurulum Rehberi
Yöntem 1: EXE Dosyasını Kullanma (Önerilen - En Kolay)

İndirin

WexPlayer_Pro.exe dosyasını indirin
Herhangi bir klasöre kaydedin (örn: C:\Program Files\WexPlayer)


FFmpeg Kurulumu (Gerekli!)
Otomatik Kurulum (Chocolatey ile):

bash   # PowerShell'i Yönetici olarak açın
   Set-ExecutionPolicy Bypass -Scope Process -Force
   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
   iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   
   # FFmpeg'i kurun
   choco install ffmpeg
Manuel Kurulum:

FFmpeg İndir
ZIP'i çıkarın
ffmpeg.exe dosyasını şu konumlardan birine kopyalayın:

C:\Windows\System32\
Veya WexPlayer_Pro.exe ile aynı klasöre




Çalıştırın

WexPlayer_Pro.exe dosyasına çift tıklayın
İlk açılışta Windows SmartScreen uyarısı çıkabilir
"Ek bilgi" → "Yine de çalıştır" seçin


Hazır! 🎉

Program otomatik olarak gerekli klasörleri oluşturacak
Müzik aramaya başlayabilirsiniz!




Yöntem 2: Python ile Çalıştırma (Geliştiriciler İçin)
Adım 1: Python Kurulumu
bash# Python 3.8 veya üzeri gerekli
python --version
Python İndir (3.8+)
Adım 2: Gerekli Kütüphaneleri Yükleyin
bash# Tüm bağımlılıkları yükle
pip install pygame
pip install customtkinter
pip install Pillow
pip install yt-dlp
pip install mutagen
pip install requests
pip install numpy
Veya tek komutla:
bashpip install pygame customtkinter Pillow yt-dlp mutagen requests numpy
Adım 3: FFmpeg Kurulumu
Yukarıdaki FFmpeg kurulum adımlarını takip edin.
Adım 4: Programı Çalıştırın
bashpython wexplayer.py
```

---

## 🛠️ İlk Kurulum Sonrası Yapılandırma

### 1. Tema Seçimi
- Ayarlar (⚙️) → Tema Rengi
- Beğendiğiniz temayı seçin
- Programı yeniden başlatın

### 2. Klasör Yapısı
Program çalıştığında otomatik olarak şu klasörler oluşturulur:
```
WexPlayer_Pro_v12/
├── Music/              # İndirilen şarkılar
├── Covers/            # Albüm kapakları
├── Cache/             # Geçici dosyalar
├── Playlists/         # Playlist verileri
├── wex_library_v12.db # Veritabanı
└── settings.json      # Ayarlar
3. İlk Şarkınızı Ekleyin

🔍 "Müzik Ara" bölümüne gidin
Şarkı adı veya sanatçı yazın
"🔍 ARA" butonuna tıklayın
Sonuçlardan:

▶ Dinle: Online dinle
💾 İndir: Kütüphaneye ekle
❤️: Favorilere ekle




📖 Kullanım Kılavuzu
🎵 Şarkı İndirme

Arama bölümüne şarkı adını yazın
Sonuçları inceleyin
"💾 İndir" butonuna tıklayın
İndirme tamamlanınca kütüphanede görünecek

📋 Playlist Oluşturma

"📋 Playlistler" bölümüne gidin
"+ Yeni Playlist" butonuna tıklayın
İsim ve açıklama girin
Kütüphaneden şarkılara sağ tıklayıp ekleyin

💿 Albüm Oluşturma

"💿 Albümler" bölümüne gidin
"+ Yeni Albüm" butonuna tıklayın
Albüm adı ve kapak resmi seçin
Şarkılara sağ tıklayarak albüme ekleyin

🎤 Şarkı Sözlerini Görüntüleme

Herhangi bir şarkının yanındaki "🎤" butonuna tıklayın
Şarkı sözleri otomatik yüklenecek
Lyrics bulunamazsa manuel ekleyebilirsiniz


🐛 Sorun Giderme
"FFmpeg bulunamadı" Hatası
Çözüm:
bash# Komut satırında test edin
ffmpeg -version

# Çıktı gelmezse FFmpeg kurulumu yapın (yukarıdaki adımlar)
Antivirüs Programı EXE'yi Engelliyor
Çözüm:

Bu yanlış bir alarmıdır (False Positive)
Antivirüs programınıza WexPlayer_Pro.exe dosyasını istisna olarak ekleyin
Program tamamen güvenlidir ve açık kaynak kodludur

Program Açılmıyor
Çözüm 1: Visual C++ Redistributable yükleyin

Microsoft Visual C++ İndir

Çözüm 2: .NET Framework güncelleyin

.NET Framework İndir

Şarkı İndirilmiyor
Kontrol Listesi:

✅ İnternet bağlantınız aktif mi?
✅ FFmpeg kurulu mu? (ffmpeg -version)
✅ Disk alanınız yeterli mi?
✅ Antivirüs indirmeyi engelliyor mu?

Veritabanı Hatası
Çözüm:

Programı kapatın
WexPlayer_Pro_v12/wex_library_v12.db dosyasını silin
Programı yeniden başlatın (yeni veritabanı oluşturulur)


🎯 İpuçları ve Püf Noktaları
⚡ Performans İpuçları

Cache klasörünü düzenli temizleyin
500+ şarkıdan fazla indirirseniz albümlere kategorileyin
Gereksiz thumbnail'leri silin

🎨 Özelleştirme

Temalar arasında geçiş yaparak en sevdiğinizi bulun
Equalizer (görsel) ile atmosfer yaratın
Bildirimler ayarlarını ihtiyacınıza göre düzenleyin

💡 Verimlilik

Klavye kısayollarını öğrenin (Space, Ctrl+F, vb.)
Playlist kullanarak müzik yolculukları oluşturun
Favoriler özelliğiyle hızlı erişim sağlayın


📊 Teknik Detaylar
Kullanılan Teknolojiler

GUI Framework: CustomTkinter (Modern UI)
Ses Motoru: Pygame Mixer
Video İndirme: yt-dlp
Metadata: Mutagen (MP3 tags)
Veritabanı: SQLite3
Görsel İşleme: Pillow (PIL)

Özellikler

Thread-safe veritabanı işlemleri
Akıllı cache yönetimi
Otomatik metadata senkronizasyonu
Güvenli dosya işlemleri


🤝 Destek ve İletişim
Sorunuz mu var?

GitHub Issues üzerinden bildirin
Detaylı hata açıklaması ekleyin
Ekran görüntüleri paylaşın

Katkıda Bulunun

Fork yapın
Yeni özellikler ekleyin
Pull request gönderin




✅ Ücretsiz kullanım
✅ Kaynak kodu değiştirme
✅ Ticari kullanım
✅ Dağıtım


🎉 Başlarken
bash# Hızlı Başlangıç (3 Adım)

1. FFmpeg'i kurun
2. WexPlayer_Pro.exe'yi çalıştırın  
3. Müziğin keyfini çıkarın! 🎵

🌟 Teşekkürler!
WexPlayer Pro'yu seçtiğiniz için teşekkür ederiz! Müzik dinleme deneyiminizi bir üst seviyeye taşıyın! 🚀
Müziğin gücü parmaklarınızın ucunda! 🎵✨

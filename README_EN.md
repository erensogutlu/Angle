# Angle — Modular Social Engineering Toolkit

<div align="center">

```
╔═╗╔╗╔╔═╗╦  ╔═╗
╠═╣║║║║ ╦║  ║╣
╩ ╩╝╚╝╚═╝╩═╝╚═╝
```

**v1.0.0** — *Developer: Eren | Modular, extensible, professional*

[![Turkish](https://img.shields.io/badge/Language-Türkçe-red?style=flat-square)](README.md)
![Python](https://img.shields.io/badge/python-3.9+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows%20|%20Linux%20|%20macOS-lightgrey?style=flat-square)

</div>

---

> **Legal Disclaimer:** This tool is intended **solely for educational purposes and authorized security testing**. Unauthorized use is strictly prohibited and may lead to legal consequences. The user assumes full responsibility.

---

## Features

| Feature | Description |
|---|---|
| **Phishing (`oltalama`)** | Clones target web pages or deploys built-in templates (Google, Microsoft, Instagram, General). Supports Public IP, domain tunneling, QR codes, and offline asset conversion. |
| **Collector (`toplayici`)** | Independent HTTP listener — captures incoming POST credentials and form data enriched with GeoIP intelligence. |
| **Email (`eposta`)** | Send spoofed email messages via SMTP. Supports HTML formatting, multiple recipients, file attachments, retries, and SSL/TLS. |
| **USB Dropper (`usb`)** | Generates USB-based payload files for Windows, Linux, and macOS. Supports Base64 obfuscation. |
| **Public WAN IP Detection** | Automatically detects the external public WAN IP of the machine and exposes server URLs over the public network. |
| **Offline Proxying** | External images in cloned pages are downloaded and embedded directly as Base64 Data URIs into the HTML, removing external dependencies. |
| **GeoIP Intelligence** | Every captured credential is automatically enriched with real-time Country, City, and ISP data (LRU cached). |
| **Live Terminal Dashboard** | Interactive Rich-based live dashboard during server execution. Shortcuts: `s` (statistics), `l` (logs), `r` (reports), `q` (quit). |

---

## Installation

### Repository Cloning and Setup

```bash
git clone https://github.com/erensogutlu/angle.git
cd angle

# Install dependencies
pip install -r requirements.txt

# Or install in editable/development mode
pip install -e ".[dev]"
```

### Python Version Compatibility

| Python Version | Status |
|---|---|
| Python 3.9 | Supported |
| Python 3.10 | Supported |
| Python 3.11 | Supported |
| Python 3.12+ | Supported |

---

## Usage — Step-by-Step Guide

### 1. Interactive Menu Mode (Wizard)

**What it does:** Launches a step-by-step guided Rich interface without needing to memorize CLI arguments. Modules are automatically discovered.

**Command:**
```bash
python angle.py
```

---

### 2. Phishing Mode (Site Cloning or Built-in Templates)

**What it does:** Clones a target web page or launches built-in phishing templates (Google, Microsoft, Instagram). Handles public WAN IP resolution and external tunnel addresses automatically.

**Scenario A: Live Web Page Cloning from URL**
```bash
python angle.py oltalama --url https://example.com/login --port 8080
```

**Scenario B: Using a Built-in Template (e.g. Google)**
```bash
python angle.py oltalama --sablon google --port 8080
```

**Scenario C: External Tunnel (Ngrok / Cloudflare) Integration**
```bash
python angle.py oltalama --sablon google --port 8080 --dis-url https://custom-subdomain.ngrok-free.app
```

**Interactive Controls During Server Execution:**
- `s` -> Displays live server statistics panel.
- `l` -> Lists recent captured credentials along with GeoIP location data.
- `r` -> Generates interactive `rapor.html` and JSON reports.
- `q` -> Safely stops the server and listener.

---

### 3. Standalone Credential Collector Mode

**What it does:** Starts a lightweight HTTP listener without serving any HTML content, purely logging incoming POST requests and form data.

```bash
python angle.py toplayici --port 9090
```

---

### 4. Email Sending Mode

**What it does:** Dispatches HTML-formatted or plain text email messages to targets via a configured SMTP server.

```bash
python angle.py eposta \
    --gonderen support@company.com \
    --alici target@company.com \
    --konu "Urgent: Password Reset" \
    --mesaj "Please verify your account..." \
    --sunucu smtp.gmail.com \
    --port 587 \
    --kullanici test@gmail.com \
    --sifre "app_password" \
    --html
```

---

### 5. USB Dropper Mode

**What it does:** Generates OS-specific USB payload files for target operating systems (Windows, Linux, macOS).

```bash
python angle.py usb --hedef /media/usb --ip 192.168.1.10 --port 4444 --os linux
```

---

## Quickstart — Sample Test Workflow

```bash
# Step 1: Clone repository and enter directory
git clone https://github.com/erensogutlu/angle.git
cd angle

# Step 2: Install required dependencies
pip install -r requirements.txt

# Step 3: Launch phishing server with built-in Google template
python angle.py oltalama --sablon google --port 8080

# Step 4: Access server from another terminal or browser to test
# Monitor live output on screen. Press Ctrl+C or 'q' to stop.
```

---

## Command-Line Parameters Reference

| Parameter | Short | Module | Required? | Description |
|---|---|---|---|---|
| `--url` | - | `oltalama` | No | Target website URL to clone |
| `--sablon` | - | `oltalama` | No | Built-in template name (`google`, `microsoft`, `instagram`, `genel`) |
| `--port` | - | All | No | Server listening port (Default: 8080 / 9090) |
| `--dinle` | - | `oltalama`, `toplayici` | No | Bind address (Default: 0.0.0.0) |
| `--dis-url` | - | `oltalama`, `toplayici` | No | External public tunnel/domain URL (ngrok, cloudflare) |
| `--https` | - | `oltalama` | No | Enable HTTPS with self-signed SSL certificate |
| `--gonderen` | - | `eposta` | Yes | Sender email address |
| `--alici` | - | `eposta` | Yes | Recipient email address |
| `--konu` | - | `eposta` | Yes | Email subject line |
| `--mesaj` | - | `eposta` | Yes | Email body text |
| `--sunucu` | - | `eposta` | Yes | SMTP server host (`smtp.gmail.com`, etc.) |
| `--kullanici` | - | `eposta` | Yes | SMTP username |
| `--sifre` | - | `eposta` | Yes | SMTP password / App password |
| `--html` | - | `eposta` | No | Send email as HTML formatted |
| `--ek` | - | `eposta` | No | File attachment path |
| `--hedef` | - | `usb` | Yes | Target USB mount path / directory |
| `--ip` | - | `usb` | Yes | Listener IP address for payload connection |
| `--os` | - | `usb` | Yes | Target OS (`windows`, `linux`, `macos`) |
| `--version` | `-V` | General | No | Display tool version |
| `--help` | `-h` | General | No | Display command help menu |

---

## Configuration Hierarchy

Configuration settings are resolved in 4 levels of priority:

1. **CLI Arguments** (Highest priority)
2. **Environment Variables** (`ANGLE_PORT`, `ANGLE_LOG_LEVEL`, `ANGLE_HTTPS`)
3. **Configuration File** (`angle_modulleri/ayarlar.json`)
4. **Default Values** (`Yapilandirma` dataclass)

```bash
# Example environment variable definition
export ANGLE_PORT=9090
export ANGLE_LOG_LEVEL=DEBUG
export ANGLE_HTTPS=true
```

---

## Architecture Overview

```
angle/
├── angle.py                  # Entry point (CLI & interactive wizard)
├── pyproject.toml             # PEP 621 package metadata & configuration
├── requirements.txt           # Package dependencies
├── angle_modulleri/
│   ├── __init__.py            # Automatic plugin discovery engine
│   ├── konsol.py              # Rich-based terminal UI framework
│   ├── yardimci.py            # Helpers: Config, GeoIP, Public IP, SSL
│   ├── sunucu.py              # Thread-safe, rate-limited HTTP server
│   ├── oltalama.py            # Phishing & web site cloning module
│   ├── toplayici.py           # Credential & form collector
│   ├── eposta_sahte.py        # Spoofed email sender module
│   ├── usb_damlat.py          # USB dropper payload builder
│   └── sablonlar/             # Built-in HTML templates
└── testler/                   # Unit test suite (53 tests)
```

---

## Security & Reliability Features

- **Thread-Safe Logging:** Lock-protected file writes preventing data corruption under concurrent requests.
- **Path Traversal Protection:** File path validation preventing `../` directory traversal attacks.
- **Rate Limiting:** Request frequency restrictions per client IP to mitigate denial of service.
- **Offline Proxying:** Automatic Base64 inline conversion of external images for zero-dependency execution.
- **Graceful Shutdown:** Interruption handling via Ctrl+C or `q` to safely finalize logs and report generation.

---

## Frequently Asked Questions (FAQ)

**Q: Images in the cloned web page do not display, what should I do?**
Angle automatically downloads and converts external images in cloned web pages into Base64 Data URIs (Offline Proxying). As long as internet connectivity is active during cloning, images load properly offline.

**Q: How do I expose the server over the public internet?**
The tool automatically detects your public WAN IP address. Additionally, you can pass `--dis-url` with your `ngrok` or `cloudflare tunnel` domain to make the server accessible globally.

**Q: Port binding conflict error?**
Specify a different available port using `--port 8081`.

---

## Plugin System

To add a new module, create a `.py` file under `angle_modulleri/` and define a `MODUL_BILGI` dictionary:

```python
# angle_modulleri/new_module.py

MODUL_BILGI = {
    "ad": "New Module",
    "aciklama": "Module description",
    "giris_noktasi": "start",  # Function name to execute
    "komut": "newmod",         # CLI sub-command
}

def start():
    """Module entry point"""
    print("New module running!")
```

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

**Developer:** Eren  
**Version:** 1.0.0  
**Platform:** Windows / Linux / macOS

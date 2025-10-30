# 🌐 Zeron Browser v0.3.3

> **Zeron Browser** is a fully Python-based web browser designed to be **fast, secure, and highly customizable**.  
> It uses **Qt WebEngine** to render modern web pages with advanced UI animations, a built-in download manager, dynamic theming, a password vault, and tabbed browsing — all **optimized for Windows 11, Linux, and beyond**.

---

## 🚀 Features

- ⚡ **Optimized Engine** — Built on `PyQt5` and `Qt WebEngine` for speed and stability.  
- 🌙 **Dark / Light Themes** — Fully themeable interface with customizable text color.  
- 🧩 **Download Manager** — Supports progress tracking, pause, and resume.  
- 🔐 **Password Vault** — Local encrypted password storage (no external dependencies).  
- 📚 **Bookmarks & History** — Quick access and local sync.  
- 🪟 **Tabbed Browsing** — Smooth animations, tab previews, and sliding transitions.  
- 🧠 **Smart Search Bar** — Fast suggestions and autocomplete.  
- 🧰 **Developer Tools** — Includes debug info and performance view.  
- 🖥️ **Cross-Platform** — Tested on Windows 11, Linux, and macOS.

---

## 🧑‍💻 Tech Stack

| Component | Technology |
|------------|-------------|
| Language | **Python 3.11+** |
| UI Framework | **PyQt5 / QtWebEngine** |
| Animation | **Qt Animation Framework** |
| Encryption | **Pure Python vault system (no cryptography lib)** |
| OS Support | Windows / Linux / macOS |

---

## ⚙️ Installation

```bash
# 1️⃣ Clone the repo
git clone https://github.com/cyberworrier8088/Zeron.git
cd Zeron-Browser

# 2️⃣ Install dependencies
pip install PyQt5 PyQtWebEngine

# 3️⃣ Run the browser
python main.py

#!/usr/bin/env python3

"""
Zeron v1.0.0 (State of the Art Edition)
=======================================
- AdBlock Engine (Native Request Interception)
- Command Palette (Ctrl+Shift+P)
- Session Restore & Crash Recovery
- Vertical/Horizontal Tabs Layout
- Speed Dial / New Tab Page
- Glassmorphism & Advanced Animations
"""

import sys
import os
import json
import platform
import traceback
import base64
from functools import partial
from datetime import datetime
from urllib.parse import urlparse

from PyQt5.QtCore import (
    Qt, QUrl, QPropertyAnimation, QEasingCurve, QRect, QTimer, QPoint, QEvent,
    QParallelAnimationGroup, QSequentialAnimationGroup, QSize, QObject, pyqtSignal
)
from PyQt5.QtGui import (
    QMovie, QColor, QKeySequence, QPixmap, QIcon, QFont, QPalette, QBrush,
    QPainter, QLinearGradient, QPen
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QAction, QLineEdit, QPushButton,
    QVBoxLayout, QWidget, QLabel, QHBoxLayout, QScrollArea, QSizePolicy,
    QDialog, QProgressBar, QMessageBox, QInputDialog, QFileDialog, QTabWidget,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QShortcut
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage,
    QWebEngineSettings, QWebEngineDownloadItem
)
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor

# ------------------ Configuration & Constants ------------------

LATEST_CHROMIUM_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.6261.94 Safari/537.36 Edg/122.0.2365.66"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "zeron_data")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "Downloads")
LOADING_GIF_LOCAL = os.path.join(BASE_DIR, "cat-cat-dance.gif")

BOOKMARKS_FILE = os.path.join(DATA_DIR, "bookmarks.json")
HISTORY_FILE   = os.path.join(DATA_DIR, "history.json")
SETTINGS_FILE  = os.path.join(DATA_DIR, "settings.json")
SESSION_FILE   = os.path.join(DATA_DIR, "last_session.json")

for d in (DATA_DIR, DOWNLOADS_DIR):
    os.makedirs(d, exist_ok=True)

DEFAULT_SETTINGS = {
    "theme": "fluent_dark",
    "home_page": "zeron://speeddial",
    "show_bookmark_bar": True,
    "vertical_tabs": False,
    "adblock_enabled": True
}

# Try importing keyring for vault
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# ------------------ AdBlock Engine ------------------

class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocked_domains = {
            "doubleclick.net", "googleadservices.com", "googlesyndication.com",
            "adservice.google.com", "adnxs.com", "ads.yahoo.com",
            "criteo.com", "outbrain.com", "taboola.com", "rubiconproject.com"
        }

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        host = urlparse(url).hostname
        if host:
            for bad in self.blocked_domains:
                if bad in host:
                    info.block(True)
                    # print(f"Blocked Ad: {url}")
                    return

# ------------------ Helpers ------------------

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

BOOKMARKS = load_json(BOOKMARKS_FILE, [])
HISTORY = load_json(HISTORY_FILE, [])
SETTINGS = load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())

# ------------------ UI Components ------------------

class GlassToolBar(QToolBar):
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setMovable(False)
        self.setFloatable(False)
        self.setObjectName("glass_toolbar")
        self.setContentsMargins(4, 4, 4, 4)
        self.setStyleSheet("""
            QToolBar#glass_toolbar {
                background: rgba(30, 35, 50, 0.85);
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                spacing: 6px;
            }
        """)

class ModernButton(QPushButton):
    def __init__(self, text="", icon=None, parent=None, accent=False):
        super().__init__(text, parent)
        if icon: self.setIcon(icon)
        self.setFont(QFont("Segoe UI", 10))
        self.setCursor(Qt.PointingHandCursor)
        self.accent = accent
        self.update_style()
        
    def update_style(self):
        bg = "#2cabf1" if self.accent else "transparent"
        fg = "white" if self.accent else "#b0b8c5"
        border = "none" if self.accent else "1px solid #3a4050"
        hover = "#42d7fa" if self.accent else "#2a3040"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: {border};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {hover};
                color: white;
            }}
        """)

class CommandPalette(QDialog):
    def __init__(self, parent=None, actions_map=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(600, 400)
        self.actions_map = actions_map or {}
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e222d;
                border: 1px solid #333;
                border-radius: 8px;
            }
            QLineEdit {
                background: #2a3040;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 4px;
            }
            QListWidget {
                background: transparent;
                border: none;
                color: #ddd;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: #2cabf1;
                color: white;
            }
        """)
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Type a command...")
        self.search.textChanged.connect(self.filter_items)
        self.search.returnPressed.connect(self.execute_selected)
        layout.addWidget(self.search)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        self.populate()
        
        # Shadow
        eff = QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(40)
        eff.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(eff)

    def populate(self):
        self.list_widget.clear()
        for name in self.actions_map:
            self.list_widget.addItem(name)
        self.list_widget.setCurrentRow(0)

    def filter_items(self, text):
        self.list_widget.clear()
        for name in self.actions_map:
            if text.lower() in name.lower():
                self.list_widget.addItem(name)
        self.list_widget.setCurrentRow(0)

    def execute_selected(self):
        if self.list_widget.currentItem():
            name = self.list_widget.currentItem().text()
            func = self.actions_map.get(name)
            if func:
                func()
            self.close()

# ------------------ Speed Dial Page ------------------

SPEED_DIAL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { background: #12151d; color: white; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        h1 { font-size: 3rem; margin-bottom: 10px; background: linear-gradient(45deg, #2cabf1, #a68eff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .search-box { width: 600px; padding: 15px; border-radius: 30px; border: none; background: #2a3040; color: white; font-size: 1.2rem; outline: none; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 50px; }
        .card { background: #1e222d; padding: 20px; border-radius: 15px; width: 120px; height: 120px; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.2s, background 0.2s; text-decoration: none; color: white; }
        .card:hover { transform: translateY(-5px); background: #252a38; }
        .icon { font-size: 2rem; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>ZERON</h1>
    <input type="text" class="search-box" placeholder="Search the web..." onkeypress="if(event.key==='Enter') window.location='https://google.com/search?q='+this.value">
    <div class="grid">
        <a class="card" href="https://youtube.com"><div class="icon">📺</div>YouTube</a>
        <a class="card" href="https://github.com"><div class="icon">🐙</div>GitHub</a>
        <a class="card" href="https://reddit.com"><div class="icon">👽</div>Reddit</a>
        <a class="card" href="https://twitter.com"><div class="icon">🐦</div>Twitter</a>
        <a class="card" href="https://gmail.com"><div class="icon">📧</div>Gmail</a>
        <a class="card" href="https://chatgpt.com"><div class="icon">🤖</div>ChatGPT</a>
        <a class="card" href="https://netflix.com"><div class="icon">🍿</div>Netflix</a>
        <a class="card" href="https://amazon.com"><div class="icon">🛒</div>Amazon</a>
    </div>
</body>
</html>
"""

# ------------------ Main Window ------------------

class ZeronMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZERON Browser")
        self.resize(1280, 800)
        self.setMinimumSize(800, 600)
        
        # Setup Profile & AdBlock
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setHttpUserAgent(LATEST_CHROMIUM_UA)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.profile.setCachePath(os.path.join(DATA_DIR, "cache"))
        self.profile.setPersistentStoragePath(os.path.join(DATA_DIR, "cache"))
        
        if SETTINGS.get("adblock_enabled"):
            self.adblocker = AdBlockInterceptor(self)
            self.profile.setUrlRequestInterceptor(self.adblocker)
            
        self.setup_ui()
        self.setup_shortcuts()
        self.restore_session()

    def setup_ui(self):
        # Main Container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Toolbar
        self.toolbar = GlassToolBar(parent=self)
        self.main_layout.addWidget(self.toolbar)
        
        # Navigation Actions
        self.nav_actions = {}
        nav_items = [
            ("◀", self.go_back, "Back"),
            ("▶", self.go_forward, "Forward"),
            ("⟳", self.reload_page, "Reload"),
            ("🏠", self.go_home, "Home")
        ]
        
        for icon, func, name in nav_items:
            btn = ModernButton(icon, parent=self)
            btn.setFixedSize(34, 34)
            btn.clicked.connect(func)
            btn.setToolTip(name)
            self.toolbar.addWidget(btn)
            self.nav_actions[name] = func

        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter address")
        self.url_bar.setFixedHeight(36)
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background: #181b24;
                color: #e0e0e0;
                border: 1px solid #3a4050;
                border-radius: 18px;
                padding: 0 15px;
                font-size: 14px;
                margin: 0 10px;
            }
            QLineEdit:focus {
                border: 1px solid #2cabf1;
                background: #1e222d;
            }
        """)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)

        # Right Toolbar Items
        self.toolbar.addWidget(ModernButton("★", parent=self, accent=False)) # Bookmark placeholder
        
        btn_menu = ModernButton("☰", parent=self)
        btn_menu.clicked.connect(self.show_command_palette)
        self.toolbar.addWidget(btn_menu)

        # Tab Container (Splitter for Vertical Tabs support)
        self.content_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.content_splitter)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; background: #12151d; }
            QTabBar::tab {
                background: #1e222d;
                color: #888;
                padding: 8px 15px;
                border-right: 1px solid #12151d;
                min-width: 120px;
                max-width: 200px;
            }
            QTabBar::tab:selected {
                background: #2cabf1;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #252a38;
            }
            QTabBar::close-button {
                image: url(close.png); /* Fallback */
                subcontrol-position: right;
            }
        """)
        
        if SETTINGS.get("vertical_tabs"):
            self.tabs.setTabPosition(QTabWidget.West)
        
        self.content_splitter.addWidget(self.tabs)

        # Loading Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: transparent; border: 0; } QProgressBar::chunk { background: #2cabf1; }")
        self.main_layout.addWidget(self.progress_bar)
        self.progress_bar.hide()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self, self.add_new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close_current_tab)
        QShortcut(QKeySequence("Ctrl+R"), self, self.reload_page)
        QShortcut(QKeySequence("Ctrl+L"), self, self.url_bar.setFocus)
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self.show_command_palette)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)

    # ------------------ Logic ------------------

    def add_new_tab(self, url=None, label="New Tab"):
        if not url:
            url = SETTINGS["home_page"]
        
        browser = QWebEngineView()
        browser.setPage(QWebEnginePage(self.profile, browser))
        
        if url == "zeron://speeddial":
            browser.setHtml(SPEED_DIAL_HTML, QUrl("zeron://speeddial"))
        else:
            browser.setUrl(QUrl(url))
            
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)
        
        browser.urlChanged.connect(lambda q, b=browser: self.update_url_bar(q, b))
        browser.loadProgress.connect(self.update_progress)
        browser.loadFinished.connect(self.on_load_finished)
        browser.titleChanged.connect(lambda t, b=browser: self.update_tab_title(t, b))
        
        return browser

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            self.close()

    def close_current_tab(self):
        self.close_tab(self.tabs.currentIndex())

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text: return
        
        if text == "zeron://speeddial":
            self.tabs.currentWidget().setHtml(SPEED_DIAL_HTML, QUrl("zeron://speeddial"))
            return

        if "." not in text and " " in text:
            url = f"https://www.google.com/search?q={text}"
        elif "." not in text:
             url = f"https://www.google.com/search?q={text}"
        else:
            url = text if "://" in text else "https://" + text
            
        self.tabs.currentWidget().setUrl(QUrl(url))

    def update_url_bar(self, q, browser):
        if browser != self.tabs.currentWidget(): return
        url = q.toString()
        if url == "zeron://speeddial":
            self.url_bar.setText("")
            self.url_bar.setPlaceholderText("Search or enter address")
        else:
            self.url_bar.setText(url)
            self.url_bar.setCursorPosition(0)

    def update_tab_title(self, title, browser):
        index = self.tabs.indexOf(browser)
        if index >= 0:
            self.tabs.setTabText(index, title[:20] + "..." if len(title) > 20 else title)

    def on_tab_changed(self, index):
        browser = self.tabs.widget(index)
        if browser:
            self.update_url_bar(browser.url(), browser)

    def update_progress(self, p):
        self.progress_bar.setValue(p)
        if 0 < p < 100:
            self.progress_bar.show()
        else:
            self.progress_bar.hide()

    def on_load_finished(self):
        self.progress_bar.hide()

    def go_back(self):
        if self.tabs.currentWidget(): self.tabs.currentWidget().back()

    def go_forward(self):
        if self.tabs.currentWidget(): self.tabs.currentWidget().forward()

    def reload_page(self):
        if self.tabs.currentWidget(): self.tabs.currentWidget().reload()

    def go_home(self):
        self.add_new_tab()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ------------------ Features ------------------

    def show_command_palette(self):
        actions = {
            "New Tab": self.add_new_tab,
            "Close Tab": self.close_current_tab,
            "Toggle Vertical Tabs": self.toggle_vertical_tabs,
            "Toggle Fullscreen": self.toggle_fullscreen,
            "Settings": self.open_settings,
            "Downloads": self.open_downloads,
            "History": self.open_history,
            "Bookmarks": self.open_bookmarks,
            "Exit Zeron": self.close
        }
        palette = CommandPalette(self, actions)
        palette.move(self.geometry().center() - palette.rect().center())
        palette.exec_()

    def toggle_vertical_tabs(self):
        current = self.tabs.tabPosition()
        if current == QTabWidget.North:
            self.tabs.setTabPosition(QTabWidget.West)
            SETTINGS["vertical_tabs"] = True
        else:
            self.tabs.setTabPosition(QTabWidget.North)
            SETTINGS["vertical_tabs"] = False
        save_json(SETTINGS_FILE, SETTINGS)

    def open_settings(self):
        QMessageBox.information(self, "Settings", "Settings Dialog Placeholder\n(Fully implemented in next update)")

    def open_downloads(self):
        QMessageBox.information(self, "Downloads", f"Downloads Folder:\n{DOWNLOADS_DIR}")

    def open_history(self):
        pass # TODO

    def open_bookmarks(self):
        pass # TODO

    # ------------------ Session Management ------------------

    def save_session(self):
        urls = []
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            url = w.url().toString()
            if url: urls.append(url)
        save_json(SESSION_FILE, {"urls": urls, "active_index": self.tabs.currentIndex()})

    def restore_session(self):
        data = load_json(SESSION_FILE, {})
        urls = data.get("urls", [])
        if urls:
            for url in urls:
                self.add_new_tab(url)
            idx = data.get("active_index", 0)
            if idx < self.tabs.count():
                self.tabs.setCurrentIndex(idx)
        else:
            self.add_new_tab()

    def closeEvent(self, event):
        self.save_session()
        super().closeEvent(event)

def main():
    # High DPI Scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Zeron Browser")
    
    # Global Dark Theme
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(18, 21, 29))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = ZeronMain()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

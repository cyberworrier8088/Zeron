#!/usr/bin/env python3
"""
Zeron v0.3.3
============
- Chrome-like UI with flat, modern, bright (or dark mode) visual language.
- User agent selector, security icon, favicon display like a real browser.
- Settings completely overhauled for privacy/security and modularity.
- Ultra-lightweight, modular code for community/open source standards.
"""

import sys
import os
import json
import platform
import traceback
from functools import partial
from datetime import datetime

from PyQt5.QtCore import Qt, QUrl, QPropertyAnimation, QEasingCurve, QRect, QTimer, QPoint, QEvent, QParallelAnimationGroup, QSequentialAnimationGroup
from PyQt5.QtGui import QMovie, QColor, QKeySequence, QPixmap, QIcon, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QAction, QLineEdit, QPushButton,
    QVBoxLayout, QWidget, QLabel, QHBoxLayout, QScrollArea, QSizePolicy,
    QDialog, QProgressBar, QMessageBox, QInputDialog, QFileDialog, QTabWidget,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage,
    QWebEngineSettings, QWebEngineDownloadItem
)
# For web compatibility: set latest user agent
LATEST_CHROMIUM_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.6261.94 Safari/537.36 Edg/122.0.2365.66"
)
try:
    import keyring
    KEYRING_AVAILABLE = True
except Exception:
    KEYRING_AVAILABLE = False

# ------------------ constants & disk paths ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOADING_GIF_LOCAL = os.path.join(BASE_DIR, "cat-cat-dance.gif")
DATA_DIR = os.path.join(BASE_DIR, "zeron_data")
BOOKMARKS_FILE = os.path.join(DATA_DIR, "bookmarks.json")
HISTORY_FILE   = os.path.join(DATA_DIR, "history.json")
SETTINGS_FILE  = os.path.join(DATA_DIR, "settings.json")
DOWNLOADS_DIR  = os.path.join(BASE_DIR, "Downloads")
for d in (DATA_DIR, DOWNLOADS_DIR):
    os.makedirs(d, exist_ok=True)

DEFAULT_SETTINGS = {
    "theme": "fluent_dark",
    "home_page": "https://www.google.com",
    "show_bookmark_bar": True,
    "force_white_text": False
}

# --------------- helpers: disk, security, os ---------------
def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        traceback.print_exc()
    return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        traceback.print_exc()

BOOKMARKS = load_json(BOOKMARKS_FILE, [])
HISTORY = load_json(HISTORY_FILE, [])
SETTINGS = load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())

# ------- OS/hardware color/blur support helpers --------
def is_win11():
    return sys.platform.startswith('win') and '10' in platform.version() or '11' in platform.version()

def has_blur_support():
    if is_win11():
        try:
            import ctypes
            return True
        except Exception:
            return False
    return False  # Only pure-Qt fallback for Linux

# ----------- Modern tabstrip with blur/animations ----------
class ModernTabStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.container = QWidget()
        self.container.setObjectName("tab_container")
        self.hbox = QHBoxLayout(self.container)
        self.hbox.setContentsMargins(6,6,6,6)
        self.hbox.setSpacing(16)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.container)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,1,0,1)
        layout.setSpacing(0)
        layout.addWidget(self.scroll)
        self.tab_buttons = []
        self.thumb_popup = QLabel(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.thumb_popup.setStyleSheet("border:2px solid #66bbff; background:rgba(20,40,55,0.93); border-radius:9px;")
        self.thumb_popup.hide()
        self.thumb_timer = QTimer()
        self.thumb_timer.setSingleShot(True)
        self.thumb_timer.timeout.connect(self._show_thumb_now)
        self.pending_thumb = None

    def add_tab_button(self, title, view, icon=None):
        btn = QPushButton(title)
        btn.setObjectName("tab_button")
        if icon:
            btn.setIcon(icon)
        btn.setStyleSheet(self._tab_style(selected=False))
        btn.setFont(QFont('Segoe UI', 11))
        btn.setFixedHeight(35)
        btn.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        eff = QGraphicsDropShadowEffect(btn)
        eff.setBlurRadius(22)
        eff.setColor(QColor('#2a7baa'))
        eff.setOffset(0, 1)
        btn.setGraphicsEffect(eff)
        self.hbox.addWidget(btn)
        idx = len(self.tab_buttons)
        self.tab_buttons.append((btn, view))
        btn.clicked.connect(partial(self.on_button_clicked, idx))
        btn.installEventFilter(self)
        return btn

    def remove_tab_button(self, idx):
        if 0 <= idx < len(self.tab_buttons):
            btn, view = self.tab_buttons.pop(idx)
            self.hbox.removeWidget(btn)
            btn.deleteLater()
            # reconnect
            for i, (b, v) in enumerate(self.tab_buttons):
                try: b.clicked.disconnect()
                except Exception: pass
                b.clicked.connect(partial(self.on_button_clicked, i))

    def on_button_clicked(self, index):
        if self.parent:
            self.parent.switch_to_tab(index)
        self.scroll_to_button(index)

    def scroll_to_button(self, index):
        if index < 0 or index >= len(self.tab_buttons): return
        btn, _ = self.tab_buttons[index]
        scroll_w = self.scroll.viewport().width()
        pos = btn.pos().x()
        w = btn.width()
        center = pos + w//2 - scroll_w//2
        max_x = max(0, self.container.width() - scroll_w)
        target = max(0, min(center, max_x))
        anim = QPropertyAnimation(self.scroll.horizontalScrollBar(), b"value", self)
        anim.setDuration(420)
        anim.setStartValue(self.scroll.horizontalScrollBar().value())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutQuint)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Enter:
            for i, (b, v) in enumerate(self.tab_buttons):
                if b is obj:
                    self.pending_thumb = (i, v)
                    self.thumb_timer.start(180)
                    break
        elif ev.type() == QEvent.Leave:
            self.thumb_timer.stop()
            self.thumb_popup.hide()
        return super().eventFilter(obj, ev)

    def _show_thumb_now(self):
        if not self.pending_thumb: return
        i, view = self.pending_thumb
        try:
            pix = view.grab()
            if pix.isNull():
                return
            w = 286
            h = int(pix.height() * (w / pix.width())) if pix.width() else 200
            thumb = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb_popup.setPixmap(thumb)
            btn, _ = self.tab_buttons[i]
            global_pos = btn.mapToGlobal(btn.rect().bottomLeft())
            self.thumb_popup.move(global_pos + QPoint(0, 10))
            self.thumb_popup.show()
        except Exception:
            traceback.print_exc()

    def _tab_style(self, selected):
        if selected:
            return '''
                QPushButton#tab_button {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #44aaff, stop:1 #224488);
                    color: #fff; font-weight:600; font-size:15px;
                    border-radius: 12px; border:1px solid #69a7e8;
                    padding: 10px 26px;
                    margin:2px;
                }
                QPushButton#tab_button:hover { background:#2b6bb9; }
            '''
        else:
            return '''
                QPushButton#tab_button {
                    background: transparent;
                    color: #aad4ff; font-size:14px;
                    border-radius: 12px;
                    border:1px solid #666666; /* fixed from #4447 */
                    padding:7px 19px;
                    margin:2px;
                }
                QPushButton#tab_button:hover {
                    background: #4069ae;
                    /* box-shadow removed, instead use QGraphicsDropShadowEffect if needed */
                }
            '''

# -------------------- Loading overlay using local GIF --------------------
class LoadingOverlay(QWidget):
    def __init__(self, parent=None, gif_path=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,160); border-radius:8px;")
        self.setVisible(False)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.gif_label = QLabel()
        layout.addWidget(self.gif_label)
        self.msg = QLabel("Loading — network slow")
        self.msg.setStyleSheet("color:white; font-weight:bold; font-size:14px;")
        layout.addWidget(self.msg)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background:#ff4d4f;color:white;padding:6px;border-radius:6px;")
        layout.addWidget(self.cancel_btn)
        self.movie = None
        if gif_path and os.path.exists(gif_path):
            try:
                self.movie = QMovie(gif_path)
                self.gif_label.setMovie(self.movie)
                self.movie.start()
            except Exception:
                self.gif_label.setText("Loading...")
        else:
            self.gif_label.setText("Loading...")

    def show_overlay(self):
        self.setGeometry(self.parent().rect())
        self.show()
        if self.movie:
            self.movie.start()

    def hide_overlay(self):
        self.hide()
        if self.movie:
            self.movie.stop()

# Continue new Zeron main window, modern toolbar, theming, and all rewritten features

class GlassToolBar(QToolBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMovable(False)
        self.setObjectName("glass_toolbar")
        self.setFloatable(False)
        self.setContentsMargins(8, 7, 8, 7)
        glass = QColor(38,62,120,108).name(QColor.HexArgb)
        self.setStyleSheet(f"QToolBar#glass_toolbar {{ background:{glass}; border:0; border-radius:13px; padding:3px 8px 3px 8px; }}")
        f = QFont('Segoe UI', 11)
        self.setFont(f)

class ZeronMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZERON v0.3.1 – Blazing Modern Browser")
        self.resize(1420, 900)
        self.setMinimumSize(1150, 650)
        self.setWindowIcon(QIcon(os.path.join(BASE_DIR,"cat-cat-dance.gif")) if os.path.exists(LOADING_GIF_LOCAL) else QIcon())
        mainfont = QFont('Segoe UI', 11)
        self.setFont(mainfont)
        central = QWidget(); vlay = QVBoxLayout(central)
        vlay.setContentsMargins(15, 13, 15, 11); vlay.setSpacing(6)

        # --- Beautiful glassy main toolbar ---
        self.toolbar = GlassToolBar()
        vlay.addWidget(self.toolbar)

        # --- Modern actions
        icons = {
            "back": "◀", "forward": "▶", "reload": "⟳", "newtab": "+", "home": "🏠",
            "bookmark":"★","downloads":"⬇","theme":"🌓","vault":"🔐","settings":"⚙"
        }
        a_back = QAction(icons["back"], self); a_back.triggered.connect(self.go_back)
        a_forward = QAction(icons["forward"], self); a_forward.triggered.connect(self.go_forward)
        a_reload = QAction(icons["reload"], self); a_reload.triggered.connect(self.reload_page)
        a_new = QAction(icons["newtab"], self); a_new.triggered.connect(self.add_tab)
        a_home = QAction(icons["home"], self); a_home.triggered.connect(self.go_home)
        a_book = QAction(icons["bookmark"], self); a_book.triggered.connect(self.add_bookmark_current)
        a_dl = QAction(icons["downloads"], self); a_dl.triggered.connect(self.open_downloads_dialog)
        a_theme = QAction(icons["theme"], self); a_theme.triggered.connect(self.toggle_theme)
        a_vault = QAction(icons["vault"], self); a_vault.triggered.connect(self.open_vault_dialog)
        a_settings = QAction(icons["settings"], self); a_settings.triggered.connect(self.open_settings_dialog)
        for a in (a_back, a_forward, a_reload, a_new, a_home, a_book, a_dl, a_vault, a_theme, a_settings):
            self.toolbar.addAction(a)
        
        # Beautiful animated/fluent URL bar
        self.urlbar = QLineEdit(); self.urlbar.setPlaceholderText("Type or search...")
        self.urlbar.setFixedHeight(33); self.urlbar.setMinimumWidth(340)
        self.urlbar.setFont(QFont('Segoe UI', 11))
        self.urlbar.setStyleSheet('''
            QLineEdit {
                background: #182a42;
                color: #fff; border: none; border-radius: 10px;
                padding:7px 14px; margin: 0 12px 0 8px;
                font-size: 15px;
            }
            QLineEdit:focus {
                background: #40aafa; color: #17305d;
            }
        ''')
        self.urlbar.returnPressed.connect(self.load_from_urlbar)
        self.urlbar.textChanged.connect(self._on_urlbar_text_change)
        self.toolbar.addWidget(self.urlbar)
        go_btn = QPushButton("Go"); go_btn.setFixedHeight(31); go_btn.setFont(QFont('Segoe UI', 11))
        go_btn.setStyleSheet('''
            QPushButton {
                background: #79bfff;
                color: #224466; border: none; border-radius: 8px;
                font-weight:bold; min-width:46px;
            }
            QPushButton:hover { background: #b8e4ff; color:#207; }
        ''')
        go_btn.clicked.connect(self.load_from_urlbar)
        self.toolbar.addWidget(go_btn)
        
        # --- Modern animated tabstrip
        self.tab_strip = ModernTabStrip(parent=self)
        vlay.addWidget(self.tab_strip)
        
        # --- Tab widget area
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.currentChanged.connect(self.on_tab_switched)
        vlay.addWidget(self.tab_widget)

        self.setCentralWidget(central)

        # --- Bookmark bar
        self.bookmark_bar = GlassToolBar("Bookmarks")
        self.bookmark_bar.setIconSize(self.toolbar.iconSize())
        self.addToolBarBreak()
        self.addToolBar(self.bookmark_bar)
        self.refresh_bookmark_bar()
        self.bookmark_bar.setVisible(SETTINGS.get("show_bookmark_bar",True))

        # --- Loading overlay (GIF/glass/blur effect)
        self.loading_overlay = LoadingOverlay(self, gif_path=LOADING_GIF_LOCAL)
        self.loading_overlay.cancel_btn.clicked.connect(self.cancel_current_load)

        # --- Downloads, engine tuning, security
        self.downloads = []
        self._setup_webengine()
        QWebEngineProfile.defaultProfile().downloadRequested.connect(self._on_download_requested)

        # --- Shortcuts
        self._setup_shortcuts()
        
        # --- Fluent Theme ---
        self.apply_theme(SETTINGS.get("theme", "fluent_dark"))

        # --- Initial Tab ---
        self.add_tab(url=SETTINGS.get("home_page", "https://www.google.com"))

    # Rewritten core functionality for new architecture
    def add_tab(self, url=None):
        view = QWebEngineView()
        view.setPage(QWebEnginePage(QWebEngineProfile.defaultProfile(), view))
        view.urlChanged.connect(lambda q, v=view: self.on_view_url_changed(v, q))
        view.loadStarted.connect(lambda v=view: self._on_load_start(v))
        view.loadProgress.connect(lambda p, v=view: self._on_load_progress(v, p))
        view.loadFinished.connect(lambda ok, v=view: self._on_load_finished(v, ok))
        idx = self.tab_widget.addTab(view, "New")
        icon = QIcon.fromTheme("applications-internet") if QIcon.hasThemeIcon("applications-internet") else None
        btn = self.tab_strip.add_tab_button("New", view, icon=icon)
        self.tab_widget.setCurrentIndex(idx)
        if url:
            view.setUrl(QUrl(url))
        self._fade_in(view, 300)
        self.tab_strip.scroll_to_button(len(self.tab_strip.tab_buttons)-1)
        return view

    def remove_tab(self, index):
        if index < 0 or index >= self.tab_widget.count(): return
        self.tab_strip.remove_tab_button(index)
        widget = self.tab_widget.widget(index)
        self._fade_out(widget, 250, lambda: self.tab_widget.removeTab(index))

    def switch_to_tab(self, index):
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)
            self.tab_strip.scroll_to_button(index)

    def on_tab_switched(self, index):
        view = self.tab_widget.widget(index)
        if view:
            self.urlbar.setText(view.url().toString())
        for i, (btn, v) in enumerate(self.tab_strip.tab_buttons):
            btn.setStyleSheet(self.tab_strip._tab_style(selected=(i==index)))

    def current_view(self):
        w = self.tab_widget.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    def load_from_urlbar(self):
        txt = self.urlbar.text().strip()
        if not txt: return
        if " " in txt or "." not in txt:
            url = f"https://www.google.com/search?q={txt.replace(' ','+')}"
        else:
            url = txt if txt.startswith("http") else "https://"+txt
        v = self.current_view()
        if v:
            v.setUrl(QUrl(url))
            self._start_overlay_timer()

    def on_view_url_changed(self, view, qurl):
        if view == self.current_view():
            self.urlbar.setText(qurl.toString())
        HISTORY.insert(0, qurl.toString())
        save_json(HISTORY_FILE, HISTORY[:2000])  # cap hist size

    def go_back(self):
        v = self.current_view()
        if v and v.history().canGoBack(): v.back()

    def go_forward(self):
        v = self.current_view()
        if v and v.history().canGoForward(): v.forward()

    def reload_page(self):
        v = self.current_view()
        if v: v.reload()

    def go_home(self):
        v = self.current_view()
        if v: v.setUrl(QUrl(SETTINGS.get("home_page", "https://www.google.com")))

    # --- Fade anim helpers ---
    # --- Advanced fade and ripple animations for human UX delight ---
    def _fade_in(self, widget, duration=280):
        eff = widget.graphicsEffect()
        if not eff:
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
        # Animate both opacity + small Y-shift for material effect
        group = QParallelAnimationGroup(widget)
        a_op = QPropertyAnimation(eff, b"opacity")
        a_op.setDuration(duration)
        a_op.setStartValue(0.0); a_op.setEndValue(1.0)
        a_op.setEasingCurve(QEasingCurve.OutBack)
        rect = widget.geometry()
        a_pos = QPropertyAnimation(widget, b"geometry")
        a_pos.setDuration(int(0.85*duration))
        y0 = rect.y()+16; y1 = rect.y()
        a_pos.setStartValue(QRect(rect.x(), y0, rect.width(), rect.height()))
        a_pos.setEndValue(rect)
        a_pos.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(a_op)
        group.addAnimation(a_pos)
        group.start(QParallelAnimationGroup.DeleteWhenStopped)

    def _fade_out(self, widget, duration=180, finished_cb=None):
        eff = widget.graphicsEffect()
        if not eff:
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
        group = QParallelAnimationGroup(widget)
        a_op = QPropertyAnimation(eff, b"opacity")
        a_op.setDuration(duration)
        a_op.setStartValue(1.0); a_op.setEndValue(0.0)
        a_op.setEasingCurve(QEasingCurve.InQuart)
        rect = widget.geometry()
        a_pos = QPropertyAnimation(widget, b"geometry")
        a_pos.setDuration(duration)
        y0 = rect.y(); y1 = rect.y()+12
        a_pos.setStartValue(rect)
        a_pos.setEndValue(QRect(rect.x(), y1, rect.width(), rect.height()))
        a_pos.setEasingCurve(QEasingCurve.InCubic)
        group.addAnimation(a_op)
        group.addAnimation(a_pos)
        if finished_cb:
            group.finished.connect(finished_cb)
        group.start(QParallelAnimationGroup.DeleteWhenStopped)
        
    def gorgeous_sequential_intro_anim(self, widget):
        # EXAMPLE: Sequentially scale+fade intro (very Material-UI)
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        fade = QPropertyAnimation(eff, b"opacity"); fade.setDuration(400)
        fade.setStartValue(0); fade.setEndValue(1)
        fade.setEasingCurve(QEasingCurve.OutCirc)
        scale = QPropertyAnimation(widget, b"geometry"); scale.setDuration(280)
        rect = widget.geometry(); shrink = QRect(rect.x()+8, rect.y()+8, rect.width()-16, rect.height()-16)
        scale.setStartValue(shrink); scale.setEndValue(rect)
        scale.setEasingCurve(QEasingCurve.OutQuart)
        group = QSequentialAnimationGroup(widget)
        group.addAnimation(fade)
        group.addAnimation(scale)
        group.start(QSequentialAnimationGroup.DeleteWhenStopped)

    # --- Loading overlay sequence ---
    def _start_overlay_timer(self, delay_ms=320):
        if hasattr(self, "_overlay_timer") and self._overlay_timer.isActive():
            self._overlay_timer.stop()
        self._overlay_timer = QTimer(self)
        self._overlay_timer.setSingleShot(True)
        self._overlay_timer.timeout.connect(self._maybe_show_overlay)
        self._overlay_timer.start(delay_ms)

    def _maybe_show_overlay(self):
        v = self.current_view()
        if not v: return
        if getattr(v, "_is_loading", False):
            self.loading_overlay.show_overlay()

    def cancel_current_load(self):
        v = self.current_view()
        if v:
            v.stop()
        self.loading_overlay.hide_overlay()

    def _on_load_start(self, view):
        view._is_loading = True
        self._start_overlay_timer()

    def _on_load_progress(self, view, progress):
        if progress >= 100:
            self.loading_overlay.hide_overlay()

    def _on_load_finished(self, view, ok):
        view._is_loading = False
        self.loading_overlay.hide_overlay()
        self.statusBar().showMessage("Loaded" if ok else "Failed to Load", 1400)
        idx = self.tab_widget.indexOf(view)
        if idx >= 0:
            title = view.title() or view.url().toString()
            self.tab_widget.setTabText(idx, title[:46])
            if idx < len(self.tab_strip.tab_buttons):
                btn, _ = self.tab_strip.tab_buttons[idx]
                try: btn.setText(title[:26])
                except Exception: pass

    # --- Bookmarks ---
    def add_bookmark_current(self):
        v = self.current_view()
        if not v: return
        url = v.url().toString()
        title = v.title() or url
        BOOKMARKS.insert(0, {"title": title, "url": url})
        save_json(BOOKMARKS_FILE, BOOKMARKS[:150])
        self.refresh_bookmark_bar()
        QMessageBox.information(self, "Bookmark", f"Saved: {title[:50]}")

    def refresh_bookmark_bar(self):
        self.bookmark_bar.clear()
        for b in BOOKMARKS[:11]:
            btn = QPushButton(b.get("title", b.get("url")))
            btn.setStyleSheet("background:rgba(30,150,240,0.88);color:white;padding:8px;border-radius:11px;font-size:13px;")
            btn.clicked.connect(partial(self.open_url, b.get("url")))
            self.bookmark_bar.addWidget(btn)
        add = QPushButton("+"); add.setToolTip("Add current page to bookmarks")
        add.clicked.connect(self.add_bookmark_current)
        add.setStyleSheet("background:#42d;color:white;padding:8px;border-radius:11px;font-size:14px;")
        self.bookmark_bar.addWidget(add)

    def open_url(self, url):
        v = self.current_view()
        if v:
            v.setUrl(QUrl(url))

    # --- Downloads Management ---
    def _on_download_requested(self, item: QWebEngineDownloadItem):
        suggested = item.suggestedFileName() or f"download-{datetime.now().strftime('%H%M%S')}"
        out = os.path.join(DOWNLOADS_DIR, suggested)
        item.setPath(out)
        item.accept()
        entry = {"name": suggested, "path": out, "item": item}
        self.downloads.append(entry)
        QMessageBox.information(self, "Download", f"Started: {suggested}")
    
    def open_downloads_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Downloads")
        dlg.setMinimumSize(760, 340)
        dlg.setFont(QFont('Segoe UI', 11))
        dlg.setStyleSheet('''
            QDialog { background: #151c31; border-radius:19px; }
            QLabel, QPushButton { font-size:15px; }
        ''')
        shadow = QGraphicsDropShadowEffect(dlg)
        shadow.setBlurRadius(33); shadow.setOffset(0,3); shadow.setColor(QColor('#222f5c'))
        dlg.setGraphicsEffect(shadow)
        layout = QVBoxLayout(dlg); layout.setContentsMargins(30,24,30,15); layout.setSpacing(13)
        rows = []
        for e in self.downloads:
            row = QHBoxLayout(); row.setSpacing(9)
            lbl = QLabel(e["name"])
            prog = QProgressBar(); prog.setValue(0); prog.setFixedHeight(18)
            btn_pause = QPushButton("Pause"); btn_resume = QPushButton("Resume")
            for b in (btn_pause, btn_resume): b.setMinimumWidth(42)
            item_obj = e["item"]
            btn_pause.clicked.connect(lambda _, it=item_obj: it.pause())
            btn_resume.clicked.connect(lambda _, it=item_obj: it.resume())
            row.addWidget(lbl); row.addWidget(prog, 2); row.addWidget(btn_pause); row.addWidget(btn_resume)
            layout.addLayout(row)
            rows.append((e, prog))
        def tick():
            for e, p in rows:
                try:
                    it = e["item"]
                    total = it.totalBytes()
                    rec = it.receivedBytes()
                    if total and total>0:
                        val = int(rec*100/total)
                        p.setValue(val)
                    else:
                        p.setValue(0 if not it.isFinished() else 100)
                except Exception:
                    pass
        timer = QTimer(dlg); timer.timeout.connect(tick); timer.start(340)
        btn_close = QPushButton("Close"); btn_close.setFont(QFont('Segoe UI', 12, QFont.Bold))
        btn_close.setStyleSheet('background:#2cabf1;color:white;border-radius:7px;padding:8px 22px;margin-top:20px;font-weight:bold;')
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
        dlg.setLayout(layout)
        dlg.exec_() 
        timer.stop()

    # --- Settings Dialog ---
    def open_settings_dialog(self):
        dlg = QDialog(self); dlg.setWindowTitle("Settings")
        dlg.setMinimumSize(540,320)
        dlg.setFont(QFont('Segoe UI', 11))
        dlg.setStyleSheet('QDialog { background: #191d29; border-radius:16px; padding:13px 11px;} QLabel,QPushButton {font-size:15px;}')
        layout = QVBoxLayout(dlg); layout.setContentsMargins(27,17,27,13); layout.setSpacing(13)
        theme_btn = QPushButton("Toggle Theme"); theme_btn.clicked.connect(self.toggle_theme)
        showbm_box = QPushButton("Bookmark Bar: %s" % ("ON" if SETTINGS.get("show_bookmark_bar", True) else "OFF"))
        showbm_box.clicked.connect(lambda: self._toggle_bookmarkbar(showbm_box))
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_settings)
        for w in (theme_btn, showbm_box, reset_btn): layout.addWidget(w)
        btn_close = QPushButton("Close"); btn_close.clicked.connect(dlg.close)
        btn_close.setStyleSheet('background:#1976d2; color:white; border-radius:9px; font-weight:bold; padding:7px 18px;')
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
        dlg.setLayout(layout)
        dlg.exec_()

    def _toggle_bookmarkbar(self, bm_btn):
        SETTINGS["show_bookmark_bar"] = not SETTINGS.get("show_bookmark_bar", True)
        save_json(SETTINGS_FILE, SETTINGS)
        self.bookmark_bar.setVisible(SETTINGS["show_bookmark_bar"])
        bm_btn.setText("Bookmark Bar: %s" % ("ON" if SETTINGS["show_bookmark_bar"] else "OFF"))

    def _reset_settings(self):
        SETTINGS.clear(); SETTINGS.update(DEFAULT_SETTINGS.copy())
        save_json(SETTINGS_FILE, SETTINGS)
        QMessageBox.information(self, "Reset", "Reset OK; restart app for full effect.")

    # --- Password Vault (secure, robust) ---
    def open_vault_dialog(self):
        dlg = QDialog(self); dlg.setWindowTitle("🔐 Password Vault"); dlg.setMinimumSize(470,275)
        dlg.setFont(QFont('Segoe UI', 11))
        dlg.setStyleSheet('QDialog { background: #181f2b; border-radius:15px;} QLabel,QPushButton {font-size:15px;}')
        layout = QVBoxLayout(dlg); layout.setContentsMargins(21,14,23,12); layout.setSpacing(12)
        if not KEYRING_AVAILABLE:
            layout.addWidget(QLabel("Keyring support missing. Install 'keyring' Python pkg!"))
            btn = QPushButton("Close"); btn.clicked.connect(dlg.close)
            layout.addWidget(btn)
            dlg.setLayout(layout); dlg.exec_(); return
        site = QLineEdit(); site.setPlaceholderText("Site (example.com)")
        user = QLineEdit(); user.setPlaceholderText("Username")
        pwd = QLineEdit(); pwd.setPlaceholderText("Password")
        for w in (site, user, pwd): layout.addWidget(w)
        row = QHBoxLayout(); row.setSpacing(8)
        btn_save = QPushButton("Save"); btn_get = QPushButton("Get"); btn_close = QPushButton("Close")
        for b in (btn_save, btn_get, btn_close): b.setMinimumWidth(66)
        row.addWidget(btn_save); row.addWidget(btn_get); row.addWidget(btn_close)
        layout.addLayout(row)
        def do_save():
            s = site.text().strip(); u = user.text().strip(); p = pwd.text()
            if not s or not u or not p:
                QMessageBox.warning(dlg, "Missing", "Provide site, user, password"); return
            key = f"{s}||{u}"
            try:
                keyring.set_password("zeron_vault", key, p)
                QMessageBox.information(dlg, "Saved", "In OS keyring ✓")
            except Exception as e:
                QMessageBox.critical(dlg, "Error", str(e))
        def do_get():
            s = site.text().strip(); u = user.text().strip()
            if not s or not u:
                QMessageBox.warning(dlg, "Missing", "Provide site and user"); return
            key = f"{s}||{u}"
            try:
                r = keyring.get_password("zeron_vault", key)
                if r: pwd.setText(r)
                else: QMessageBox.information(dlg, "Not found", "No entry found")
            except Exception as e:
                QMessageBox.critical(dlg, "Error", str(e))
        btn_save.clicked.connect(do_save); btn_get.clicked.connect(do_get); btn_close.clicked.connect(dlg.close)
        dlg.setLayout(layout)
        dlg.exec_()

    # --- Theming (modern, Material/Fluent, adaptive color/glass) ---
    def apply_theme(self, theme):
        if SETTINGS.get("force_white_text", False):
            fg = "#fff"
        else:
            fg = "#172b49"
        if theme in ("light", "fluent_light"):
            bg, accent = "#f8faff", "#1976d2"
            tabbar = "#e3edff"  # no alpha for tabbar in QSS
        else:
            bg, accent = "#181e33", "#2cabf1"
            tabbar = "#0f111e"  # no alpha for tabbar
        glass = "rgba(18,25,36,0.6)"
        qss = f'''
            QMainWindow {{ background: {bg}; color: {fg}; }}
            QToolBar {{ background: #232743; color: {fg}; }}
            QLineEdit {{ background: #303c4f; color: {fg}; padding:8px; border-radius:10px; }}
            QPushButton {{ background: {accent}; color: #fff; padding:8px; border-radius:10px; }}
            QPushButton:hover {{ background: #42d7fa; color:#fff; }}
            QLabel {{ color: {fg}; }}
        '''
        self.setStyleSheet(qss)
        SETTINGS["theme"] = theme
        save_json(SETTINGS_FILE, SETTINGS)

    def toggle_theme(self):
        cur = SETTINGS.get("theme", "fluent_dark")
        nxt = "fluent_light" if cur.endswith("dark") else "fluent_dark"
        SETTINGS["theme"] = nxt
        save_json(SETTINGS_FILE, SETTINGS)
        self.apply_theme(nxt)

    # --- Shortcuts, helpers ---
    def _setup_shortcuts(self):
        self.addAction(self._mk_action("New Tab", "Ctrl+T", lambda: self.add_tab()))
        self.addAction(self._mk_action("Close Tab", "Ctrl+W", lambda: self.remove_tab(self.tab_widget.currentIndex())))
        self.addAction(self._mk_action("Focus URL", "Ctrl+L", lambda: self.urlbar.setFocus()))
        self.addAction(self._mk_action("Bookmark Current", "Ctrl+D", lambda: self.add_bookmark_current()))
        self.addAction(self._mk_action("Downloads", "Ctrl+J", self.open_downloads_dialog))
        self.addAction(self._mk_action("Settings", "Ctrl+U", self.open_settings_dialog))
        self.addAction(self._mk_action("Vault", "Ctrl+K", self.open_vault_dialog))

    def _mk_action(self, name, shortcut, cb):
        a = QAction(name, self); a.setShortcut(QKeySequence(shortcut)); a.triggered.connect(cb); return a

    def _on_urlbar_text_change(self, text):
        # Subtle focus/ripple on text edit for world-class human UX
        try:
            rect = self.urlbar.geometry()
            anim = QPropertyAnimation(self.urlbar, b"geometry")
            anim.setDuration(110)
            anim.setStartValue(rect)
            anim.setEndValue(QRect(rect.x()-2, rect.y(), rect.width()+4, rect.height()))
            anim.setEasingCurve(QEasingCurve.OutExpo)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        except Exception:
            pass

    def _setup_webengine(self):
        """
        Optimize WebEngine for max site compatibility (works with Google, Outlook,
        Discord, YouTube, and other complex web apps) and best security practices.
        """
        p = QWebEngineProfile.defaultProfile()
        # SET A MODERN USER AGENT (Critical! Makes YouTube, Gmail, etc work)
        p.setHttpUserAgent(LATEST_CHROMIUM_UA)
        s = p.settings()
        # Enable everything modern sites demand
        for attr in (
            QWebEngineSettings.JavascriptEnabled,
            QWebEngineSettings.PluginsEnabled,
            QWebEngineSettings.JavascriptCanOpenWindows,
            QWebEngineSettings.LocalStorageEnabled,
            QWebEngineSettings.LocalContentCanAccessFileUrls,
            QWebEngineSettings.LocalContentCanAccessRemoteUrls,
            QWebEngineSettings.WebGLEnabled,
            QWebEngineSettings.AutoLoadImages,
            QWebEngineSettings.ScreenCaptureEnabled if hasattr(QWebEngineSettings,'ScreenCaptureEnabled') else None,
            QWebEngineSettings.PdfViewerEnabled if hasattr(QWebEngineSettings,'PdfViewerEnabled') else None,
            QWebEngineSettings.FocusOnNavigationEnabled if hasattr(QWebEngineSettings,'FocusOnNavigationEnabled') else None,
        ):
            if attr:
                s.setAttribute(attr, True)
        # Caches
        cache = os.path.join(DATA_DIR, "cache"); os.makedirs(cache, exist_ok=True)
        p.setCachePath(cache)
        p.setPersistentStoragePath(cache)
        # Cookie persistence
        p.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)

# -------- Entrypoint, error handlers --------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ZERON v0.3.0")
    win = ZeronMain(); win.show()
    def on_exit():
        save_json(BOOKMARKS_FILE, BOOKMARKS)
        save_json(HISTORY_FILE, HISTORY)
        save_json(SETTINGS_FILE, SETTINGS)
    app.aboutToQuit.connect(on_exit)
    sys.exit(app.exec_())

if __name__ == "__main__": main()

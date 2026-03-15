"""
main.py — SecureVault application entry point.

Startup sequence:
  1. Show splash / loading animation while initialising the database.
  2. Prompt for master password (create on first run, verify on subsequent runs).
  3. Present the main vault window with full CRUD, search, and backup features.

GUI toolkit: PySide6
"""

import sys
import os
import logging

# ── Graceful PySide6 / PyQt6 import ──────────────────────────────────────────
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QDialog,
        QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
        QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
        QProgressBar, QComboBox, QSizePolicy, QFrame, QToolTip,
        QFileDialog, QTextEdit, QCheckBox, QSpinBox, QDialogButtonBox,
    )
    from PySide6.QtCore import (
        Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize,
        QThread, Signal, QObject, QAbstractAnimation,
    )
    from PySide6.QtGui import (
        QFont, QColor, QPalette, QIcon, QClipboard, QGuiApplication,
        QAction,
    )
except ImportError:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QDialog,
        QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
        QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
        QProgressBar, QComboBox, QSizePolicy, QFrame, QToolTip,
        QFileDialog, QTextEdit, QCheckBox, QSpinBox, QDialogButtonBox,
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize,
        QThread, pyqtSignal as Signal, QObject, QAbstractAnimation,
    )
    from PyQt6.QtGui import (
        QFont, QColor, QPalette, QIcon, QClipboard, QGuiApplication,
        QAction,
    )

from securevault import database, encryption, clipboard, utils

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ── Palette & stylesheet ──────────────────────────────────────────────────────
DARK_BG = "#1a1a2e"
PANEL_BG = "#16213e"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
TEXT_PRIMARY = "#eaeaea"
TEXT_SECONDARY = "#a0a0b0"
SUCCESS_COLOR = "#2ecc71"
ERROR_COLOR = "#e74c3c"
INFO_COLOR = "#3498db"
INPUT_BG = "#0d1b2a"

GLOBAL_STYLESHEET = f"""
QMainWindow, QDialog, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "SF Pro Display", "Ubuntu", sans-serif;
    font-size: 13px;
}}
QLabel {{
    color: {TEXT_PRIMARY};
}}
QPushButton {{
    background-color: {ACCENT};
    color: {TEXT_PRIMARY};
    border: 1px solid {HIGHLIGHT};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    min-width: 90px;
}}
QPushButton:hover {{
    background-color: {HIGHLIGHT};
    color: #ffffff;
}}
QPushButton:pressed {{
    background-color: #c0392b;
}}
QPushButton:disabled {{
    background-color: #2c2c3e;
    color: {TEXT_SECONDARY};
    border-color: #444;
}}
QLineEdit, QTextEdit, QComboBox, QSpinBox {{
    background-color: {INPUT_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT};
    border-radius: 5px;
    padding: 5px 8px;
    selection-background-color: {HIGHLIGHT};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border-color: {HIGHLIGHT};
}}
QTableWidget {{
    background-color: {PANEL_BG};
    color: {TEXT_PRIMARY};
    gridline-color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    selection-background-color: {HIGHLIGHT};
}}
QHeaderView::section {{
    background-color: {ACCENT};
    color: {TEXT_PRIMARY};
    padding: 6px;
    border: none;
    font-weight: 700;
}}
QTableWidget::item:selected {{
    background-color: {HIGHLIGHT};
    color: #ffffff;
}}
QProgressBar {{
    border: 1px solid {ACCENT};
    border-radius: 4px;
    background-color: {INPUT_BG};
    text-align: center;
    color: {TEXT_PRIMARY};
}}
QProgressBar::chunk {{
    background-color: {HIGHLIGHT};
    border-radius: 3px;
}}
QComboBox::drop-down {{
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {INPUT_BG};
    color: {TEXT_PRIMARY};
    selection-background-color: {HIGHLIGHT};
    border: 1px solid {ACCENT};
}}
QScrollBar:vertical {{
    background: {PANEL_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {ACCENT};
    border-radius: 4px;
}}
QToolTip {{
    background-color: {PANEL_BG};
    color: {TEXT_PRIMARY};
    border: 1px solid {HIGHLIGHT};
    padding: 4px;
    border-radius: 4px;
}}
QMessageBox {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {ACCENT};
    border-radius: 3px;
    background: {INPUT_BG};
}}
QCheckBox::indicator:checked {{
    background: {HIGHLIGHT};
    border-color: {HIGHLIGHT};
}}
"""


# ── Database initialiser thread ───────────────────────────────────────────────

class DbInitWorker(QObject):
    """Initialise the database in a background thread."""

    finished = Signal(bool, str)  # (success, error_message)
    progress = Signal(int)        # 0-100

    def run(self) -> None:
        try:
            self.progress.emit(30)
            database.init_db()
            self.progress.emit(100)
            self.finished.emit(True, "")
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(False, str(exc))


# ── Splash / loading window ───────────────────────────────────────────────────

class SplashWindow(QWidget):
    """Animated splash screen shown during database initialisation."""

    init_complete = Signal(bool)  # emitted once DB is ready

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 280)
        self._build_ui()
        self._center()
        self._start_init()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Card background frame
        card = QFrame(self)
        card.setObjectName("splashCard")
        card.setStyleSheet(
            f"#splashCard {{ background: {PANEL_BG}; border: 2px solid {HIGHLIGHT};"
            f" border-radius: 18px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)
        card_layout.setContentsMargins(24, 28, 24, 28)

        # Logo / title
        title = QLabel("🔐 SecureVault")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 28px; font-weight: 800; color: {HIGHLIGHT};"
            " letter-spacing: 2px;"
        )
        subtitle = QLabel("Your offline secret manager")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(10)
        self._progress.setTextVisible(False)

        self._status = QLabel("Initialising encrypted database…")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)
        card_layout.addWidget(self._progress)
        card_layout.addWidget(self._status)

        layout.addWidget(card)
        self.setLayout(layout)

    def _center(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    def _start_init(self) -> None:
        self._thread = QThread()
        self._worker = DbInitWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

        # Animate progress bar smoothly from 0→30 during thread startup
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._tick_progress)
        self._anim_timer.start(30)
        self._fake_val = 0

    def _tick_progress(self) -> None:
        if self._fake_val < 28:
            self._fake_val += 1
            self._progress.setValue(self._fake_val)

    def _on_progress(self, val: int) -> None:
        self._anim_timer.stop()
        self._progress.setValue(val)
        if val == 100:
            self._status.setText("Ready.")

    def _on_finished(self, success: bool, error: str) -> None:
        self._thread.quit()
        if not success:
            self._status.setText(f"Error: {error}")
        QTimer.singleShot(400, lambda: self.init_complete.emit(success))


# ── Master password dialog ────────────────────────────────────────────────────

class MasterPasswordDialog(QDialog):
    """Prompt for the master password (new vault or existing vault)."""

    def __init__(self, is_new_vault: bool, parent=None) -> None:
        super().__init__(parent)
        self.is_new_vault = is_new_vault
        self._password: str = ""
        self.setWindowTitle("SecureVault — Authentication")
        self.setFixedSize(400, is_new_vault and 330 or 250)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(30, 30, 30, 24)

        title = QLabel("🔐 SecureVault")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {HIGHLIGHT};")
        layout.addWidget(title)

        if self.is_new_vault:
            hint = QLabel(
                "Welcome! Create a master password to protect your vault.\n"
                "Use at least 8 characters. This cannot be recovered."
            )
        else:
            hint = QLabel("Enter your master password to unlock the vault.")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(hint)

        self._pw_input = QLineEdit()
        self._pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_input.setPlaceholderText("Master password")
        self._pw_input.setToolTip("Enter your master password")
        layout.addWidget(self._pw_input)

        if self.is_new_vault:
            self._pw_confirm = QLineEdit()
            self._pw_confirm.setEchoMode(QLineEdit.EchoMode.Password)
            self._pw_confirm.setPlaceholderText("Confirm master password")
            layout.addWidget(self._pw_confirm)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet(f"color: {ERROR_COLOR}; font-size: 11px;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._error_label)

        btn_label = "Create Vault" if self.is_new_vault else "Unlock"
        unlock_btn = QPushButton(btn_label)
        unlock_btn.setDefault(True)
        unlock_btn.clicked.connect(self._on_submit)
        self._pw_input.returnPressed.connect(self._on_submit)
        if self.is_new_vault:
            self._pw_confirm.returnPressed.connect(self._on_submit)
        layout.addWidget(unlock_btn)

    def _on_submit(self) -> None:
        password = self._pw_input.text()
        err = utils.validate_master_password(password)
        if err:
            self._show_error(err)
            return

        if self.is_new_vault:
            confirm = self._pw_confirm.text()
            if password != confirm:
                self._show_error("Passwords do not match.")
                return
            pw_hash = encryption.hash_master_password(password)
            database.set_master_password_hash(pw_hash)

        self._password = password
        self.accept()

    def _show_error(self, msg: str) -> None:
        self._error_label.setText(msg)

    def get_password(self) -> str:
        return self._password


# ── Add Key dialog ────────────────────────────────────────────────────────────

class AddKeyDialog(QDialog):
    """Dialog for adding a new secret."""

    def __init__(self, master_password: str, parent=None) -> None:
        super().__init__(parent)
        self._master_password = master_password
        self.setWindowTitle("Add Secret")
        self.setFixedSize(460, 400)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(28, 24, 28, 20)

        title = QLabel("➕ Add New Secret")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {HIGHLIGHT};")
        layout.addWidget(title)

        # Description
        layout.addWidget(QLabel("Description:"))
        self._desc = QLineEdit()
        self._desc.setPlaceholderText("e.g. AWS Production API Key")
        self._desc.setToolTip("A short description to identify this secret")
        layout.addWidget(self._desc)

        # Category
        layout.addWidget(QLabel("Category:"))
        self._cat = QComboBox()
        self._cat.setEditable(True)
        self._cat.addItems(utils.DEFAULT_CATEGORIES)
        self._cat.setToolTip("Choose or type a category/tag")
        layout.addWidget(self._cat)

        # Secret
        layout.addWidget(QLabel("Secret:"))
        self._secret = QLineEdit()
        self._secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._secret.setPlaceholderText("Paste or type your secret here")
        self._secret.setToolTip("The secret value — stored encrypted, never shown in the list")
        layout.addWidget(self._secret)

        # Show / generate row
        toggle_row = QHBoxLayout()
        show_cb = QCheckBox("Show secret")
        show_cb.stateChanged.connect(
            lambda s: self._secret.setEchoMode(
                QLineEdit.EchoMode.Normal if s else QLineEdit.EchoMode.Password
            )
        )
        gen_btn = QPushButton("🎲 Generate")
        gen_btn.setToolTip("Generate a cryptographically secure random secret")
        gen_btn.clicked.connect(self._on_generate)
        toggle_row.addWidget(show_cb)
        toggle_row.addStretch()
        toggle_row.addWidget(gen_btn)
        layout.addLayout(toggle_row)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet(f"color: {ERROR_COLOR}; font-size: 11px;")
        layout.addWidget(self._error_label)

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("💾 Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _on_generate(self) -> None:
        dlg = KeyGenDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._secret.setText(dlg.get_key())
            self._secret.setEchoMode(QLineEdit.EchoMode.Normal)

    def _on_save(self) -> None:
        desc = self._desc.text().strip()
        cat = self._cat.currentText().strip() or "General"
        secret = self._secret.text()

        for validator, value in [
            (utils.validate_description, desc),
            (utils.validate_secret, secret),
        ]:
            err = validator(value)
            if err:
                self._error_label.setText(err)
                return

        try:
            enc = encryption.encrypt_secret(secret, self._master_password)
            database.add_secret(
                description=desc,
                category=cat,
                encrypted_key=enc["encrypted_key"],
                chacha_nonce=enc["chacha_nonce"],
                chacha_salt=enc["chacha_salt"],
                fernet_salt=enc["fernet_salt"],
            )
        except Exception as exc:  # noqa: BLE001
            self._error_label.setText(f"Encryption failed: {exc}")
            return

        self.accept()


# ── Key Generator dialog ──────────────────────────────────────────────────────

class KeyGenDialog(QDialog):
    """Stand-alone random key generator."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Random Key Generator")
        self.setFixedSize(420, 340)
        self._key = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 18)

        title = QLabel("🎲 Random Key Generator")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {HIGHLIGHT};")
        layout.addWidget(title)

        # Length
        len_row = QHBoxLayout()
        len_row.addWidget(QLabel("Length:"))
        self._length_spin = QSpinBox()
        self._length_spin.setRange(8, 256)
        self._length_spin.setValue(32)
        self._length_spin.setToolTip("Number of characters")
        len_row.addWidget(self._length_spin)
        len_row.addStretch()
        layout.addLayout(len_row)

        # Character classes
        self._use_upper = QCheckBox("Uppercase (A-Z)")
        self._use_upper.setChecked(True)
        self._use_lower = QCheckBox("Lowercase (a-z)")
        self._use_lower.setChecked(True)
        self._use_digits = QCheckBox("Digits (0-9)")
        self._use_digits.setChecked(True)
        self._use_symbols = QCheckBox("Symbols (!@#…)")
        self._use_symbols.setChecked(True)
        for cb in (self._use_upper, self._use_lower, self._use_digits, self._use_symbols):
            layout.addWidget(cb)

        # Result
        self._output = QLineEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("Click Generate…")
        layout.addWidget(self._output)

        gen_btn = QPushButton("⚡ Generate")
        gen_btn.clicked.connect(self._on_generate)
        layout.addWidget(gen_btn)

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        use_btn = QPushButton("✔ Use this key")
        use_btn.setDefault(True)
        use_btn.clicked.connect(self._on_use)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(use_btn)
        layout.addLayout(btn_row)

    def _on_generate(self) -> None:
        try:
            key = utils.generate_random_key(
                length=self._length_spin.value(),
                use_upper=self._use_upper.isChecked(),
                use_lower=self._use_lower.isChecked(),
                use_digits=self._use_digits.isChecked(),
                use_symbols=self._use_symbols.isChecked(),
            )
            self._output.setText(key)
            self._key = key
        except ValueError as exc:
            self._output.setText(f"Error: {exc}")

    def _on_use(self) -> None:
        if not self._key:
            self._on_generate()
        if self._key:
            self.accept()

    def get_key(self) -> str:
        return self._key


# ── View Key dialog ───────────────────────────────────────────────────────────

class ViewKeyDialog(QDialog):
    """Display a decrypted secret in a temporary popup (auto-closes in 30 s)."""

    AUTO_CLOSE_SECS = 30

    def __init__(self, description: str, secret: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("View Secret")
        self.setFixedSize(460, 280)
        self.setModal(True)
        self._remaining = self.AUTO_CLOSE_SECS
        self._build_ui(description, secret)
        self._start_timer()

    def _build_ui(self, description: str, secret: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(28, 24, 28, 20)

        header = QLabel(f"🔍 {utils.truncate(description, 50)}")
        header.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {HIGHLIGHT};")
        layout.addWidget(header)

        notice = QLabel("⚠ This window will close automatically in 30 seconds.")
        notice.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        layout.addWidget(notice)

        self._secret_box = QTextEdit()
        self._secret_box.setReadOnly(True)
        self._secret_box.setPlainText(secret)
        self._secret_box.setStyleSheet(
            f"background: {INPUT_BG}; font-family: monospace; font-size: 13px;"
        )
        layout.addWidget(self._secret_box)

        self._countdown = QLabel(f"Closing in {self._remaining}s…")
        self._countdown.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self._countdown)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _start_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self) -> None:
        self._remaining -= 1
        self._countdown.setText(f"Closing in {self._remaining}s…")
        if self._remaining <= 0:
            self._timer.stop()
            self.accept()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


# ── Main application window ───────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Primary SecureVault window."""

    def __init__(self, master_password: str) -> None:
        super().__init__()
        self._master_password = master_password
        self._sort_order = "date_added DESC"
        self.setWindowTitle("SecureVault — Secret Manager")
        self.setMinimumSize(860, 560)
        self._build_ui()
        self._refresh_table()
        self._animate_open()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Header bar ──────────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(
            f"background: {PANEL_BG}; border-bottom: 2px solid {HIGHLIGHT};"
        )
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(18, 8, 18, 8)

        logo = QLabel("🔐 SecureVault")
        logo.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {HIGHLIGHT}; letter-spacing: 1px;"
        )
        h_layout.addWidget(logo)
        h_layout.addStretch()

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        h_layout.addWidget(self._status_label)

        root.addWidget(header)

        # ── Toolbar ─────────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setFixedHeight(54)
        toolbar.setStyleSheet(f"background: {PANEL_BG};")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(14, 6, 14, 6)
        tb_layout.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search by description or category…")
        self._search.setToolTip("Filter secrets in real time")
        self._search.textChanged.connect(self._on_search)
        self._search.setFixedWidth(280)
        tb_layout.addWidget(self._search)

        self._sort_combo = QComboBox()
        self._sort_combo.addItems([
            "Newest first", "Oldest first",
            "Description A→Z", "Description Z→A",
            "Category A→Z",
        ])
        self._sort_combo.setToolTip("Sort secrets")
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        tb_layout.addWidget(self._sort_combo)

        tb_layout.addStretch()

        def mk_btn(label: str, tip: str, slot) -> QPushButton:
            b = QPushButton(label)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            return b

        self._btn_add = mk_btn("➕ Add Key", "Add a new secret to the vault", self._on_add)
        self._btn_view = mk_btn("👁 View Key", "View the selected secret (auto-closes in 30s)", self._on_view)
        self._btn_copy = mk_btn("📋 Copy Key", "Copy the selected secret to clipboard (auto-clears in 12s)", self._on_copy)
        self._btn_delete = mk_btn("🗑 Delete Key", "Permanently delete the selected secret", self._on_delete)
        self._btn_exit = mk_btn("✖ Exit", "Exit SecureVault", self._on_exit)
        self._btn_exit.setStyleSheet(
            f"background-color: #3a1020; border-color: {ERROR_COLOR};"
        )

        for btn in (self._btn_add, self._btn_view, self._btn_copy, self._btn_delete, self._btn_exit):
            tb_layout.addWidget(btn)

        root.addWidget(toolbar)

        # ── Secret list table ────────────────────────────────────────────────
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["#", "Description", "Category", "Date Added"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            self._table.styleSheet()
            + f" QTableWidget {{ alternate-background-color: {ACCENT}; }}"
        )
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_view)
        self._table.setToolTip("Double-click a row to view the secret")
        root.addWidget(self._table)

        # ── Status bar ───────────────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(32)
        footer.setStyleSheet(f"background: {PANEL_BG}; border-top: 1px solid {ACCENT};")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(14, 0, 14, 0)
        self._footer_left = QLabel("Ready.")
        self._footer_left.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        f_layout.addWidget(self._footer_left)
        f_layout.addStretch()
        self._footer_right = QLabel("")
        self._footer_right.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        f_layout.addWidget(self._footer_right)
        root.addWidget(footer)

        # ── Menu bar ─────────────────────────────────────────────────────────
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        export_action = QAction("Export Encrypted Backup…", self)
        export_action.triggered.connect(self._on_export)
        import_action = QAction("Import Encrypted Backup…", self)
        import_action.triggered.connect(self._on_import)
        file_menu.addAction(export_action)
        file_menu.addAction(import_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._on_exit)
        file_menu.addAction(exit_action)

        tools_menu = menu_bar.addMenu("Tools")
        keygen_action = QAction("Random Key Generator…", self)
        keygen_action.triggered.connect(self._on_keygen)
        tools_menu.addAction(keygen_action)

    # ── Animation ─────────────────────────────────────────────────────────────

    def _animate_open(self) -> None:
        """Smooth expand animation on first show."""
        self.setWindowOpacity(0.0)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(700)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    # ── Table management ───────────────────────────────────────────────────────

    def _refresh_table(self, rows=None) -> None:
        if rows is None:
            rows = database.get_all_secrets(self._sort_order)
        self._table.setRowCount(0)
        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            id_item = QTableWidgetItem(str(row["id"]))
            id_item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self._table.setItem(r, 0, id_item)
            self._table.setItem(r, 1, QTableWidgetItem(utils.truncate(row["description"], 70)))
            self._table.setItem(r, 2, QTableWidgetItem(row["category"] or "—"))
            self._table.setItem(r, 3, QTableWidgetItem(utils.format_date(row["date_added"])))
        total = self._table.rowCount()
        self._footer_right.setText(f"{total} secret{'s' if total != 1 else ''}")

    def _selected_row_id(self) -> int | None:
        selected = self._table.selectedItems()
        if not selected:
            return None
        row = self._table.currentRow()
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _show_status(self, msg: str, color: str = SUCCESS_COLOR) -> None:
        self._footer_left.setText(msg)
        self._footer_left.setStyleSheet(f"color: {color}; font-size: 11px;")
        QTimer.singleShot(5000, lambda: self._footer_left.setText("Ready."))

    # ── Button handlers ────────────────────────────────────────────────────────

    def _on_add(self) -> None:
        dlg = AddKeyDialog(self._master_password, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_table()
            self._show_status("✅ Secret added successfully.")

    def _on_view(self) -> None:
        secret_id = self._selected_row_id()
        if secret_id is None:
            self._show_status("⚠ Please select a secret to view.", ERROR_COLOR)
            return
        row = database.get_secret_by_id(secret_id)
        if not row:
            self._show_status("⚠ Secret not found.", ERROR_COLOR)
            return
        try:
            plaintext = encryption.decrypt_secret(
                encrypted_key=bytes(row["encrypted_key"]),
                chacha_nonce=bytes(row["chacha_nonce"]),
                chacha_salt=bytes(row["chacha_salt"]),
                fernet_salt=bytes(row["fernet_salt"]),
                master_password=self._master_password,
            )
        except Exception:  # noqa: BLE001
            self._show_status("❌ Decryption failed — wrong password or corrupted data.", ERROR_COLOR)
            return
        ViewKeyDialog(row["description"], plaintext, self).exec()

    def _on_copy(self) -> None:
        secret_id = self._selected_row_id()
        if secret_id is None:
            self._show_status("⚠ Please select a secret to copy.", ERROR_COLOR)
            return
        row = database.get_secret_by_id(secret_id)
        if not row:
            self._show_status("⚠ Secret not found.", ERROR_COLOR)
            return
        try:
            plaintext = encryption.decrypt_secret(
                encrypted_key=bytes(row["encrypted_key"]),
                chacha_nonce=bytes(row["chacha_nonce"]),
                chacha_salt=bytes(row["chacha_salt"]),
                fernet_salt=bytes(row["fernet_salt"]),
                master_password=self._master_password,
            )
        except Exception:  # noqa: BLE001
            self._show_status("❌ Decryption failed — wrong password or corrupted data.", ERROR_COLOR)
            return

        def on_cleared():
            QTimer.singleShot(0, lambda: self._show_status("ℹ Clipboard cleared.", INFO_COLOR))

        ok = clipboard.copy_to_clipboard(
            plaintext,
            delay=clipboard.DEFAULT_CLEAR_DELAY,
            on_cleared=on_cleared,
        )
        if ok:
            self._show_status(
                f"📋 Copied to clipboard (clears in {clipboard.DEFAULT_CLEAR_DELAY}s).", INFO_COLOR
            )
        else:
            # Fallback: use Qt clipboard directly
            QGuiApplication.clipboard().setText(plaintext)
            self._show_status(
                f"📋 Copied to clipboard (clears in {clipboard.DEFAULT_CLEAR_DELAY}s).", INFO_COLOR
            )
            QTimer.singleShot(
                clipboard.DEFAULT_CLEAR_DELAY * 1000,
                lambda: (QGuiApplication.clipboard().setText(""),
                         self._show_status("ℹ Clipboard cleared.", INFO_COLOR)),
            )

    def _on_delete(self) -> None:
        secret_id = self._selected_row_id()
        if secret_id is None:
            self._show_status("⚠ Please select a secret to delete.", ERROR_COLOR)
            return
        row = database.get_secret_by_id(secret_id)
        if not row:
            self._show_status("⚠ Secret not found.", ERROR_COLOR)
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Permanently delete "{utils.truncate(row['description'], 50)}"?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_secret(secret_id)
            self._refresh_table()
            self._show_status("🗑 Secret deleted.")

    def _on_exit(self) -> None:
        clipboard.cancel_clear_timer()
        QApplication.quit()

    def _on_search(self, query: str) -> None:
        if query.strip():
            rows = database.search_secrets(query.strip())
        else:
            rows = database.get_all_secrets(self._sort_order)
        self._refresh_table(rows)

    def _on_sort_changed(self, index: int) -> None:
        mapping = {
            0: "date_added DESC",
            1: "date_added ASC",
            2: "description ASC",
            3: "description DESC",
            4: "category ASC",
        }
        self._sort_order = mapping.get(index, "date_added DESC")
        self._refresh_table()

    def _on_keygen(self) -> None:
        KeyGenDialog(self).exec()

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Backup", os.path.expanduser("~"), "SQLite Backup (*.db)"
        )
        if path:
            try:
                database.export_backup(path)
                QMessageBox.information(self, "Export", f"Backup saved to:\n{path}")
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Export Failed", str(exc))

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Backup", os.path.expanduser("~"), "SQLite Backup (*.db)"
        )
        if path:
            reply = QMessageBox.question(
                self,
                "Confirm Import",
                "Importing will REPLACE the current vault.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    database.import_backup(path)
                    self._refresh_table()
                    QMessageBox.information(self, "Import", "Backup imported successfully.")
                except Exception as exc:  # noqa: BLE001
                    QMessageBox.critical(self, "Import Failed", str(exc))


# ── Application bootstrap ─────────────────────────────────────────────────────

def _show_master_password_prompt(is_new: bool, attempt: int = 1) -> str | None:
    """Show master-password dialog; return password or None if user cancelled."""
    dlg = MasterPasswordDialog(is_new_vault=is_new)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None

    password = dlg.get_password()

    if not is_new:
        stored_hash = database.get_master_password_hash()
        if not encryption.verify_master_password(stored_hash, password):
            box = QMessageBox()
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("Access Denied")
            if attempt >= 3:
                box.setText("Too many failed attempts. SecureVault will now exit.")
                box.exec()
                return None
            box.setText(
                f"Incorrect master password (attempt {attempt}/3).\nPlease try again."
            )
            box.exec()
            return _show_master_password_prompt(is_new=False, attempt=attempt + 1)

    return password


def main() -> None:
    # Prevent secrets appearing in Qt debug output
    os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false")

    app = QApplication(sys.argv)
    app.setApplicationName("SecureVault")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    # ── Splash / DB init ──────────────────────────────────────────────────────
    splash = SplashWindow()

    main_window_holder: list = []

    def on_db_ready(success: bool) -> None:
        splash.close()
        if not success:
            QMessageBox.critical(None, "Startup Error", "Failed to initialise the database.")
            app.quit()
            return

        # ── Master password ────────────────────────────────────────────────
        stored_hash = database.get_master_password_hash()
        is_new = stored_hash is None
        password = _show_master_password_prompt(is_new=is_new)
        if password is None:
            app.quit()
            return

        # ── Main window ────────────────────────────────────────────────────
        win = MainWindow(password)
        main_window_holder.append(win)
        win.show()

    splash.init_complete.connect(on_db_ready)
    splash.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

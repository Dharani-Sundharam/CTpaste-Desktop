"""
AutoTyper Desktop Application
Modern UI with PyQt6
"""

import sys
import os
import threading

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QProgressBar, QRadioButton, QButtonGroup,
    QLineEdit, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, pyqtSlot
from PyQt6.QtGui import QFont

import pyperclip
import keyboard

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.typing_engine import typing_engine
from core.clipboard_sync_service import clipboard_sync
from core.auth_service import auth_service, PLAN_CONFIG


# Theme matching Android app
DARK_STYLE = """
QWidget {
    background-color: #0f0f1a;
    color: #eaeaea;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QMainWindow { background-color: #0f0f1a; }
QLabel { background: transparent; color: #eaeaea; }

QPushButton {
    background-color: #8b5cf6;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 11px;
    font-weight: bold;
    color: white;
}
QPushButton:hover { background-color: #a78bfa; }
QPushButton:pressed { background-color: #7c3aed; }
QPushButton:disabled { background-color: #2d2d44; color: #6a6a8a; }

QPushButton#primaryBtn {
    background-color: #8b5cf6;
    border: none;
    color: white;
}
QPushButton#primaryBtn:hover { background-color: #a78bfa; }
QPushButton#primaryBtn:pressed { background-color: #7c3aed; }
QPushButton#primaryBtn:disabled { background-color: #2d2d44; color: #6a6a8a; }

QPushButton#stopBtn {
    background-color: transparent;
    border: 2px solid #8b5cf6;
    color: #8b5cf6;
}
QPushButton#stopBtn:hover { background-color: #8b5cf6; color: white; }
QPushButton#stopBtn:disabled { border-color: #2d2d44; color: #4a4a6a; }

QFrame#card {
    background-color: #1a1a2e;
    border-radius: 15px;
    border: 1px solid #2d2d44;
}

QProgressBar {
    background-color: #2d2d44;
    border-radius: 5px;
    border: none;
    height: 8px;
}
QProgressBar::chunk {
    background-color: #8b5cf6;
    border-radius: 5px;
}
"""



class SignalEmitter(QObject):
    """Helper class for thread-safe signal emission"""
    update_signal = pyqtSignal(str, str)  # status, color
    progress_signal = pyqtSignal(int)
    complete_signal = pyqtSignal(int)
    sync_status_signal = pyqtSignal(str, bool)  # status message, is_connected
    sync_update_signal = pyqtSignal(str)  # sync event message
    addons_changed_signal = pyqtSignal(dict) # new addons dict


class LoginWindow(QDialog):
    """Login dialog shown on startup — premium redesign."""

    LOGIN_STYLE = """
    QDialog {
        background-color: #0d0f1a;
    }
    QLabel#appTitle {
        color: #9c8fff;
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    QLabel#appSub {
        color: #5a6080;
        font-size: 12px;
    }
    QLabel#fieldLabel {
        color: #6b7ab0;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }
    QLineEdit {
        background: #161929;
        border: 1px solid #252840;
        border-radius: 10px;
        padding: 12px 16px;
        color: #e8eaf6;
        font-size: 13px;
        selection-background-color: #5b4fe0;
    }
    QLineEdit:focus {
        border-color: #7c6ef7;
        background: #1a1d30;
    }
    QLineEdit::placeholder {
        color: #383d60;
    }
    QPushButton#loginBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5b4fe0, stop:1 #7c6ef7);
        color: white;
        border: none;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 700;
        padding: 13px 0;
    }
    QPushButton#loginBtn:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6a5ef0, stop:1 #9c8fff);
    }
    QPushButton#loginBtn:pressed { background: #4a3ec8; }
    QPushButton#loginBtn:disabled {
        background: #252840;
        color: #4a5070;
    }
    QLabel#statusLbl {
        font-size: 11px;
        padding: 10px 14px;
        border-radius: 8px;
    }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CTpaste")
        self.setFixedSize(400, 430)
        self.setStyleSheet(self.LOGIN_STYLE)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._checking = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(0)

        # ── Logo mark row ──────────────────────────────────────
        from PyQt6.QtWidgets import QHBoxLayout
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)

        logo_box = QLabel("⌨")
        logo_box.setFixedSize(40, 40)
        logo_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_box.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #5b4fe0,stop:1 #ff6b81);
            border-radius: 10px;
            font-size: 18px;
        """)
        logo_row.addWidget(logo_box)
        logo_row.addStretch()
        layout.addLayout(logo_row)
        layout.addSpacing(22)

        # ── Title ───────────────────────────────────────────────
        title = QLabel("CTpaste")
        title.setObjectName("appTitle")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        layout.addSpacing(4)

        sub = QLabel("Sign in with your roll number")
        sub.setObjectName("appSub")
        sub.setFont(QFont("Segoe UI", 10))
        layout.addWidget(sub)
        layout.addSpacing(6)

        # ── Status label ────────────────────────────────────────
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("statusLbl")
        self.status_lbl.setFont(QFont("Segoe UI", 9))
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setVisible(False)
        layout.addWidget(self.status_lbl)
        layout.addSpacing(18)

        # ── Roll number ─────────────────────────────────────────
        roll_lbl = QLabel("ROLL NUMBER")
        roll_lbl.setObjectName("fieldLabel")
        roll_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(roll_lbl)
        layout.addSpacing(7)

        self.roll_input = QLineEdit()
        self.roll_input.setPlaceholderText("e.g. 111524104001")
        self.roll_input.setFont(QFont("Segoe UI", 12))
        self.roll_input.setFixedHeight(46)
        layout.addWidget(self.roll_input)
        layout.addSpacing(16)

        # ── Password ────────────────────────────────────────────
        pass_lbl = QLabel("PASSWORD")
        pass_lbl.setObjectName("fieldLabel")
        pass_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(pass_lbl)
        layout.addSpacing(7)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Enter your password")
        self.pass_input.setFont(QFont("Segoe UI", 12))
        self.pass_input.setFixedHeight(46)
        self.pass_input.returnPressed.connect(self._do_login)
        layout.addWidget(self.pass_input)
        layout.addSpacing(22)

        # ── Login button ────────────────────────────────────────
        self.login_btn = QPushButton("Sign In →")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.login_btn.setFixedHeight(48)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self._do_login)
        layout.addWidget(self.login_btn)
        layout.addStretch()

    def _set_status(self, msg: str, kind: str = "error"):
        colour = {"error": "#ff6b81", "success": "#43e97b", "info": "#9c8fff"}.get(kind, "#ff6b81")
        bg     = {"error": "rgba(255,107,129,.1)", "success": "rgba(67,233,123,.1)",
                  "info":  "rgba(124,110,247,.1)"}.get(kind, "rgba(255,107,129,.1)")
        border = {"error": "rgba(255,107,129,.25)", "success": "rgba(67,233,123,.25)",
                  "info":  "rgba(124,110,247,.25)"}.get(kind, "rgba(255,107,129,.25)")
        self.status_lbl.setStyleSheet(
            f"color:{colour}; background:{bg}; border:1px solid {border}; "
            f"border-radius:8px; padding:10px 14px; font-size:11px;"
        )
        self.status_lbl.setText(msg)
        self.status_lbl.setVisible(bool(msg))

    def _do_login(self):
        if self._checking:
            return
        roll = self.roll_input.text().strip()
        password = self.pass_input.text()

        if not roll or not password:
            self._set_status("Please enter both your roll number and password.")
            return

        self.login_btn.setText("Signing in…")
        self.login_btn.setEnabled(False)
        self._set_status("")
        self._checking = True

        import threading
        def _attempt():
            ok, msg = auth_service.login(roll, password)
            from PyQt6.QtCore import QMetaObject, Q_ARG
            QMetaObject.invokeMethod(self, "_login_result",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(bool, ok), Q_ARG(str, msg))

        threading.Thread(target=_attempt, daemon=True).start()

    @pyqtSlot(bool, str)
    def _login_result(self, ok: bool, msg: str):
        self._checking = False
        self.login_btn.setText("Sign In →")
        self.login_btn.setEnabled(True)
        if ok:
            self.accept()
        elif msg == "__SUSPENDED__":
            self._set_status(
                "⛔  Account Suspended — your account has been suspended by the admin. "
                "Please contact your administrator.",
                "error"
            )
        else:
            self._set_status(msg, "error")




class MainWindow(QMainWindow):
    """Main Dashboard Window"""
    
    def __init__(self):
        super().__init__()
        self.signals = SignalEmitter()
        self.signals.update_signal.connect(self.update_status)
        self.signals.progress_signal.connect(self.update_progress)
        self.signals.complete_signal.connect(self.typing_complete)
        self.signals.sync_status_signal.connect(self.update_sync_status)
        self.signals.sync_update_signal.connect(self.update_sync_event)
        self.signals.addons_changed_signal.connect(self._handle_addons_changed)

        self.setWindowTitle("CTpaste")
        self.setFixedSize(480, 620)
        self.setStyleSheet(DARK_STYLE)
        
        self.hotkey = "alt+v"
        self.hotkey_registered = False
        
        # Initialize UI and start session enforcement
        self.setup_ui()
        
        # Session timer mechanism
        from PyQt6.QtCore import QTimer
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(self._tick_session)
        self._session_remaining = 0
        self._session_is_cooldown = False
        self._current_extra_hours = 0
        self._current_super_pass = False
        
        self._init_session()
        
        # Hook up raw auth service listener to Emit the Qt Signal
        auth_service.on_addons_changed = self.signals.addons_changed_signal.emit
        
        # Check if plan was recently activated by admin
        user = auth_service.current_user
        if user and user.get("plan_activated_by") == "admin":
            # Show notification then clear the flag so it only shows once
            import threading
            def _clear_flag():
                t = user.get("plan_activated_at", 0)
                from core.auth_service import fb_update
                fb_update(f"users/{user.get('roll_number')}", {
                    "plan_activated_by": None
                })
            threading.Thread(target=_clear_flag, daemon=True).start()
            
            # Show a success message in the sync event label
            plan_name = user.get("plan", "Unknown")
            self.sync_event_label.setText(f"🎉 Your {plan_name} plan has been activated!")
            self.sync_event_label.setStyleSheet("color: #00ffaa; font-weight: bold; font-size: 13px;")
        
    def _init_session(self):
        """Enforce plan speed, load persistent timer from QSettings, and start the local session timer."""
        user = auth_service.current_user
        if not user:
            return

        # Enforce strict plan speed locking
        speed = auth_service.get_plan_speed_mode()  # 0=Fast, 1=Medium, 2=Slow
        typing_engine.set_mode(speed)
        for btn_id in range(3):
            rb = self.mode_group.button(btn_id)
            if rb:
                rb.setChecked(btn_id == speed)
                # Radio buttons are completely disabled and dictated by the app
                rb.setEnabled(False) 

        # Load session state from QSettings
        from PyQt6.QtCore import QSettings
        settings = QSettings("CTpaste", "DesktopApp")
        
        # Track initial add-on state so we can detect delta later
        addons = user.get("active_addons", {})
        self._current_extra_hours = addons.get("extra_hours_added", 0)
        self._current_super_pass = addons.get("super_pass", False)
        
        cfg = user.get("config", PLAN_CONFIG["GO"])
        
        # Keys unique to this user roll number
        roll = user.get("roll_number")
        rem_key      = f"session_rem_{roll}"
        cd_end_key   = f"cooldown_end_{roll}"
        addon_hrs_key = f"session_addon_hrs_{roll}"   # hours already baked into stored time

        import time
        now_ts = int(time.time())
        cooldown_end = settings.value(cd_end_key, type=int, defaultValue=0)

        if cooldown_end > now_ts:
            # Active cooldown persisting from last run
            self._session_remaining = cooldown_end - now_ts
            self._session_is_cooldown = True
            self.stop_service()
            self.start_btn.setEnabled(False)
        else:
            stored_rem      = settings.value(rem_key,       type=int, defaultValue=-1)
            baked_addon_hrs = settings.value(addon_hrs_key, type=int, defaultValue=0)

            extra_hrs   = addons.get("extra_hours_added", 0) or 0
            is_super    = bool(addons.get("super_pass"))

            if stored_rem > 0:
                # Resume previous session — but also apply any NEW add-on hours not yet baked in
                self._session_remaining = stored_rem
                new_addon_hrs = extra_hrs - baked_addon_hrs
                if new_addon_hrs > 0:
                    print(f"[Session] Applying {new_addon_hrs} new add-on hour(s) to stored session")
                    self._session_remaining += new_addon_hrs * 3600
            else:
                # Brand-new session — apply full add-on stack
                if is_super:
                    self._session_remaining = 3 * 3600
                else:
                    self._session_remaining = (1 + extra_hrs) * 3600

            # Always save how many addon hours are now baked in
            settings.setValue(addon_hrs_key, extra_hrs)
            self._session_is_cooldown = False

            # Clear expired cooldown timestamp
            if cooldown_end > 0:
                settings.remove(cd_end_key)

        self._session_timer.start(1000)
        self._update_session_ui()

    def _tick_session(self):
        """Called every second by QTimer."""
        if self._session_remaining > 0:
            self._session_remaining -= 1
            self._update_session_ui()
        else:
            self._session_timer.stop()
            if not self._session_is_cooldown:
                # Session just expired — start 2-hour cooldown and clear add-ons
                self._session_remaining = 2 * 3600  # 2hr cooldown
                self._session_is_cooldown = True
                self._session_timer.start(1000)
                self.stop_service()
                self.start_btn.setEnabled(False)
                self.update_status("Session expired — cooldown active", "#d29922")
                self._save_session_state()
                # Wipe add-ons from Firebase so next session starts clean
                if auth_service.current_user:
                    import threading
                    roll = auth_service.current_user["roll_number"]
                    def _clear_addons():
                        from desktop_app.core.auth_service import _db_patch
                        _db_patch(f"users/{roll}/active_addons",
                                  {"speed_boost": False, "extra_hours_added": 0, "super_pass": False})
                    threading.Thread(target=_clear_addons, daemon=True).start()
                    auth_service.current_user["active_addons"] = {}
                    self._current_extra_hours = 0
                    self._current_super_pass = False
            else:
                # Cooldown done — reset to fresh GO session
                self._session_is_cooldown = False
                self._session_remaining = 1 * 3600  # 1-hour base
                self.start_btn.setEnabled(True)
                self._update_session_ui()
                self.update_status("Session ready", "#58a6ff")
                self._session_timer.start(1000)
                self._save_session_state()

    def _handle_addons_changed(self, new_addons: dict):
        """Called dynamically live when admin approves a payment mid-session."""
        # 1. Check for newly added hours
        new_hours = new_addons.get("extra_hours_added", 0)
        if new_hours > self._current_extra_hours:
            diff = new_hours - self._current_extra_hours
            if not self._session_is_cooldown:
                # Add straight to the active timer
                self._session_remaining += diff * 3600
                self._current_extra_hours = new_hours
                
                # Show success pip
                self.sync_event_label.setText(f"🎉 +{diff} Hour(s) Added to your session!")
                self.sync_event_label.setStyleSheet("color: #00ffaa; font-weight: bold; font-size: 13px;")

        # 2. Check for fresh SUPER pass
        new_super = new_addons.get("super_pass", False)
        if new_super and not self._current_super_pass:
            if not self._session_is_cooldown:
                self._session_remaining = 3 * 3600 # Super grants outright 3 hours
                self._current_super_pass = True
                self.sync_event_label.setText("🎉 Upgraded to SUPER PASS!")
                self.sync_event_label.setStyleSheet("color: #00ffaa; font-weight: bold; font-size: 13px;")
                
        # 3. Re-evaluate strict Speed Locks
        speed = auth_service.get_plan_speed_mode()
        typing_engine.set_mode(speed)
        for btn_id in range(3):
            rb = self.mode_group.button(btn_id)
            if rb:
                rb.setChecked(btn_id == speed)
                
        # 4. Update the visual UI Plan Badge
        if hasattr(self, 'plan_lbl'):
            self.plan_lbl.setText(f"Current Plan: {auth_service.get_plan_name()}")

        self._update_session_ui()
        self._save_session_state()

    def _update_session_ui(self):
        h = self._session_remaining // 3600
        m = (self._session_remaining % 3600) // 60
        s = self._session_remaining % 60
        label = f"{h:02d}:{m:02d}:{s:02d}"
        if self._session_is_cooldown:
            color = "#d29922"  # amber
            prefix = "Cooldown"
        elif self._session_remaining <= 300:  # under 5 mins
            color = "#f85149"  # red warning
            prefix = "Session"
        else:
            color = "#3fb950"  # green
            prefix = "Session"
        if hasattr(self, "session_timer_lbl"):
            self.session_timer_lbl.setText(f"{prefix}: {label}")
            self.session_timer_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")


    
    def _save_session_state(self):
        """Save the current session/cooldown state to QSettings when app closes or changes state."""
        user = auth_service.current_user
        if not user:
            return
            
        from PyQt6.QtCore import QSettings
        import time
        settings = QSettings("CTpaste", "DesktopApp")
        roll = user.get("roll_number")
        
        if self._session_is_cooldown:
            # Save the timestamp when the cooldown will finish so it tracks while app is closed
            now_ts = int(time.time())
            settings.setValue(f"cooldown_end_{roll}", now_ts + self._session_remaining)
            settings.setValue(f"session_rem_{roll}", 0)
        else:
            # We are inside an active session. Just save the remaining time so they don't lose it if they close the app.
            settings.setValue(f"session_rem_{roll}", self._session_remaining)
            settings.remove(f"cooldown_end_{roll}")

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── Header ──────────────────────────────────────────────
        title = QLabel("CTpaste")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #eaeaea; letter-spacing: 1px;")
        subtitle = QLabel("Stealth typing engine")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #b0b0b0; margin-bottom: 4px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # User info and session timer
        user_info_layout = QHBoxLayout()
        roll = auth_service.current_user['roll_number']
        plan = auth_service.current_user.get('plan', 'GO')
        
        user_info_vbox = QVBoxLayout()
        self.user_lbl = QLabel(f"👤 {roll}")
        self.user_lbl.setFont(QFont("Segoe UI", 9))
        self.user_lbl.setStyleSheet("color: #8b949e;")
        
        self.plan_lbl = QLabel(f"Current Plan: {auth_service.get_plan_name()}")
        self.plan_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.plan_lbl.setStyleSheet("color: #58a6ff;")
        
        user_info_vbox.addWidget(self.user_lbl)
        user_info_vbox.addWidget(self.plan_lbl)
        
        user_info_layout.addLayout(user_info_vbox)
        user_info_layout.addStretch()

        self.session_timer_lbl = QLabel("Session: --:--:--")
        self.session_timer_lbl.setFont(QFont("Segoe UI", 9))
        self.session_timer_lbl.setStyleSheet("color: #8b949e;")
        user_info_layout.addWidget(self.session_timer_lbl)
        layout.addLayout(user_info_layout)

        # ── How to Use card ─────────────────────────────────────
        instr_card = QFrame()
        instr_card.setObjectName("card")
        instr_layout = QVBoxLayout(instr_card)
        instr_layout.setContentsMargins(16, 14, 16, 14)
        instr_layout.setSpacing(6)

        instr_title = QLabel("How to Use")
        instr_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        instr_title.setStyleSheet("color: #b0b0b0;")
        instr_layout.addWidget(instr_title)

        steps = [
            "1.  Start the service",
            "2.  Minimise this window",
            "3.  Copy your code  (Ctrl+C)",
            "4.  Press  Alt+V  to paste",
        ]
        for step in steps:
            lbl = QLabel(step)
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet("color: #8a8a9a;")
            instr_layout.addWidget(lbl)

        layout.addWidget(instr_card)

        # ── Phone Sync card ──────────────────────────────────────
        sync_card = QFrame()
        sync_card.setObjectName("card")
        sync_layout = QVBoxLayout(sync_card)
        sync_layout.setContentsMargins(16, 14, 16, 14)
        sync_layout.setSpacing(8)

        sync_title = QLabel("Phone Sync")
        sync_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        sync_title.setStyleSheet("color: #b0b0b0;")
        sync_layout.addWidget(sync_title)

        code_row = QHBoxLayout()
        self.pairing_code_label = QLabel("Auto-syncing to your account")
        self.pairing_code_label.setFont(QFont("Segoe UI", 10))
        self.pairing_code_label.setStyleSheet("color: #8b949e;")
        code_row.addWidget(self.pairing_code_label)
        code_row.addStretch()
        self.sync_status_dot = QLabel("●")
        self.sync_status_dot.setFont(QFont("Segoe UI", 12))
        self.sync_status_dot.setStyleSheet("color: #ff6b6b;")
        code_row.addWidget(self.sync_status_dot)
        sync_layout.addLayout(code_row)

        self.sync_event_label = QLabel("")
        self.sync_event_label.setFont(QFont("Segoe UI", 8))
        self.sync_event_label.setStyleSheet("color: #6a6a8a;")
        sync_layout.addWidget(self.sync_event_label)

        self.sync_btn = QPushButton("Toggle Sync")
        self.sync_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.sync_btn.setMinimumHeight(32)
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.clicked.connect(self.toggle_phone_sync)
        sync_layout.addWidget(self.sync_btn)

        layout.addWidget(sync_card)

        # ── Status card ───────────────────────────────────────────
        status_card = QFrame()
        status_card.setObjectName("card")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(16, 14, 16, 14)
        status_layout.setSpacing(8)

        self.status_label = QLabel("Stopped")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #8a8a9a;")
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(6)
        status_layout.addWidget(self.progress_bar)

        # Speed selector
        status_layout.addSpacing(6)
        speed_row = QHBoxLayout()
        speed_lbl = QLabel("Speed")
        speed_lbl.setFont(QFont("Segoe UI", 9))
        speed_lbl.setStyleSheet("color: #8a8a9a;")
        speed_row.addWidget(speed_lbl)
        speed_row.addSpacing(10)

        self.mode_group = QButtonGroup(self)

        def make_radio(label, color, btn_id, checked=False):
            rb = QRadioButton(label)
            rb.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            rb.setStyleSheet(f"""
                QRadioButton {{ color: {color}; spacing: 5px; }}
                QRadioButton::indicator {{ width: 12px; height: 12px; }}
                QRadioButton::indicator:checked {{
                    background: {color}; border-radius: 6px;
                    border: 2px solid {color};
                }}
                QRadioButton::indicator:unchecked {{
                    background: #2d2d44; border-radius: 6px;
                    border: 2px solid #3d3d5c;
                }}
            """)
            rb.setChecked(checked)
            self.mode_group.addButton(rb, btn_id)
            return rb

        self.fast_radio   = make_radio("Fast",   "#51cf66", 0, checked=True)
        self.medium_radio = make_radio("Medium", "#fcc419", 1)
        self.slow_radio   = make_radio("Slow",   "#a78bfa", 2)

        for rb in (self.fast_radio, self.medium_radio, self.slow_radio):
            speed_row.addWidget(rb)
            speed_row.addSpacing(8)
        speed_row.addStretch()
        status_layout.addLayout(speed_row)
        self.mode_group.idClicked.connect(self.on_mode_change)

        layout.addWidget(status_card)

        # ── Start / Stop buttons ──────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.start_btn = QPushButton("Start")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_service)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_service)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()


    def start_service(self):
        """Start the hotkey listener service"""
        self.register_hotkey()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.update_status("Running  —  Alt+V to paste", "#51cf66")
    
    def stop_service(self):
        """Stop the hotkey listener and any active typing"""
        # If typing is in progress, stop it immediately
        if typing_engine.is_typing:
            typing_engine.stop()
        self.unregister_hotkey()
        self.hotkey_registered = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.update_status("Stopped", "#8a8a9a")
    
    def register_hotkey(self):
        try:
            keyboard.add_hotkey(self.hotkey, self.trigger_typing)
            self.hotkey_registered = True
        except Exception as e:
            print(f"Failed to register hotkey: {e}")
    
    def unregister_hotkey(self):
        if self.hotkey_registered:
            try:
                keyboard.remove_hotkey(self.hotkey)
            except:
                pass
    
    def setup_typing_callbacks(self):
        def on_progress(current, total):
            progress = int((current / total) * 100)
            self.signals.progress_signal.emit(progress)
            self.signals.update_signal.emit(f"Typing... {current}/{total}", "#fcc419")
        
        def on_complete(count):
            self.signals.complete_signal.emit(count)
        
        def on_error(error):
            self.signals.update_signal.emit(f"Error: {error}", "#ff6b6b")
            self.signals.complete_signal.emit(0)
        
        typing_engine.on_progress = on_progress
        typing_engine.on_complete = on_complete
        typing_engine.on_error = on_error
    
    def update_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def typing_complete(self, count):
        self.progress_bar.setValue(100)
        if count > 0:
            self.update_status(f"Done! Typed {count} characters", "#51cf66")
        QTimer.singleShot(2000, lambda: self.reset_status())
    
    def reset_status(self):
        if self.hotkey_registered:
            self.update_status("Running  —  Alt+V to paste", "#51cf66")
        else:
            self.update_status("Stopped", "#8a8a9a")
    
    def on_mode_change(self, btn_id: int):
        """Switch typing engine mode when speed radio button changes"""
        mode = {0: 'fast', 1: 'medium', 2: 'slow'}.get(btn_id, 'fast')
        typing_engine.set_mode(mode)
    
    def trigger_typing(self):
        if typing_engine.is_typing:
            return
        QTimer.singleShot(0, self.start_typing)
    
    def start_typing(self):
        try:
            text = pyperclip.paste()
        except Exception as e:
            self.update_status(f"Clipboard error: {str(e)}", "#ff6b6b")
            print(f"Clipboard error: {e}")
            import traceback
            traceback.print_exc()
            return
        
        if not text:
            self.update_status("Clipboard is empty", "#ff6b6b")
            return
        
        char_count = len(text.replace('\r', ''))
        
        self.update_status(f"Typing {char_count} characters...", "#fcc419")
        self.progress_bar.setValue(0)
        
        def type_thread():
            success_count = typing_engine.type_text(text)
            if success_count > 0:
                self.signals.update_signal.emit(
                    f"Done! Typed {success_count} characters", "#51cf66"
                )
            self.signals.complete_signal.emit(success_count)
        
        threading.Thread(target=type_thread, daemon=True).start()
    
    def setup_sync_callbacks(self):
        """Setup callbacks for clipboard sync service"""
        def on_status_change(status, is_connected):
            self.signals.sync_status_signal.emit(status, is_connected)
        
        def on_sync(message):
            self.signals.sync_update_signal.emit(message)
        
        def on_error(error):
            self.signals.sync_update_signal.emit(f"Error: {error}")
        
        clipboard_sync.on_status_change = on_status_change
        clipboard_sync.on_sync = on_sync
        clipboard_sync.on_error = on_error
    
    def toggle_phone_sync(self):
        """Toggle phone sync on/off using Roll Number"""
        if clipboard_sync.is_running:
            # Stop sync
            clipboard_sync.stop_sync()
            self.sync_btn.setText("🔗 Enable Phone Sync")
        else:
            # Start sync using Roll Number instead of generating a code
            roll = auth_service.current_user.get('roll_number') if auth_service.current_user else ""
            if roll and clipboard_sync.start_sync(roll, generate_new=False):
                self.sync_btn.setText("🔌 Disconnect Sync")
                self.pairing_code_label.setText("Syncing Android clipboard")
                self.pairing_code_label.setStyleSheet("color: #51cf66; font-weight: bold; font-size: 14px;")
            else:
                self.pairing_code_label.setText("Failed to start sync")
                self.pairing_code_label.setStyleSheet("color: #ff6b6b;")
    
    def update_sync_status(self, status, is_connected):
        """Update sync status display"""
        if is_connected:
            self.sync_status_dot.setStyleSheet("color: #51cf66;")
            self.pairing_code_label.setText("Sync active")
            self.pairing_code_label.setStyleSheet("color: #51cf66; font-weight: bold; font-size: 14px;")
        else:
            self.sync_status_dot.setStyleSheet("color: #ff6b6b;")
            self.pairing_code_label.setText("Sync paused")
            self.pairing_code_label.setStyleSheet("color: #8a8a9a; font-size: 13px;")
            self.sync_event_label.setText("")
    
    def update_sync_event(self, message):
        """Update sync event message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.sync_event_label.setText(f"{timestamp} - {message}")
        if "Error" in message:
            self.sync_event_label.setStyleSheet("color: #ff6b6b; margin-top: 4px;")
        else:
            self.sync_event_label.setStyleSheet("color: #51cf66; margin-top: 4px;")
    
    def closeEvent(self, event):
        self._save_session_state()
        self.unregister_hotkey()
        # Stop clipboard sync if running
        if clipboard_sync.is_running:
            clipboard_sync.stop_sync()
        event.accept()


def _cleanup_old_versions():
    """On startup, silently delete any EXE containing 'codepaste' in its
    filename from common locations (Downloads, Desktop, Documents, Temp)."""
    userprofile = os.environ.get("USERPROFILE", os.path.expanduser("~"))

    search_dirs = []
    seen = set()
    for d in [
        os.path.join(userprofile, "Downloads"),
        os.path.join(userprofile, "Desktop"),
        os.path.join(userprofile, "Documents"),
        os.path.join(userprofile, "AppData", "Local", "Temp"),
    ]:
        norm = os.path.normcase(os.path.abspath(d))
        if norm not in seen:
            seen.add(norm)
            search_dirs.append(d)

    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if "codepaste" in fname.lower() and fname.lower().endswith(".exe"):
                try:
                    os.remove(os.path.join(directory, fname))
                except Exception:
                    pass  # file may be locked — skip silently


def start_app():
    """Start the application"""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        from PyQt6.QtGui import QIcon
        
        # Proper PyInstaller icon resolution
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle
            base_path = sys._MEIPASS
        else:
            # If run from Python directly
            base_path = os.path.dirname(__file__)
            
        icon_path = os.path.join(base_path, "icon.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        # Clean up old EXE versions from Desktop/Downloads before anything else
        _cleanup_old_versions()

        # Show login dialog first
        login = LoginWindow()
        if login.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)  # User closed login window

        window = MainWindow()
        window.show()

        sys.exit(app.exec())
    
    except Exception as e:
        # Show error dialog if something goes wrong
        from PyQt6.QtWidgets import QMessageBox
        try:
            QMessageBox.critical(
                None,
                "CTpaste Error",
                f"Failed to start application:\n\n{str(e)}\n\nPlease try running as administrator or contact support."
            )
        except:
            # If even the error dialog fails, print to console
            print(f"FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    start_app()

"""
CTpaste Auth Service
Handles user authentication and session management against Firebase.
"""
import hashlib
import json
import os
import threading
import time
import sys
from urllib import request, error

# ── Firebase config ─────────────────────────────────
def _get_firebase_url():
    config_paths = []
    
    # 1. PyInstaller bundled path
    if hasattr(sys, '_MEIPASS'):
        config_paths.append(os.path.join(sys._MEIPASS, "firebase_config.json"))
        # Also check relative to the .exe itself
        config_paths.append(os.path.join(os.path.dirname(sys.executable), "firebase_config.json"))
    
    # 2. Local dev paths
    config_paths.extend([
        os.path.join(os.path.dirname(__file__), "..", "..", "firebase_config.json"),
        os.path.join(os.path.dirname(__file__), "..", "firebase_config.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "firebase_config.json"),
        "firebase_config.json",
    ])
    
    for p in config_paths:
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f).get("databaseURL", "")
    return ""

DB_URL = _get_firebase_url()

# ── Plan configurations ──────────────────────────────
PLAN_CONFIG = {
    "GO":        {"speed": 2, "speed_name": "Slow",   "session_hrs": 1, "cooldown_hrs": 3},
    "PRO_SPEED": {"speed": 0, "speed_name": "Fast",   "session_hrs": 1, "cooldown_hrs": 3},
    "PRO_HOUR":  {"speed": 2, "speed_name": "Slow",   "session_hrs": 2, "cooldown_hrs": 3},
    "PRO_BOTH":  {"speed": 0, "speed_name": "Fast",   "session_hrs": 2, "cooldown_hrs": 3},
    "SUPER":     {"speed": 1, "speed_name": "Medium", "session_hrs": 3, "cooldown_hrs": 3},
}

def _hash_password(password: str) -> str:
    """Match website's SHA-256 + salt hashing."""
    raw = (password + "__CTpaste_salt__").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _db_get(path: str):
    """GET from Firebase Realtime Database REST API."""
    try:
        url = f"{DB_URL}/{path}.json?_={int(time.time() * 1000)}"
        req = request.Request(url, headers={'Cache-Control': 'no-cache'})
        with request.urlopen(req, timeout=8) as resp:
            data = resp.read().decode()
            return json.loads(data)
    except Exception:
        return None

def _db_patch(path: str, data: dict):
    """PATCH to Firebase Realtime Database REST API."""
    try:
        url = f"{DB_URL}/{path}.json"
        payload = json.dumps(data).encode()
        req = request.Request(url, data=payload, method="PATCH",
                              headers={"Content-Type": "application/json"})
        request.urlopen(req, timeout=8)
        return True
    except Exception:
        return False

def _db_put(path: str, data):
    """PUT to Firebase Realtime Database REST API."""
    try:
        url = f"{DB_URL}/{path}.json"
        payload = json.dumps(data).encode()
        req = request.Request(url, data=payload, method="PUT",
                              headers={"Content-Type": "application/json"})
        request.urlopen(req, timeout=8)
        return True
    except Exception:
        return False


class AuthService:
    """
    Handles user auth and session management.
    Session state is stored in Firebase and mirrored locally.
    """

    def __init__(self):
        self.current_user = None   # dict: {roll_number, name, plan, config}
        self._session_start = None
        self._session_end   = None
        self._cooldown_until = None
        self._timer_thread  = None
        self._stop_timer    = False
        self._heartbeat_thread = None
        self._stop_heartbeat = False
        self.on_session_tick = None    # callback(remaining_secs, is_cooldown)
        self.on_session_expire = None  # callback()
        self.on_addons_changed = None  # callback(new_addons_dict)

    # ── Login / Logout ────────────────────────────────
    def login(self, roll_number: str, password: str) -> tuple[bool, str]:
        """
        Verify credentials against Firebase.
        Returns (success: bool, message: str)
        """
        if not DB_URL:
            return False, "Firebase not configured."

        user = _db_get(f"users/{roll_number}")
        if not user:
            return False, "Roll number not found."

        if not user.get("password_hash"):
            return False, "Account not set up. Please visit the website first."

        if user.get("suspended"):
            return False, "__SUSPENDED__"

        expected_hash = _hash_password(password)
        if user["password_hash"] != expected_hash:
            return False, "Incorrect password."

        # Base plan is always GO
        plan = "GO"
        config = PLAN_CONFIG["GO"]
        addons = user.get("active_addons", {})

        self.current_user = {
            "roll_number": roll_number,
            "name": user.get("name", roll_number),
            "plan": plan,
            "config": config,
            "active_addons": addons
        }

        # Update last login in background
        threading.Thread(
            target=_db_patch,
            args=(f"users/{roll_number}", {"last_login": int(time.time() * 1000)}),
            daemon=True
        ).start()

        # Start heartbeat
        self._stop_heartbeat = False
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

        return True, f"Welcome, {self.current_user['name']}!"

    def logout(self):
        self._stop_timer = True
        self._stop_heartbeat = True
        if self.current_user:
            roll = self.current_user["roll_number"]
            # Clear last_active on logout so they immediately show as offline
            threading.Thread(target=_db_patch, args=(f"users/{roll}", {"last_active": 0}), daemon=True).start()
        self.current_user = None
        self._session_start = None
        self._session_end = None
        self._cooldown_until = None

    def _heartbeat_loop(self):
        """Sends a ping every 15 seconds indicating the user is online, and checks for live add-ons."""
        while not self._stop_heartbeat and self.current_user:
            roll = self.current_user["roll_number"]
            try:
                # 1. Ping the server so admin sees we are online
                _db_patch(f"users/{roll}", {"last_active": int(time.time() * 1000)})
                
                # 2. Check for freshly purchased add-ons
                live_addons = _db_get(f"users/{roll}/active_addons") or {}
                local_addons = self.current_user.get("active_addons", {})
                
                # Simple difference check
                if live_addons != local_addons:
                    self.current_user["active_addons"] = live_addons
                    if self.on_addons_changed:
                        self.on_addons_changed(live_addons)
            except Exception:
                pass # Heartbeat ping failed silently
                
            # Sleep in 1s chunks so logout can interrupt quickly, but only poll every 60s
            for _ in range(60):
                if self._stop_heartbeat:
                    break
                time.sleep(1)

    # ── Session management ────────────────────────────
    def get_session_state(self) -> dict:
        """
        Fetch current session state from Firebase.
        Returns dict with keys: state ('none'|'active'|'cooldown'|'ready'),
        remaining_secs, session_hrs, cooldown_hrs
        """
        if not self.current_user:
            return {"state": "none", "remaining_secs": 0}

        roll = self.current_user["roll_number"]
        session = _db_get(f"sessions/{roll}")
        config = self.current_user["config"]
        now_ms = int(time.time() * 1000)

        if not session or not session.get("session_start"):
            return {"state": "ready", "remaining_secs": config["session_hrs"] * 3600}

        session_end = session.get("session_end", 0)
        cooldown_until = session.get("cooldown_until", 0)

        if now_ms < session_end:
            self._session_end = session_end
            self._cooldown_until = cooldown_until
            remaining = (session_end - now_ms) // 1000
            return {"state": "active", "remaining_secs": remaining}

        elif now_ms < cooldown_until:
            self._cooldown_until = cooldown_until
            remaining = (cooldown_until - now_ms) // 1000
            return {"state": "cooldown", "remaining_secs": remaining}

        else:
            return {"state": "ready", "remaining_secs": config["session_hrs"] * 3600}

    def start_session(self):
        """Start a new session for the current user."""
        if not self.current_user:
            return False

        config = self.current_user["config"]
        roll = self.current_user["roll_number"]
        now_ms = int(time.time() * 1000)
        session_ms = config["session_hrs"] * 3600 * 1000
        cooldown_ms = config["cooldown_hrs"] * 3600 * 1000

        self._session_end = now_ms + session_ms
        self._cooldown_until = now_ms + session_ms + cooldown_ms

        threading.Thread(
            target=_db_put,
            args=(f"sessions/{roll}", {
                "session_start": now_ms,
                "session_end": self._session_end,
                "cooldown_until": self._cooldown_until,
                "is_active": True
            }),
            daemon=True
        ).start()

        self._start_timer_thread()
        return True

    def resume_session(self, session_end_ms: int, cooldown_until_ms: int):
        """Resume a previously active session."""
        self._session_end = session_end_ms
        self._cooldown_until = cooldown_until_ms
        self._start_timer_thread()

    def _start_timer_thread(self):
        self._stop_timer = False
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()

    def _timer_loop(self):
        """Background thread that ticks every second and fires callbacks."""
        while not self._stop_timer:
            now_ms = int(time.time() * 1000)
            if self._session_end and now_ms < self._session_end:
                remaining = (self._session_end - now_ms) // 1000
                if self.on_session_tick:
                    self.on_session_tick(remaining, False)
            elif self._cooldown_until and now_ms < self._cooldown_until:
                remaining = (self._cooldown_until - now_ms) // 1000
                if self.on_session_tick:
                    self.on_session_tick(remaining, True)
                if self.on_session_expire and now_ms >= self._session_end:
                    # Fire expire once when session just ended
                    if self.on_session_expire:
                        self.on_session_expire()
                        self.on_session_expire = None  # fire only once
            elif self._cooldown_until and now_ms >= self._cooldown_until:
                if self.on_session_tick:
                    self.on_session_tick(0, False)
                break

            time.sleep(1)

    # ── Helpers ───────────────────────────────────────
    def get_plan_speed_mode(self) -> int:
        """Returns speed mode int: 0=Fast, 1=Medium, 2=Slow based on active add-ons"""
        if not self.current_user:
            return 2 # Slow default
        
        addons = self.current_user.get("active_addons", {})
        if addons.get("super_pass"):
            return 1 # Medium
        if addons.get("speed_boost"):
            return 0 # Fast
            
        return 2 # Slow Base

    def get_plan_name(self) -> str:
        """Computes a human-readable string based on active stacked add-ons"""
        if not self.current_user:
            return "GO"
        
        addons = self.current_user.get("active_addons", {})
        if addons.get("super_pass"):
            return "SUPER Pass"
            
        parts = []
        if addons.get("speed_boost"):
            parts.append("Speed")
        if addons.get("extra_hours_added"):
            parts.append(f"+{addons.get('extra_hours_added')}Hr")
            
        if parts:
            return "GO + " + " & ".join(parts)
        return "GO"

    def is_logged_in(self) -> bool:
        return self.current_user is not None


# Singleton
auth_service = AuthService()

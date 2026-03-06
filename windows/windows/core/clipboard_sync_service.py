"""
Clipboard Sync Service - Firebase-based clipboard synchronization
Syncs clipboard between desktop and Android devices using pairing codes
"""

import threading
import time
import random
import string
import json
import os
from typing import Optional, Callable
from datetime import datetime

import pyperclip

# Firebase will be imported only when needed to avoid errors if not configured
firebase_admin = None
db = None


class ClipboardSyncService:
    """
    Manages clipboard synchronization between desktop and Android devices.
    Uses Firebase Realtime Database for real-time sync.
    """
    
    def __init__(self):
        self.is_running = False
        self.pairing_code: Optional[str] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_clipboard_text = ""
        self.last_sync_time: Optional[datetime] = None
        self.should_stop = False
        
        # Callbacks for UI updates
        self.on_status_change: Optional[Callable[[str, bool], None]] = None
        self.on_sync: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        self.firebase_ref = None
        self.firebase_initialized = False
    
    def initialize_firebase(self, config_path: str = None) -> bool:
        """
        Initialize Firebase Admin SDK
        
        Args:
            config_path: Path to firebase service account JSON file
            
        Returns:
            True if successful, False otherwise
        """
        global firebase_admin, db
        
        try:
            import firebase_admin
            from firebase_admin import credentials, db as firebase_db
            
            # Check if already initialized
            if self.firebase_initialized:
                return True
            
            # Default config path
            if config_path is None:
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'firebase_config.json'
                )
            
            # Check if config exists
            if not os.path.exists(config_path):
                if self.on_error:
                    self.on_error(
                        "Firebase config not found. Please set up Firebase first.\n"
                        "See README for instructions."
                    )
                return False
            
            # Read config to get database URL
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            database_url = config_data.get('databaseURL')
            if not database_url:
                if self.on_error:
                    self.on_error("databaseURL not found in firebase_config.json")
                return False
            
            # Initialize Firebase Admin
            cred = credentials.Certificate(config_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            
            db = firebase_db
            self.firebase_initialized = True
            return True
            
        except ImportError:
            if self.on_error:
                self.on_error(
                    "Firebase Admin SDK not installed.\n"
                    "Run: pip install firebase-admin"
                )
            return False
        except Exception as e:
            if self.on_error:
                self.on_error(f"Firebase initialization error: {str(e)}")
            return False
    
    def generate_pairing_code(self) -> str:
        """
        Generate a random 6-character pairing code (alphanumeric, no ambiguous chars)
        
        Returns:
            6-character pairing code (e.g., "4K7BMX")
        """
        # Exclude ambiguous characters: 0, O, I, 1, l
        chars = string.ascii_uppercase.replace('O', '').replace('I', '') + \
                string.digits.replace('0', '').replace('1', '')
        
        code = ''.join(random.choices(chars, k=6))
        return code
    
    def start_sync(self, pairing_code: str, generate_new: bool = True) -> bool:
        """
        Start clipboard synchronization
        
        Args:
            pairing_code: 6-character pairing code
            generate_new: If True, generate new code; if False, use provided code
            
        Returns:
            True if sync started successfully
        """
        if self.is_running:
            if self.on_error:
                self.on_error("Sync already running")
            return False
        
        # Initialize Firebase if needed
        if not self.firebase_initialized:
            if not self.initialize_firebase():
                return False
        
        try:
            # We now use the roll number as the pairing code identifier
            self.pairing_code = pairing_code.strip()
            
            # Create Firebase reference for this user's clipboard
            self.firebase_ref = db.reference(f'users/{self.pairing_code}/clipboard')
            
            # Get current clipboard content
            try:
                self.last_clipboard_text = pyperclip.paste()
            except:
                self.last_clipboard_text = ""
            
            # Start monitoring thread
            self.should_stop = False
            self.monitor_thread = threading.Thread(
                target=self._monitor_clipboard,
                daemon=True
            )
            self.monitor_thread.start()
            
            # Start Firebase listener
            print(f"DEBUG: Attaching listener to: users/{self.pairing_code}/clipboard")
            try:
                # Get initial value to verify connection
                initial_val = self.firebase_ref.get()
                print(f"DEBUG: Initial value validation: {initial_val}")
                
                # Attach listener
                self.firebase_ref.listen(self._on_firebase_change)
                print("DEBUG: Listener attached successfully")
            except Exception as e:
                print(f"DEBUG: Failed to attach listener: {e}")
            
            self.is_running = True
            
            if self.on_status_change:
                self.on_status_change(f"Connected - Code: {self.pairing_code}", True)
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to start sync: {str(e)}")
            return False
    
    def stop_sync(self):
        """Stop clipboard synchronization"""
        self.should_stop = True
        self.is_running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        self.firebase_ref = None
        self.pairing_code = None
        
        if self.on_status_change:
            self.on_status_change("Disconnected", False)
    
    def _monitor_clipboard(self):
        """Background thread that monitors clipboard changes"""
        print("DEBUG: Monitor thread started")
        while not self.should_stop:
            try:
                # Skip if we are currently processing a remote update
                if self.is_remote_update:
                    time.sleep(0.1)
                    continue

                current_text = pyperclip.paste()
                
                # Check if clipboard changed
                if current_text != self.last_clipboard_text:
                    print(f"DEBUG: Local change detected! Old: '{self.last_clipboard_text[:20]}...', New: '{current_text[:20]}...'")
                    self.last_clipboard_text = current_text
                    
                    # Push to Firebase
                    if self.firebase_ref and current_text:
                        print("DEBUG: Pushing to Firebase...")
                        self.firebase_ref.set({
                            'text': current_text,
                            'timestamp': time.time(),
                            'source': 'desktop'
                        })
                        
                        self.last_sync_time = datetime.now()
                        
                        if self.on_sync:
                            self.on_sync(f"Synced to phone")
                
                # Check every 500ms
                time.sleep(0.5)
                
            except Exception as e:
                # Ignore empty clipboard errors
                time.sleep(1)

    def _set_clipboard(self, text: str) -> bool:
        """Reliably set clipboard text with retries"""
        print(f"DEBUG: Setting clipboard to: '{text[:20]}...'")
        max_retries = 5
        for i in range(max_retries):
            try:
                pyperclip.copy(text)
                # Verify
                pasted = pyperclip.paste()
                if pasted == text:
                    print("DEBUG: Clipboard set successfully")
                    return True
                print(f"DEBUG: Verify failed (Attempt {i+1}). Got: '{pasted[:20]}...'")
                time.sleep(0.1)
            except Exception as e:
                print(f"DEBUG: Set error: {e}")
                time.sleep(0.1)
        print("DEBUG: Failed to set clipboard after retries")
        return False

    def _on_firebase_change(self, event):
        """Callback when Firebase data changes"""
        try:
            if event.data is None:
                return
            
            data = event.data
            print(f"DEBUG: Firebase event received: {data}")
            
            # Helper to extract text safely whatever the structure
            is_manual = False
            if isinstance(data, dict):
                # Check for manual override
                if data.get('source') == 'android_manual':
                    print("DEBUG: Manual override received!")
                    is_manual = True
                # Don't sync our own changes (unless manual force)
                elif data.get('source') == 'desktop':
                    print("DEBUG: Ignoring our own change")
                    return
                
                new_text = data.get('text', '')
            else:
                return
            
            print(f"DEBUG: Remote text: '{new_text[:20]}...'")
            
            # Update local clipboard if different OR if manual override
            if is_manual or (new_text and new_text != self.last_clipboard_text):
                print("DEBUG: Updating local clipboard from remote...")
                # Set flag to pause monitor
                self.is_remote_update = True
                
                if self._set_clipboard(new_text):
                    self.last_clipboard_text = new_text
                    self.last_sync_time = datetime.now()
                    
                    if self.on_sync:
                        self.on_sync(f"Synced from phone")
                else:
                    if self.on_error:
                        self.on_error("Failed to update clipboard")
                
                # Release flag
                time.sleep(0.5)  # Increased grace period
                self.is_remote_update = False
                print("DEBUG: Remote update complete, monitor resumed")
                    
        except Exception as e:
            self.is_remote_update = False
            print(f"DEBUG: Firebase callback error: {e}")
            if self.on_error:
                self.on_error(f"Sync error: {str(e)}")
    
    def get_status(self) -> dict:
        """
        Get current sync status
        
        Returns:
            Dictionary with status information
        """
        return {
            'is_running': self.is_running,
            'pairing_code': self.pairing_code,
            'last_sync': self.last_sync_time.strftime('%H:%M:%S') if self.last_sync_time else 'Never',
            'connected': self.is_running
        }


# Global instance
clipboard_sync = ClipboardSyncService()

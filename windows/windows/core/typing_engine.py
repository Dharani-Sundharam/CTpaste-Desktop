"""
Stealth Typing Engine - Uses WM_CHAR direct window messaging
to bypass kernel-level keyboard hooks.
"""

import time
import ctypes
import random
from ctypes import wintypes
from typing import Callable, Optional

# Windows API constants
WM_CHAR = 0x0102
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_BACK = 0x08
VK_DELETE = 0x2E
VK_RIGHT = 0x27

# Load DLLs
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Define function signatures
user32.GetForegroundWindow.restype = wintypes.HWND
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.GetFocus.restype = wintypes.HWND


class TypingEngine:
    """Stealth typing engine using direct window messages"""
    
    def __init__(self):
        self.is_typing = False
        self.should_stop = False
        self.base_delay = 0.050  # used by fast mode
        self.delete_duration = 5.0  # Delete key spam duration
        self.strip_indentation = True  # Smart indentation for Python IDEs
        self.typing_mode = 'fast'  # 'fast', 'medium', or 'slow'
        self.skip_auto_closing_tags = True  # Avoid typing closing tags that IDE auto-completes 
        
        
        # Callbacks
        self.on_progress: Optional[Callable[[int, int], None]] = None
        self.on_complete: Optional[Callable[[int], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
    
    def get_indentation_level(self, line: str) -> int:
        """Get the indentation level (number of leading spaces/tabs converted to spaces)"""
        indent = 0
        for char in line:
            if char == ' ':
                indent += 1
            elif char == '\t':
                indent += 4  # Treat tab as 4 spaces
            else:
                break
        return indent
    
    def preprocess_text_with_dedent_markers(self, text: str) -> str:
        """
        Smart handling for Python auto-indentation.
        Strips leading whitespace and inserts BACKSPACE markers for dedents.
        HTML tag completion is handled dynamically in type_text.
        """
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        
        # Handle Python indentation
        lines = text.split('\n')
        if not lines:
            return text
        
        processed_lines = []
        last_indent = 0
        
        for line in lines:
            if not line.strip():  # Empty line
                processed_lines.append('')
                continue
            
            current_indent = self.get_indentation_level(line)
            stripped_line = line.lstrip()
            
            # If we're dedenting (going back to lower indentation)
            if current_indent < last_indent:
                # Calculate how many indentation levels to go back
                indent_diff = last_indent - current_indent
                backspaces_needed = indent_diff // 4  # Each indent level is 4 spaces
                if backspaces_needed > 0:
                    marker = f'<<<BACKSPACE:{backspaces_needed}>>>'
                    processed_lines.append(marker + stripped_line)
                else:
                    processed_lines.append(stripped_line)
            else:
                processed_lines.append(stripped_line)
            
            last_indent = current_indent
        
        return '\n'.join(processed_lines)
    
    def get_focused_control(self) -> Optional[int]:
        """Get the handle of the currently focused control"""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        
        remote_thread = user32.GetWindowThreadProcessId(hwnd, None)
        current_thread = kernel32.GetCurrentThreadId()
        
        if remote_thread != current_thread:
            user32.AttachThreadInput(current_thread, remote_thread, True)
        
        focused = user32.GetFocus()
        
        if remote_thread != current_thread:
            user32.AttachThreadInput(current_thread, remote_thread, False)
        
        return focused if focused else hwnd
    
    def send_char(self, hwnd: int, char: str) -> bool:
        """Send a character via WM_CHAR"""
        result = user32.PostMessageW(hwnd, WM_CHAR, ord(char), 0)
        return result != 0
    
    def send_key(self, hwnd: int, vk_code: int):
        """Send a virtual key via WM_KEYDOWN/WM_KEYUP"""
        scan_code = user32.MapVirtualKeyW(vk_code, 0)
        lparam_down = 1 | (scan_code << 16)
        lparam_up = 1 | (scan_code << 16) | (1 << 30) | (1 << 31)
        
        user32.PostMessageW(hwnd, WM_KEYDOWN, vk_code, lparam_down)
        time.sleep(0.001)
        user32.PostMessageW(hwnd, WM_KEYUP, vk_code, lparam_up)
    
    def get_delay(self) -> float:
        """Return the appropriate delay based on current typing mode"""
        if self.typing_mode == 'fast':
            return random.uniform(0.030, 0.070)   # ~50ms
        elif self.typing_mode == 'medium':
            return random.uniform(0.100, 0.150)   # 100–150ms
        else:  # slow
            return random.uniform(0.150, 0.200)   # 150–200ms

    def set_mode(self, mode: str):
        """Set typing mode: 'fast', 'medium', or 'slow'"""
        if mode in ('fast', 'medium', 'slow'):
            self.typing_mode = mode
    
    def spam_delete(self, hwnd: int, duration: float = 3.0):
        """Rapidly press Delete key"""
        start_time = time.time()
        while (time.time() - start_time) < duration and not self.should_stop:
            self.send_key(hwnd, VK_DELETE)
            time.sleep(0.05)
    
    def type_text(self, text: str, spam_delete_after: bool = True) -> int:
        """
        Type text using stealth method.
        Returns number of characters successfully typed.
        """
        if self.is_typing:
            if self.on_error:
                self.on_error("Already typing in progress")
            return 0
        
        self.is_typing = True
        self.should_stop = False
        
        # Preprocess text to handle IDE auto-indentation
        text = self.preprocess_text_with_dedent_markers(text)
        
        try:
            # Small delay to ensure focus
            time.sleep(0.3)
            
            hwnd = self.get_focused_control()
            if not hwnd:
                if self.on_error:
                    self.on_error("Could not find focused window")
                return 0
            
            
            success_count = 0
            total = len(text)
            
            i = 0
            while i < len(text):
                if self.should_stop:
                    break
                
                # Check for IDE auto-populated closing tags (e.g., </something>)
                if self.skip_auto_closing_tags and text.startswith('</', i):
                    import re
                    match = re.match(r'</([a-zA-Z0-9\-]+)>', text[i:])
                    if match:
                        print(f"[DEBUG] Skipping IDE auto-closed tag: {match.group(0)}")
                        self.send_char(hwnd, '<')
                        time.sleep(self.get_delay())
                        self.send_char(hwnd, '/')
                        time.sleep(0.15)  # Pause to let IDE output the rest of closing tag
                        i += len(match.group(0))  # Skip the entire closing tag from our payload
                        success_count += 2  # Count the '<' and '/'
                        continue

                
                # Check for backspace marker (for dedenting)
                if text[i:i+13] == '<<<BACKSPACE:':
                    end_marker = text.find('>>>', i)
                    if end_marker != -1:
                        try:
                            backspaces = int(text[i+13:end_marker])
                            for _ in range(backspaces):
                                self.send_key(hwnd, VK_BACK)
                                time.sleep(self.get_delay())
                            i = end_marker + 3
                            continue
                        except ValueError:
                            pass
                
                char = text[i]
                
                if char == '\r':
                    i += 1
                    continue
                elif char == '\n':
                    self.send_key(hwnd, VK_RETURN)
                    time.sleep(self.get_delay())
                elif char == '\t':
                    self.send_key(hwnd, VK_TAB)
                    time.sleep(self.get_delay())
                else:
                    if self.send_char(hwnd, char):
                        success_count += 1
                    time.sleep(self.get_delay())
                
                i += 1
                
                # Progress callback every 50 chars
                if self.on_progress and (i + 1) % 50 == 0:
                    self.on_progress(i + 1, total)
            
            # Final progress update
            if self.on_progress:
                self.on_progress(total, total)
            
            # Spam delete after typing
            if spam_delete_after and not self.should_stop:
                time.sleep(0.2)
                self.spam_delete(hwnd, self.delete_duration)
            
            if self.on_complete:
                self.on_complete(success_count)
            
            return success_count
            
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            return 0
        finally:
            self.is_typing = False
    
    def stop(self):
        """Stop current typing operation"""
        self.should_stop = True
    
    def set_speed(self, delay_ms: int):
        """Set typing speed (delay between characters in milliseconds)"""
        self.base_delay = delay_ms / 1000.0
    
    def set_delete_duration(self, seconds: float):
        """Set delete spam duration"""
        self.delete_duration = seconds


# Global engine instance
typing_engine = TypingEngine()

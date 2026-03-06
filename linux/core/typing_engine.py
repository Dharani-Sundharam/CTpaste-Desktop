"""
Stealth Typing Engine for Linux - Uses pynput for cross-platform typing
"""

import time
import random
from typing import Callable, Optional
from pynput.keyboard import Controller, Key

keyboard_controller = Controller()

class TypingEngine:
    """Typing engine using pynput"""
    
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
        """
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
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
            
            if current_indent < last_indent:
                indent_diff = last_indent - current_indent
                backspaces_needed = indent_diff // 4
                if backspaces_needed > 0:
                    marker = f'<<<BACKSPACE:{backspaces_needed}>>>'
                    processed_lines.append(marker + stripped_line)
                else:
                    processed_lines.append(stripped_line)
            else:
                processed_lines.append(stripped_line)
            
            last_indent = current_indent
        
        return '\n'.join(processed_lines)
    
    def send_char(self, char: str):
        """Send a character"""
        keyboard_controller.type(char)
        return True
    
    def send_key(self, key):
        """Send a special key"""
        keyboard_controller.press(key)
        keyboard_controller.release(key)
    
    def get_delay(self) -> float:
        """Return the appropriate delay based on current typing mode"""
        if self.typing_mode == 'fast':
            return random.uniform(0.030, 0.070)
        elif self.typing_mode == 'medium':
            return random.uniform(0.100, 0.150)
        else:  # slow
            return random.uniform(0.250, 0.300)

    def set_mode(self, mode: str):
        """Set typing mode"""
        if mode in ('fast', 'medium', 'slow'):
            self.typing_mode = mode
    
    def spam_delete(self, duration: float = 3.0):
        """Rapidly press Delete key"""
        start_time = time.time()
        while (time.time() - start_time) < duration and not self.should_stop:
            self.send_key(Key.delete)
            time.sleep(0.05)
    
    def type_text(self, text: str, spam_delete_after: bool = True) -> int:
        if self.is_typing:
            if self.on_error:
                self.on_error("Already typing in progress")
            return 0
        
        self.is_typing = True
        self.should_stop = False
        
        text = self.preprocess_text_with_dedent_markers(text)
        
        try:
            # Small delay to ensure focus
            time.sleep(0.3)
            
            success_count = 0
            total = len(text)
            i = 0
            
            while i < len(text):
                if self.should_stop:
                    break
                
                # Check for IDE auto-populated closing tags
                if self.skip_auto_closing_tags and text.startswith('</', i):
                    import re
                    match = re.match(r'</([a-zA-Z0-9\-]+)>', text[i:])
                    if match:
                        self.send_char('<')
                        time.sleep(self.get_delay())
                        self.send_char('/')
                        time.sleep(0.15)
                        i += len(match.group(0))
                        success_count += 2
                        continue
                
                # Check for backspace marker
                if text[i:i+13] == '<<<BACKSPACE:':
                    end_marker = text.find('>>>', i)
                    if end_marker != -1:
                        try:
                            backspaces = int(text[i+13:end_marker])
                            for _ in range(backspaces):
                                self.send_key(Key.backspace)
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
                    self.send_key(Key.enter)
                    time.sleep(self.get_delay())
                elif char == '\t':
                    self.send_key(Key.tab)
                    time.sleep(self.get_delay())
                else:
                    self.send_char(char)
                    success_count += 1
                    time.sleep(self.get_delay())
                
                i += 1
                
                if self.on_progress and (i + 1) % 50 == 0:
                    self.on_progress(i + 1, total)
            
            if self.on_progress:
                self.on_progress(total, total)
            
            if spam_delete_after and not self.should_stop:
                time.sleep(0.2)
                self.spam_delete(self.delete_duration)
            
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
        self.should_stop = True
    
    def set_speed(self, delay_ms: int):
        self.base_delay = delay_ms / 1000.0
    
    def set_delete_duration(self, seconds: float):
        self.delete_duration = seconds

# Global engine instance
typing_engine = TypingEngine()

# CTpaste for Linux

CTpaste is a stealth auto-typing application synchronized with Android clipboard mechanisms over Firebase. 
This directory contains the completely refactored Linux-compatible iteration of the originally Windows-only desktop client. 

## Features
- **Cross-Platform AutoTyper**: Employs `pynput` as the core keystroke injection engine for full compatibility across Debian-based Linux environments (e.g., Ubuntu, Kali Linux, Mint).
- **Stealth Sync**: Pings your remote Firebase instance to securely fetch and paste encrypted payloads directly into your desired editor without intermediate `Ctrl+V` commands.
- **Global Hotkeys**: Uses asynchronous hotkey listeners to trigger paste configurations system-wide without `sudo` requirements.

## Installation

We provide a compiled `.deb` installer for Debian-based systems so you do not have to install Python or manually manage virtual environments. The package carries all dependencies (including `PyQt6` and `pynput`) in a complete standalone executable.

### Using the Installer (Recommended)
1. Download or browse to the provided `ctpaste_1.0_amd64.deb` bundle.
2. Open your terminal in the directory where the `.deb` file is located and run:
   ```bash
   sudo dpkg -i ctpaste_1.0_amd64.deb
   ```
3. Once completed, CTpaste will appear in your Linux application menu. You can simply click it to launch!

### Testing from Source (Developers)
If you wish to run the program via Python directly:
```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt PyQt6

# 3. Start the Application
python main.py
```

## Setup requirements
To utilize synchronization, ensure you have an active `firebase_config.json` placed on the project root or where the binary is installed (`/opt/ctpaste/`). This file is required to connect securely to your Firebase Realtime Database.

"""
scan_old_exes.py
----------------
Scans common locations for any exe whose name contains 'codepaste' (case-insensitive)
and optionally deletes them.

Usage:
    python admin_scripts/scan_old_exes.py           # list only
    python admin_scripts/scan_old_exes.py --delete  # delete them
"""

import os
import sys


def scan(delete: bool = False):
    userprofile = os.environ.get("USERPROFILE", os.path.expanduser("~"))

    candidates = [
        os.path.join(userprofile, "Downloads"),
        os.path.join(userprofile, "Desktop"),
        os.path.join(userprofile, "Documents"),
        os.path.join(userprofile, "OneDrive", "Desktop"),
        os.path.join(userprofile, "OneDrive - Personal", "Desktop"),
        os.path.join(userprofile, "AppData", "Local", "Temp"),
    ]

    # Deduplicate, skip bare drive roots
    seen, search_dirs = set(), []
    for d in candidates:
        norm = os.path.normcase(os.path.abspath(d))
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.splitdrive(norm)[1] in ("\\", "/", ""):
            continue
        search_dirs.append(d)

    found = []
    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if "codepaste" in fname.lower() and fname.lower().endswith(".exe"):
                abs_path = os.path.abspath(os.path.join(directory, fname))
                if abs_path not in found:
                    found.append(abs_path)

    if not found:
        print("✅  No CodePaste exe files found.")
        return

    print(f"Found {len(found)} file(s) to remove:\n")
    for f in found:
        size_kb = os.path.getsize(f) // 1024
        print(f"  🗑️   {f}  ({size_kb} KB)")

    if delete:
        print()
        for f in found:
            try:
                os.remove(f)
                print(f"  Deleted: {f}")
            except Exception as e:
                print(f"  ⚠️  Could not delete {f}: {e}  (still running?)")
    else:
        print("\nRun with --delete to remove them.")


if __name__ == "__main__":
    scan(delete="--delete" in sys.argv)

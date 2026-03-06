import sys
import os
from PIL import Image

def convert_png_to_ico():
    source_png = os.path.join(os.path.dirname(__file__), "..", "icon.png")
    out_ico = os.path.join(os.path.dirname(__file__), "..", "desktop_app", "assets", "icon.ico")
    
    if not os.path.exists(source_png):
        print(f"ERROR: {source_png} not found!")
        sys.exit(1)
        
    img = Image.open(source_png)
    # Ensure it's RGBA
    img = img.convert("RGBA")
    
    # Save as ICO with multiple sizes for best desktop appearance
    os.makedirs(os.path.dirname(out_ico), exist_ok=True)
    img.save(out_ico, format='ICO', sizes=[(256,256), (128,128), (64,64), (32,32), (16,16)])
    print(f"✅ Converted custom icon to {out_ico}")

if __name__ == '__main__':
    convert_png_to_ico()

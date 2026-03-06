import sys
import subprocess
import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw, ImageFont

def make_icon():
    size = 256
    # Classic dark indigo background
    img = Image.new('RGBA', (size, size), color=(11, 13, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Outer thin border
    draw.rectangle([10, 10, size-10, size-10], outline=(124, 110, 247, 255), width=4)
    
    # Draw a stylized "C" 
    draw.arc([48, 64, 144, 192], start=45, end=315, fill=(156, 143, 255, 255), width=24)
    
    # Draw a stylized "T"
    draw.rectangle([140, 64, 208, 88], fill=(255, 107, 129, 255))
    draw.rectangle([162, 88, 186, 192], fill=(255, 107, 129, 255))

    out_path = os.path.join(os.path.dirname(__file__), "..", "desktop_app", "assets", "icon.ico")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Save as ICO with multiple sizes for best desktop appearance
    img.save(out_path, format='ICO', sizes=[(256,256), (128,128), (64,64), (32,32), (16,16)])
    print(f"✅ Created classic CTpaste icon at {out_path}")

if __name__ == '__main__':
    make_icon()

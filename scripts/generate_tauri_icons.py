import os
from PIL import Image, ImageDraw

def generate_icons():
    icon_dir = os.path.abspath("desktop/src-tauri/icons")
    os.makedirs(icon_dir, exist_ok=True)
    
    # 1. Create base 512x512 canvas
    # Sleek dark background with CHERENKOV cyan glow theme
    img = Image.new("RGBA", (512, 512), (10, 15, 25, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw a glowing cyan circle representing particle beam / Cherenkov radiation
    for r in range(160, 0, -4):
        alpha = int((160 - r) * 1.5)
        draw.ellipse(
            [(256 - r, 256 - r), (256 + r, 256 + r)],
            fill=(0, 240, 255, alpha)
        )
        
    # Draw core beam
    draw.ellipse(
        [(226, 226), (286, 286)],
        fill=(255, 255, 255, 255)
    )
    
    # Save PNGs in different sizes
    img.resize((32, 32), Image.Resampling.LANCZOS).save(os.path.join(icon_dir, "32x32.png"))
    img.resize((128, 128), Image.Resampling.LANCZOS).save(os.path.join(icon_dir, "128x128.png"))
    img.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(icon_dir, "128x128@2x.png"))
    
    # Save ICO file (with standard sizes)
    ico_img = img.resize((256, 256), Image.Resampling.LANCZOS)
    ico_img.save(
        os.path.join(icon_dir, "icon.ico"),
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    
    # Write a dummy icns file just in case it is read
    with open(os.path.join(icon_dir, "icon.icns"), "w") as f:
        f.write("dummy-icns")
        
    print("Successfully generated Tauri app icons at desktop/src-tauri/icons/")

if __name__ == "__main__":
    generate_icons()

"""
Quick setup helper - Run this after saving your grass image
"""

import os
from pathlib import Path

def check_setup():
    """Verify all visual improvements are ready"""
    
    base_dir = Path(__file__).parent
    assets_dir = base_dir / "assets"
    grass_path = assets_dir / "grass_texture.jpg"
    
    print("=" * 60)
    print("🎨 IAATCMS Visual Setup Checker")
    print("=" * 60)
    
    # Check grass texture
    if grass_path.exists():
        size = grass_path.stat().st_size / 1024  # KB
        print(f"✅ Grass texture found: {grass_path}")
        print(f"   Size: {size:.1f} KB")
    else:
        print(f"⚠️  Grass texture missing: {grass_path}")
        print(f"   Please save your grass image to this location")
        print(f"   The simulation will use a solid green background as fallback")
    
    print()
    
    # Check main.py modifications
    main_path = base_dir / "main.py"
    if main_path.exists():
        content = main_path.read_text()
        checks = [
            ("Grass texture loading", "grass_texture = pygame.image.load"),
            ("Improved taxi roads", "pygame.draw.line(self.screen, (60,60,60)"),
            ("Yellow centerlines", "(255, 215, 0)"),
            ("Enhanced gates", "border_radius=5")
        ]
        
        print("Code modifications:")
        for name, marker in checks:
            status = "✅" if marker in content else "❌"
            print(f"{status} {name}")
    
    print()
    print("=" * 60)
    print("Next steps:")
    print("1. If grass texture is missing, save it to assets/grass_texture.jpg")
    print("2. Run: python main.py")
    print("3. Check VISUAL_IMPROVEMENTS.md for details")
    print("=" * 60)

if __name__ == "__main__":
    check_setup()

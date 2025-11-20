"""
Setup script for grass texture
===============================

Since the grass image was provided as an attachment, please follow these steps:

1. Save the grass image you provided to:
   Starmind-Game-by-AI/AI/iaatcms_3d/assets/grass_texture.jpg

2. Or run this script if you have the image in your Downloads folder:

   python setup_grass.py <path_to_grass_image>

The simulation will work without the texture (using a solid green background),
but it looks much better with the real grass texture!
"""

import sys
import os
import shutil
from pathlib import Path

def setup_grass_texture(source_path=None):
    """Copy grass texture to assets folder"""
    
    # Target location
    script_dir = Path(__file__).parent
    assets_dir = script_dir / "assets"
    target_path = assets_dir / "grass_texture.jpg"
    
    # Create assets dir if needed
    assets_dir.mkdir(exist_ok=True)
    
    if source_path:
        source = Path(source_path)
        if not source.exists():
            print(f"❌ Error: Source file not found: {source}")
            return False
        
        try:
            shutil.copy(source, target_path)
            print(f"✅ Successfully copied grass texture to {target_path}")
            return True
        except Exception as e:
            print(f"❌ Error copying file: {e}")
            return False
    else:
        print("ℹ️  Please provide the path to your grass image:")
        print(f"   python setup_grass.py <path_to_grass_image>")
        print(f"\n   Target location: {target_path}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        setup_grass_texture(sys.argv[1])
    else:
        setup_grass_texture()

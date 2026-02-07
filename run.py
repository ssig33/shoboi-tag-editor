#!/usr/bin/env python3
"""PyInstaller entry point"""

import sys
sys.path.insert(0, 'src')

from shoboi_tag_editor.main import main

if __name__ == "__main__":
    sys.exit(main())

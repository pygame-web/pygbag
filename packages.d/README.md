put your package build script + patches here
in a subfolder matching the module name.

eg for pygame:
```
pygame
├── pygame.c
├── pygame.h
├── pygame.overlay
│   ├── freesansbold.ttf
│   ├── freetype.py
│   ├── __init__.py
│   ├── _sdl2
│   │   └── __init__.py
│   ├── sysfont.py
│   └── wasm_patches.py
├── pygame.sh
└── README.md

2 directories, 10 files
```



# palette.py
# English comments: simple local LEGO-like palette. Replace later with an official list or API.
from typing import List, Tuple, Dict

# Each entry: (name, code, (r,g,b))
LEGO_PALETTE: List[Dict] = [
    {"name": "White", "code": "BLANC", "rgb": (242, 243, 242)},
    {"name": "Black", "code": "NOIR", "rgb": (27, 42, 52)},
    {"name": "Red",   "code": "RED",  "rgb": (196, 40, 27)},
    {"name": "Blue",  "code": "BLUE", "rgb": (13, 105, 171)},
    {"name": "Yellow","code": "YEL",  "rgb": (245, 205, 47)},
    {"name": "Green", "code": "GRN",  "rgb": (40, 127, 70)},
    {"name": "Dark Gray", "code": "DGR", "rgb": (99, 95, 98)},
    {"name": "Light Gray","code": "LGR","rgb": (160, 160, 159)},
    {"name": "Tan", "code": "TAN", "rgb": (215, 197, 153)},
    {"name": "Brown","code": "BRN","rgb": (124, 92, 70)},
    # add more as needed
]

def get_rgb_palette() -> List[Tuple[int,int,int]]:
    return [tuple(entry["rgb"]) for entry in LEGO_PALETTE]

def get_palette_metadata():
    return LEGO_PALETTE

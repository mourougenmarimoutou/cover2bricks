# palette.py
# English comments: Load LEGO color palette from colors.csv (value, children, rgb)

import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).parent / "colorspalette.csv"

def load_palette():
    """Load LEGO colors from CSV (columns: value, children, rgb)."""
    df = pd.read_csv(CSV_PATH, sep=",") 
    # Normalize column names (strip spaces, lowercase)
    df.columns = [c.strip().lower() for c in df.columns]
    # Convert hex string (#RRGGBB) to RGB tuple
    df["rgb_tuple"] = df["rgb"].apply(
        lambda h: tuple(int(h.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    )
    return df

def get_rgb_palette():
    """Return list of RGB tuples [(r,g,b), ...] for all colors."""
    df = load_palette()
    return df["rgb_tuple"].tolist()

def get_palette_metadata():
    """Return list of dicts with color metadata (value, name, rgb)."""
    df = load_palette()
    return [
        {
            "code": int(row["value"]),
            "name": row["children"],
            "rgb": row["rgb_tuple"]
        }
        for _, row in df.iterrows()
    ]

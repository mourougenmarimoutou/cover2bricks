# Image processing utilities for LEGO mosaic conversion

from io import BytesIO
from typing import Tuple, List, Dict, Optional
import numpy as np
from PIL import Image
from skimage import color
from palette import get_rgb_palette, get_palette_metadata

def pil_to_np(img: Image.Image) -> np.ndarray:
    """Convert PIL image to numpy RGB array."""
    return np.array(img.convert("RGB"))

def np_to_pil(arr: np.ndarray) -> Image.Image:
    """Convert numpy RGB array to PIL image."""
    return Image.fromarray(arr.astype(np.uint8))

def rgb_palette_to_lab(palette_rgb: List[Tuple[int,int,int]]) -> np.ndarray:
    """Convert RGB palette to LAB colorspace."""
    arr = np.array(palette_rgb, dtype=np.uint8).reshape((-1,1,3))
    arr = arr.astype(np.float64) / 255.0
    lab = color.rgb2lab(arr)
    return lab.reshape((-1,3))

def image_to_brick_matrix(
    img: Image.Image,
    bricks: int = 32,
    crop_box: Optional[Tuple[int,int,int,int]] = None
) -> np.ndarray:
    """
    Convert image to brick matrix with averaged colors.
    Returns: array (bricks x bricks x 3) of RGB values
    """
    if crop_box:
        img = img.crop(crop_box)

    # Make square by center-cropping
    w, h = img.size
    if w != h:
        side = min(w,h)
        left = (w - side)//2
        upper = (h - side)//2
        img = img.crop((left, upper, left+side, upper+side))
    
    small = img.resize((bricks, bricks), resample=Image.LANCZOS)
    return pil_to_np(small).astype(np.uint8)

def map_to_palette(
    matrix_rgb: np.ndarray,
    palette_rgb: List[Tuple[int,int,int]]
) -> Tuple[np.ndarray, List[Dict]]:
    """
    Map matrix colors to nearest palette colors using LAB distance.
    Returns: (mapped matrix, color counts)
    """
    h, w, _ = matrix_rgb.shape
    img_flat = matrix_rgb.reshape((-1,3)).astype(np.float64) / 255.0
    lab_img = color.rgb2lab(img_flat.reshape((-1,1,3))).reshape((-1,3))
    lab_palette = rgb_palette_to_lab(palette_rgb)

    distances = np.linalg.norm(lab_img[:, None, :] - lab_palette[None, :, :], axis=2)
    idx = np.argmin(distances, axis=1)
    mapped_flat = np.array(palette_rgb, dtype=np.uint8)[idx]
    mapped = mapped_flat.reshape((h,w,3))

    unique, counts = np.unique(idx, return_counts=True)
    palette_metadata = get_palette_metadata()
    counts_list = []
    for i, p in enumerate(palette_metadata):
        cnt = int(counts[unique.tolist().index(i)]) if i in unique else 0
        counts_list.append({ "index": i, "code": p["code"], "name": p["name"], "rgb": p["rgb"], "count": cnt })
    return mapped.astype(np.uint8), counts_list

def expand_mosaic(mapped_matrix: np.ndarray, cell_size: int = 16) -> Image.Image:
    """Expand brick matrix for visualization."""
    h, w, _ = mapped_matrix.shape
    big = np.repeat(np.repeat(mapped_matrix, cell_size, axis=0), cell_size, axis=1)
    return np_to_pil(big)

def pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    """Convert PIL image to bytes in specified format."""
    bio = BytesIO()
    img.save(bio, format=fmt)
    return bio.getvalue()

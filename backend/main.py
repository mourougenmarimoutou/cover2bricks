# FastAPI app for converting images to LEGO mosaics

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from PIL import Image
import io

from utils import image_to_brick_matrix, map_to_palette, expand_mosaic, pil_to_bytes
from palette import get_rgb_palette, get_palette_metadata

app = FastAPI(title="LEGO Vinyl Cover API")

# Square plate size in bricks
DEFAULT_BRICKS = 32

# CORS config for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/convert")
async def convert(
    file: UploadFile = File(...),
    bricks: int = Form(DEFAULT_BRICKS),
    crop_left: Optional[int] = Form(None),
    crop_top: Optional[int] = Form(None),
    crop_right: Optional[int] = Form(None),
    crop_bottom: Optional[int] = Form(None),
    cell_size: int = Form(16)  # pixels per brick for visualization
):
    """
    Convert image to LEGO mosaic and return matrix info.
    """
    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    crop_box = None
    if None not in (crop_left, crop_top, crop_right, crop_bottom):
        crop_box = (crop_left, crop_top, crop_right, crop_bottom)

    # 1) create brick matrix (averaged colors per brick)
    matrix_rgb = image_to_brick_matrix(img, bricks=bricks, crop_box=crop_box)

    # 2) map to palette
    palette_rgb = get_rgb_palette()
    mapped, counts = map_to_palette(matrix_rgb, palette_rgb)

    # 3) expanded visualization image
    vis_img = expand_mosaic(mapped, cell_size=cell_size)
    png_bytes = pil_to_bytes(vis_img, fmt="PNG")

    # prepare JSON with counts and matrix codes
    # convert mapped matrix to palette index matrix
    # We will recompute indices by matching rgb to palette entries (simple)
    # Build mapping dict
    palette_map = {tuple(rgb): idx for idx, rgb in enumerate(palette_rgb)}
    h,w,_ = mapped.shape
    matrix_indices = [[int(palette_map[tuple(mapped[y,x])]) for x in range(w)] for y in range(h)]

    metadata = get_palette_metadata()
    return JSONResponse(
        content={
            "image_png_base64": None,  # large; client should request /convert/png if needed
            "matrix": matrix_indices,
            "counts": counts,
            "palette": metadata,
            "info": {
                "bricks": bricks, "cell_size": cell_size
            }
        },
        headers={"X-Image-PNG": "use /convert/png or get via another endpoint if needed"},
        status_code=200
    )

@app.post("/convert/png")
async def convert_png(
    file: UploadFile = File(...),
    bricks: int = Form(DEFAULT_BRICKS),
    crop_left: Optional[int] = Form(None),
    crop_top: Optional[int] = Form(None),
    crop_right: Optional[int] = Form(None),
    crop_bottom: Optional[int] = Form(None),
    cell_size: int = Form(16)
):
    """Return mosaic preview as PNG."""
    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    crop_box = None
    if None not in (crop_left, crop_top, crop_right, crop_bottom):
        crop_box = (crop_left, crop_top, crop_right, crop_bottom)

    matrix_rgb = image_to_brick_matrix(img, bricks=bricks, crop_box=crop_box)
    palette_rgb = get_rgb_palette()
    mapped, counts = map_to_palette(matrix_rgb, palette_rgb)
    vis_img = expand_mosaic(mapped, cell_size=cell_size)
    png_bytes = pil_to_bytes(vis_img, fmt="PNG")
    return Response(content=png_bytes, media_type="image/png")

# Simple PDF generator endpoint
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

@app.post("/convert/pdf")
async def convert_pdf(
    file: UploadFile = File(...),
    bricks: int = Form(DEFAULT_BRICKS),
    crop_left: Optional[int] = Form(None),
    crop_top: Optional[int] = Form(None),
    crop_right: Optional[int] = Form(None),
    crop_bottom: Optional[int] = Form(None),
    cell_size_mm: float = Form(7.0)  # mm per brick on PDF plan (adjustable)
):
    """Generate PDF build instructions."""
    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    crop_box = None
    if None not in (crop_left, crop_top, crop_right, crop_bottom):
        crop_box = (crop_left, crop_top, crop_right, crop_bottom)

    matrix_rgb = image_to_brick_matrix(img, bricks=bricks, crop_box=crop_box)
    palette_rgb = get_rgb_palette()
    mapped, counts = map_to_palette(matrix_rgb, palette_rgb)

    # Create PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, height - 20*mm, "LEGO Vinyl Cover - Build Plan")

    # small visualization image (top-right)
    vis_img = expand_mosaic(mapped, cell_size=6)
    img_pil = vis_img.convert("RGB")
    c.drawInlineImage(img_pil, width - 90*mm, height - 80*mm, 60*mm, 60*mm)

    # Brick counts table
    c.setFont("Helvetica", 10)
    y = height - 35*mm
    c.drawString(20*mm, y, "Brick counts:")
    y -= 6*mm
    for entry in counts:
        name = entry["name"]
        code = entry["code"]
        cnt = entry["count"]
        rgb = entry["rgb"]
        # draw color square
        try:
            c.setFillColor(colors.Color(rgb[0]/255, rgb[1]/255, rgb[2]/255))
        except:
            c.setFillColor(colors.black)
        c.rect(20*mm, y - 3*mm, 4*mm, 4*mm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.drawString(26*mm, y, f"{code} - {name}: {cnt}")
        y -= 6*mm
        if y < 30*mm:
            c.showPage()
            y = height - 20*mm

    # Add grid plan (each brick represented by its code)
    c.showPage()
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, height - 20*mm, f"Grid plan ({bricks}x{bricks}) - each cell approx {cell_size_mm} mm")
    # draw grid starting at (20mm, height - 30mm)
    start_x = 20*mm
    start_y = height - 30*mm
    cell_mm = cell_size_mm * mm
    # limit page overflow: if too big, scale down cell_mm
    max_cells_per_row = int((width - 40*mm) // cell_mm)
    if max_cells_per_row < bricks:
        scale = (width - 40*mm) / (bricks * cell_mm)
        cell_mm = cell_mm * scale

    for ry in range(bricks):
        for rx in range(bricks):
            rgb = tuple(mapped[ry, rx])
            # find palette index by rgb match
            # draw rect filled with palette color and code text
            c.setFillColor(colors.Color(rgb[0]/255, rgb[1]/255, rgb[2]/255))
            x = start_x + rx * cell_mm
            y_cell = start_y - ry * cell_mm
            c.rect(x, y_cell - cell_mm, cell_mm, cell_mm, fill=1, stroke=0)
    c.save()
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type="application/pdf")

# FastAPI app for converting images to LEGO mosaics
# 'python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000' to run

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from PIL import Image
import io
import csv 
from utils import image_to_brick_matrix, map_to_palette, expand_mosaic, pil_to_bytes
from palette import get_rgb_palette, get_palette_metadata

app = FastAPI(title="LEGO Vinyl Cover API")

# Square plate size in bricks
DEFAULT_BRICKS = 32  # inchangé mais on va l'utiliser différemment

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
    bricks: int = Form(DEFAULT_BRICKS),  # maintenant accepte 32 ou 64
    crop_left: Optional[int] = Form(None),
    crop_top: Optional[int] = Form(None),
    crop_right: Optional[int] = Form(None),
    crop_bottom: Optional[int] = Form(None),
    cell_size: int = Form(24)  # changé à 24 par défaut
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
    cell_size_mm: float = Form(7.0),  # mm per brick on PDF plan (adjustable)
    include_csv: bool = Form(False)    # if true, return a ZIP with PDF + CSV
):
    """Generate PDF build instructions. If include_csv is True, return a ZIP with PDF + brick CSV."""
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
    
    # Add size information
    c.setFont("Helvetica", 12)
    size_info = "(~25x25 cm)" if bricks == 32 else "(~50x50 cm)"
    c.drawString(20*mm, height - 30*mm, f"Size: {bricks}x{bricks} bricks {size_info}")

    # Continue with visualization image
    vis_img = expand_mosaic(mapped, cell_size=6)
    img_pil = vis_img.convert("RGB")
    c.drawInlineImage(img_pil, width - 90*mm, height - 80*mm, 60*mm, 60*mm)

    # Ajouter la/les base plate(s) aux counts
    base_plate = {
        "name": "Base Plate 32 x 32",
        "code": "6061048",
        "count": 4 if bricks == 64 else 1,
        "rgb": (128, 128, 128)  # gris par défaut pour la visualisation
    }
    
    # Filter counts to non-zero entries only
    counts_non_zero = [e for e in counts if int(e.get("count", 0)) > 0]
    counts_non_zero.append(base_plate)

    # Brick counts table (only non-zero)
    c.setFont("Helvetica", 10)
    y = height - 35*mm
    c.drawString(20*mm, y, "Brick counts:")
    y -= 6*mm
    if not counts_non_zero:
        c.drawString(20*mm, y, "No bricks required.")
        y -= 6*mm
    else:
        for entry in counts_non_zero:
            name = entry.get("name", "")
            code = entry.get("code", "")
            cnt = entry.get("count", 0)
            rgb = entry.get("rgb", (0,0,0))
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

    # Add grid plan with cell borders
    c.showPage()
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, height - 20*mm, f"Grid plan ({bricks}x{bricks}) - each cell approx {cell_size_mm} mm")
    
    start_x = 20*mm
    start_y = height - 30*mm
    cell_mm = cell_size_mm * mm
    
    # limit page overflow: if too big, scale down cell_mm
    max_cells_per_row = int((width - 40*mm) // cell_mm)
    if max_cells_per_row < bricks:
        scale = (width - 40*mm) / (bricks * cell_mm)
        cell_mm = cell_mm * scale

    # Draw colored cells and grid
    for ry in range(bricks):
        for rx in range(bricks):
            rgb = tuple(mapped[ry, rx])
            x = start_x + rx * cell_mm
            y_cell = start_y - ry * cell_mm
            
            # Fill cell with color
            c.setFillColor(colors.Color(rgb[0]/255, rgb[1]/255, rgb[2]/255))
            c.rect(x, y_cell - cell_mm, cell_mm, cell_mm, fill=1, stroke=0)
            
            # Draw cell border
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.1)  # fin trait pour la grille
            c.rect(x, y_cell - cell_mm, cell_mm, cell_mm, fill=0, stroke=1)

    # Draw thicker lines every 8 cells for better readability
    c.setLineWidth(0.5)  # trait plus épais pour les sections
    for i in range(0, bricks + 1, 8):
        # Vertical lines
        x = start_x + i * cell_mm
        c.line(x, start_y, x, start_y - bricks * cell_mm)
        # Horizontal lines
        y = start_y - i * cell_mm
        c.line(start_x, y, start_x + bricks * cell_mm, y)

    c.save()
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()

    if not include_csv:
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=build_plan.pdf"},
        )

    # build CSV (elementId = code, quantity = count) only for non-zero counts
    import csv, zipfile
    csv_out = io.StringIO()
    writer = csv.writer(csv_out)
    writer.writerow(["elementId", "quantity"])
    for entry in counts_non_zero:
        writer.writerow([entry.get("code"), int(entry.get("count", 0))])
    csv_bytes = csv_out.getvalue().encode("utf-8")

    # pack PDF + CSV into a ZIP
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("build_plan.pdf", pdf_bytes)
        zf.writestr("brick_list.csv", csv_bytes)
    zip_buf.seek(0)

    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=build_plan_and_brick_list.zip"},
    )

@app.post("/convert/bricks.csv")
async def export_brick_list_csv(
    file: UploadFile = File(...),
    bricks: int = Form(DEFAULT_BRICKS),
    crop_left: Optional[int] = Form(None),
    crop_top: Optional[int] = Form(None),
    crop_right: Optional[int] = Form(None),
    crop_bottom: Optional[int] = Form(None),
):
    """
    Export CSV with columns: elementId,quantity for non-zero brick counts.
    """
    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    crop_box = None
    if None not in (crop_left, crop_top, crop_right, crop_bottom):
        crop_box = (crop_left, crop_top, crop_right, crop_bottom)

    matrix_rgb = image_to_brick_matrix(img, bricks=bricks, crop_box=crop_box)
    palette_rgb = get_rgb_palette()
    _, counts = map_to_palette(matrix_rgb, palette_rgb)

    # Ajouter la/les base plate(s)
    base_plate = {
        "code": "6061048",
        "count": 4 if bricks == 64 else 1
    }
    
    # Filtrer les counts non-zero et ajouter la base plate
    counts_non_zero = [e for e in counts if int(e.get("count", 0)) > 0]
    counts_non_zero.append(base_plate)

    # Générer le CSV
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["elementId", "quantity"])
    for entry in counts_non_zero:
        writer.writerow([entry.get("code"), int(entry.get("count", 0))])

    csv_bytes = out.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=brick_list.csv"},
    )

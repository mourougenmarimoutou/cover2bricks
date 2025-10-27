# Cover2Bricks

A web application that converts vinyl cover images or regular images into LEGO mosaic building instructions.

## Features

- Upload and crop images
- Convert images to LEGO-compatible colors
- Generate building instructions in PDF format
- Export brick parts list in CSV format
- Support for 32x32 bricks (~25x25 cm) and 64x64 bricks (~50x50 cm) builds
- Real-time preview of the mosaic

## Technical Requirements

### Backend
- Python 3.8+
- FastAPI
- Pillow
- ReportLab
- uvicorn

### Frontend
- Node.js 16+
- Vue 3
- TypeScript
- Cropper.js

## Quick Start

1. Start the backend:
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

2. Start the frontend:
```bash
cd frontend
npm install
npm run dev
```

3. Open http://localhost:5173 in your browser

There is live preview but you can use the `Generate PNG preview` button if needed.  
You **need** to press `Generate PDF plan` in order to get the building instructions and the parts list csv generated.

## Output Files

- **PDF**: Building instructions with color grid and parts list
- **CSV**: Parts list compatible with BrickLink/LEGO ordering systems

The PDF file can be downloaded on its own or in a zip file with the parts list file.



## TODO

[ ] Automatic addition of 1x2 bricks to connect the 32x32 plates together

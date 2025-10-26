<script setup lang="ts">
// English comments: main app to upload, crop, and submit to FastAPI backend.
// Now includes real-time preview using debounce.

import { ref } from 'vue'
import Cropper from 'cropperjs'
import debounce from 'lodash.debounce'

const fileInput = ref<HTMLInputElement | null>(null)
const imgEl = ref<HTMLImageElement | null>(null)
let cropper: Cropper | null = null

const backendUrl = 'http://127.0.0.1:8000'

const bricks = ref(32)
const cellSize = ref(12)

const resultPngUrl = ref<string | null>(null)
const pdfBlobUrl = ref<string | null>(null)
const loading = ref(false)

/**
 * Send current cropped image to backend and update PNG preview in real time.
 * Debounced to avoid too many requests.
 */
const updatePreview = debounce(async () => {
  if (!cropper) return
  const canvas = cropper.getCroppedCanvas()
  if (!canvas) return

  const blob = await new Promise<Blob | null>(res => canvas.toBlob(b => res(b), 'image/png'))
  if (!blob) return

  const form = new FormData()
  form.append('file', blob, 'cropped.png')
  form.append('bricks', String(bricks.value))
  form.append('cell_size', String(cellSize.value))

  loading.value = true
  try {
    const resp = await fetch(`${backendUrl}/convert/png`, { method: 'POST', body: form })
    console.log('Réponse du serveur:', resp.status)
    if (resp.ok) {
      const blobResp = await resp.blob()
      if (resultPngUrl.value) URL.revokeObjectURL(resultPngUrl.value)
      resultPngUrl.value = URL.createObjectURL(blobResp)
      console.log('Nouvelle URL générée:', resultPngUrl.value)
    } else {
      console.error('Backend returned non-ok:', resp.status, resp.statusText)
    }
  } catch (error) {
    console.error('Erreur fetch:', error)
  } finally {
    loading.value = false
  }
}, 400)

/**
 * Handle file upload and initialize cropper.
 */
function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const f = target.files?.[0]
  if (!f) return
  const url = URL.createObjectURL(f)

  if (imgEl.value) {
    imgEl.value.src = url
    if (cropper) cropper.destroy()
    imgEl.value.onload = () => {
      cropper = new Cropper(imgEl.value as HTMLImageElement, {
        aspectRatio: 1,
        viewMode: 1,
        autoCropArea: 1,
        crop: () => updatePreview(), // auto-update preview when cropping
      })
    }
  }
}

/**
 * Generate PNG manually (button action, same endpoint as live preview).
 */
async function submitForPng() {
  if (!cropper) {
    alert('Please upload and crop an image first.')
    return
  }

  const canvas = cropper.getCroppedCanvas()
  if (!canvas) return
  const blob = await new Promise<Blob | null>(res => canvas.toBlob(b => res(b), 'image/png'))
  if (!blob) return

  const form = new FormData()
  form.append('file', blob, 'cropped.png')
  form.append('bricks', String(bricks.value))
  form.append('cell_size', String(cellSize.value))

  const resp = await fetch(`${backendUrl}/convert/png`, { method: 'POST', body: form })
  if (!resp.ok) {
    alert('Error from backend: ' + resp.statusText)
    return
  }
  const blobResp = await resp.blob()
  if (resultPngUrl.value) URL.revokeObjectURL(resultPngUrl.value)
  resultPngUrl.value = URL.createObjectURL(blobResp)
}

/**
 * Generate a PDF instruction plan from the cropped image.
 */
async function requestPdf() {
  if (!cropper) {
    alert('Please upload and crop an image first.')
    return
  }
  const canvas = cropper.getCroppedCanvas()
  if (!canvas) return
  const blob = await new Promise<Blob | null>(res => canvas.toBlob(b => res(b), 'image/png'))
  if (!blob) return

  const form = new FormData()
  form.append('file', blob, 'cropped.png')
  form.append('bricks', String(bricks.value))
  form.append('cell_size_mm', String(7.0))

  const resp = await fetch(`${backendUrl}/convert/pdf`, { method: 'POST', body: form })
  if (!resp.ok) {
    alert('Error from backend: ' + resp.statusText)
    return
  }
  const blobResp = await resp.blob()
  if (pdfBlobUrl.value) URL.revokeObjectURL(pdfBlobUrl.value)
  pdfBlobUrl.value = URL.createObjectURL(blobResp)
}
</script>

<template>
  <div class="container">
    <h1>LEGO Vinyl Cover - Live Preview</h1>

    <!-- Controls section -->
    <section class="controls">
      <label>Upload image:
        <input type="file" accept="image/*" @change="onFileChange" ref="fileInput" />
      </label>
      <div class="input-group">
        <label>Bricks per side:
          <input type="number" v-model.number="bricks" min="8" max="128" />
        </label>
        <label>Cell size (preview px):
          <input type="number" v-model.number="cellSize" min="4" max="64" />
        </label>
      </div>
      <div class="actions">
        <button @click="submitForPng">Generate PNG preview</button>
        <button @click="requestPdf">Generate PDF plan</button>
      </div>
    </section>

    <!-- Main content section -->
    <section class="main-content">
      <!-- Crop area -->
      <div class="crop-container">
        <h3>Crop (square)</h3>
        <div class="crop-area">
          <img ref="imgEl" />
        </div>
      </div>

      <!-- Preview area -->
      <div class="preview-container">
        <div v-if="loading">Generating preview...</div>
        <template v-if="resultPngUrl && !loading">
          <h3>Preview</h3>
          <div class="preview-area">
            <img :src="resultPngUrl" />
          </div>
          <div class="download-link">
            <a :href="resultPngUrl" download="lego_preview.png">Download PNG</a>
          </div>
        </template>
      </div>
    </section>

    <!-- PDF section -->
    <section v-if="pdfBlobUrl && !loading" class="pdf-section">
      <h3>PDF Plan</h3>
      <div class="pdf-actions">
        <a :href="pdfBlobUrl" download="lego_plan.pdf" class="download-btn">
          Download PDF
        </a>
      </div>
      <div class="pdf-preview">
        <embed
          :src="pdfBlobUrl"
          type="application/pdf"
          width="100%"
          height="100%"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.container {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 20px;
  font-family: Arial, Helvetica, sans-serif;
}

.controls {
  margin-bottom: 24px;
}

.input-group {
  margin-top: 12px;
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.actions {
  margin-top: 12px;
}

.main-content {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.crop-container, .preview-container {
  flex: 1;
  min-width: 300px;
}

.crop-area, .preview-area {
  width: 100%;
  aspect-ratio: 1;
  border: 1px solid #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}

.crop-area img, .preview-area img {
  max-width: 100%;
  max-height: 100%;
  display: block;
}

.pdf-section {
  border-top: 1px solid #eee;
  padding-top: 24px;
}

.pdf-actions {
  margin-bottom: 16px;
  text-align: center;
}

.pdf-preview {
  height: 500px;
  border: 1px solid #ccc;
}

button {
  padding: 8px 16px;
  cursor: pointer;
  margin-right: 10px;
}

.download-btn {
  display: inline-block;
  padding: 8px 16px;
  background: #4CAF50;
  color: white;
  text-decoration: none;
  border-radius: 4px;
}

.download-link {
  margin-top: 8px;
  text-align: center;
}

@media (max-width: 768px) {
  .main-content {
    flex-direction: column;
  }
  
  .crop-container, .preview-container {
    width: 100%;
  }
}
</style>

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import CapturePayload
from .mediapipe_worker import extract_landmarks_from_frame
from .utils import process_landmarks
import base64, cv2, numpy as np
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import logging
from fastapi.responses import JSONResponse

app = FastAPI()

FRONT_DIR = Path(__file__).resolve().parents[2] / "front"

# Servir archivos estáticos del frontend desde la raíz
# Esto permitirá que requests a /styles.css y /app.js funcionen
app.mount("/static", StaticFiles(directory=str(FRONT_DIR), html=True), name="front")

# Habilitar CORS para que el frontend pueda comunicarse
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/", response_class=HTMLResponse)
def root():
    with open("front/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.post("/extract")
async def extract(payload: CapturePayload):
    # Si vienen landmarks directamente -> normalizar y responder
    if payload.landmarks:
        try:
            # Intentar convertir modelos pydantic a estructuras nativas (dicts) si es necesario
            landmarks = [lm.dict() if hasattr(lm, 'dict') else lm for lm in payload.landmarks]
            pose_anchors = payload.pose_anchors.dict() if payload.pose_anchors and hasattr(payload.pose_anchors, 'dict') else payload.pose_anchors
            # normalización luego...
            features = process_landmarks(landmarks, pose_anchors)
            return {"status": "OK", "features": features}
        except Exception as e:
            logging.exception('Error procesando landmarks')
            # Devolver un error JSON claro al cliente
            return JSONResponse(status_code=500, content={"status": "ERROR", "detail": str(e)})

    # si se recibe frame (campo base64_frame) -> convertir y procesar
    raise HTTPException(status_code=400, detail="No landmarks provided")

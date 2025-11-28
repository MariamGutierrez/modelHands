# API & Project Specification

This document describes the endpoints, payload formats, data flow and running instructions for the project located at the repository root

## Overview

- Frontend: `front/` — static web UI that captures camera video, runs MediaPipe Hands in the browser (via `hands.js` + `camera_utils.js`) and sends detected landmarks to the backend.
- Backend: `back/` — FastAPI server exposing an `/extract` endpoint that processes landmarks into features (normalized landmarks, finger angles, palm normal, centroid).

This spec covers:
- API endpoints and request/response shapes
- Frontend→Backend integration contract
- How to run locally
- Notes about common runtime issues and debugging tips

---

## API endpoints

### POST /extract

Description: Accepts detected landmarks (from the client) and returns processed features (normalization, angles, palm normal, centroid). The endpoint also returns structured error information when processing fails.

Request Content-Type: `application/json`

Request body (JSON) - `CapturePayload`:

- sign_id: string — unique id for capture (example: `sign_163...`)
- type: string — e.g. `hand`
- device_id: string — device source e.g. `web_camera`
- timestamp: string (ISO 8601)
- landmarks: array of landmarks (optional if you plan to send frames instead)
- pose_anchors: object with anchor points (optional)

Landmark object (each element in `landmarks`):

- id: int
- x: float  (normalized 0..1 in MediaPipe coordinates)
- y: float  (normalized 0..1)
- z: float  (relative depth, can be small or missing — backend tolerates missing z)
- visibility: float (0..1)

Example payload:

{
	"sign_id": "sign_1764344190558",
	"type": "hand",
	"device_id": "web_camera",
	"timestamp": "2025-11-28T15:36:30.558Z",
	"landmarks": [
		{"id":0,"x":0.67,"y":0.53,"z":-0.00000058,"visibility":1},
		... (21 items) ...
	],
	"pose_anchors": {
		"nose": {"x":0.67, "y":0.53},
		"left_shoulder": {"x":0.53, "y":0.28},
		"right_shoulder": {"x":0.55, "y":0.33}
	}
}

Successful response (200 OK):

{
	"status": "OK",
	"features": {
		"landmarks_norm": [[...], ...],
		"angles": [/* five angles in degrees */],
		"palm_normal": [nx, ny, nz],
		"centroid": {"x":..., "y":..., "z":...}
	}
}

Error response (example 400/500):

{
	"status": "ERROR",
	"detail": "Error message or stack snippet"
}

Notes:
- The backend expects landmarks as a list of objects; the server converts Pydantic models to plain dicts and is tolerant to missing `z` values.
- The backend currently only accepts landmarks in this endpoint. There is a Python helper `mediapipe_worker.py` that can extract landmarks from an image frame (server-side) if you want to extend the API to accept base64 frames.

---

## Data flow and processing (high level)

1. Frontend captures camera video and runs MediaPipe Hands in the browser using `hands.js`.
2. For each frame MediaPipe produces `multiHandLandmarks`. The frontend collects landmarks (id,x,y,z,visibility) and a few pose anchors (nose and approximated shoulder points) and draws the results on a `canvas` overlay.
3. On user action ("Enviar landmarks"), frontend sends `CapturePayload` JSON to the backend `/extract` endpoint.
4. Backend code (`back/app/utils.py`) receives the list:
	 - `to_np(...)` converts landmarks to Nx3 NumPy array (x,y,z). This function is robust: accepts dicts or pydantic objects and fills missing z with 0.0.
	 - `normalize_landmarks(...)` normalizes coordinates either anthropometrically (using shoulder distance if available) or by centroid+scale.
	 - compute finger angles (MCP-PIP-DIP) for index/middle/ring/pinky/thumb
	 - compute palm normal (cross product of vectors defined by wrist/index/pinky)
	 - compute centroid
5. Server returns features JSON.

---

## Files of interest (brief)

- `front/index.html` — UI, loads MediaPipe scripts (tries `/static/vendor/mediapipe/*` first), includes the status indicator, video and canvas.
- `front/app.js` — main client logic: initializes MediaPipe, handles camera (Camera API with getUserMedia fallback), draws landmarks, builds and sends payloads.
- `front/styles.css` — UI styles and status indicator styles.
- `back/app/main.py` — FastAPI app, static files mounting at `/static`, CORS enabled (dev), endpoint `/extract`.
- `back/app/schemas.py` — Pydantic models (validation).
- `back/app/utils.py` — core processing: `to_np`, normalization, angle calc, palm normal, `process_landmarks`.
- `back/app/mediapipe_worker.py` — helper to extract landmarks from an image frame using MediaPipe in Python (useful if server-side frame processing is desired).

---

## How to run locally

1. Create and activate a Python virtual environment and install required packages. Example (Windows PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install fastapi uvicorn numpy opencv-python mediapipe pydantic
```

2. Start the backend server (from repository root):

```powershell
uvicorn back.app.main:app --reload --host 127.0.0.1 --port 8000
```

3. Open the frontend in your browser:

- Visit: `http://127.0.0.1:8000/` — the server serves `front/index.html` and static assets are available under `/static/`.

4. Allow camera access. The page will run MediaPipe in the browser. Press "Enviar landmarks" to send data to the server.

Notes:
- It's recommended to download the MediaPipe JS files (`camera_utils.js`, `drawing_utils.js`, `hands.js`) into `front/vendor/mediapipe/` and serve them from `/static/vendor/mediapipe/` to avoid browser Tracking Prevention warnings when loading from CDN.

---

## Debugging notes & common issues

- 405 Method Not Allowed when POSTing to `/extract` — cause: static files were mounted at root `/` and intercepted API routes (fixed: static now mounted at `/static`).
- ReferenceError: `Hands` / `FilesetResolver` — cause: mixing MediaPipe Tasks API with classic `hands.js` API. Fix: use the classic `Hands` API (as implemented in `front/app.js`).
- CORS / origin mismatch (`localhost` vs `127.0.0.1`) — set `BACKEND_URL` in the client to `window.location.origin` or ensure same origin. Backend sets CORS with `allow_origins=["*"]` for development.
- Tracking Prevention warnings for cdn.jsdelivr.net — download vendor files and serve them from your origin to reduce these warnings.
- TypeError 'Landmark' object is not subscriptable — cause: backend tried to index Pydantic model instances as dicts; fixed by converting models to dicts and making `to_np` robust.
- KeyError 'z' — cause: some pose anchors included only x,y (no z). `normalize_landmarks` now accepts missing z (defaults to 0.0) and falls back to centroid normalization if key anchors lack x/y.

---

## Suggested next improvements

1. Frontend validation: ensure each landmark has `x` and `y` before sending; set `z` to 0.0 if missing and require 21 landmarks (or warn otherwise).
2. Add a small `scripts/download_mediapipe.ps1` to fetch the three MediaPipe JS files into `front/vendor/mediapipe`.
3. Add unit tests for `back/app/utils.py::process_landmarks` with synthetic landmark sets (normal case, missing fields, single-hand/no-hand edge cases).
4. In production, restrict CORS origins and serve static files via a proper web server; pin dependency versions in `requirements.txt`.



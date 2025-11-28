# Especificación de API y Proyecto

Este documento describe los endpoints, formatos de carga útil, flujo de datos e instrucciones de ejecución para el proyecto ubicado en la raíz del repositorio

## Descripción General

- Frontend: `front/` — interfaz web estática que captura video de la cámara, ejecuta MediaPipe Hands en el navegador (a través de `hands.js` + `camera_utils.js`) y envía los puntos de referencia detectados al backend.
- Backend: `back/` — servidor FastAPI que expone un endpoint `/extract` que procesa los puntos de referencia en características (puntos de referencia normalizados, ángulos de dedos, normal de palma, centroide).

Esta especificación cubre:
- Endpoints de API y formas de solicitud/respuesta
- Contrato de integración Frontend→Backend
- Cómo ejecutar localmente
- Notas sobre problemas comunes en tiempo de ejecución y consejos de depuración

---

## Endpoints de API

### POST /extract

Descripción: Acepta puntos de referencia detectados (del cliente) y devuelve características procesadas (normalización, ángulos, normal de palma, centroide). El endpoint también devuelve información de error estructurada cuando el procesamiento falla.

Content-Type de Solicitud: `application/json`

Cuerpo de la solicitud (JSON) - `CapturePayload`:

- sign_id: string — identificador único para la captura (ejemplo: `sign_163...`)
- type: string — por ejemplo, `hand`
- device_id: string — fuente del dispositivo, por ejemplo, `web_camera`
- timestamp: string (ISO 8601)
- landmarks: array de puntos de referencia (opcional si planea enviar frames en su lugar)
- pose_anchors: objeto con puntos de anclaje (opcional)

Objeto Landmark (cada elemento en `landmarks`):

- id: int
- x: float  (normalizado 0..1 en coordenadas de MediaPipe)
- y: float  (normalizado 0..1)
- z: float  (profundidad relativa, puede ser pequeño o faltar — el backend tolera z faltante)
- visibility: float (0..1)

Carga útil de ejemplo:

{
	"sign_id": "sign_1764344190558",
	"type": "hand",
	"device_id": "web_camera",
	"timestamp": "2025-11-28T15:36:30.558Z",
	"landmarks": [
		{"id":0,"x":0.67,"y":0.53,"z":-0.00000058,"visibility":1},
		... (21 elementos) ...
	],
	"pose_anchors": {
		"nose": {"x":0.67, "y":0.53},
		"left_shoulder": {"x":0.53, "y":0.28},
		"right_shoulder": {"x":0.55, "y":0.33}
	}
}

Respuesta exitosa (200 OK):

{
	"status": "OK",
	"features": {
		"landmarks_norm": [[...], ...],
		"angles": [/* cinco ángulos en grados */],
		"palm_normal": [nx, ny, nz],
		"centroid": {"x":..., "y":..., "z":...}
	}
}

Respuesta de error (ejemplo 400/500):

{
	"status": "ERROR",
	"detail": "Mensaje de error o fragmento de pila"
}

Notas:
- El backend espera puntos de referencia como una lista de objetos; el servidor convierte modelos Pydantic a dicts simples y es tolerante con valores `z` faltantes.
- El backend actualmente solo acepta puntos de referencia en este endpoint. Hay un asistente de Python `mediapipe_worker.py` que puede extraer puntos de referencia de un frame de imagen (del lado del servidor) si desea ampliar la API para aceptar frames codificados en base64.

---

## Flujo de datos y procesamiento (nivel alto)

1. El frontend captura video de la cámara y ejecuta MediaPipe Hands en el navegador usando `hands.js`.
2. Para cada frame, MediaPipe produce `multiHandLandmarks`. El frontend recopila puntos de referencia (id, x, y, z, visibility) y algunos puntos de anclaje de pose (nariz y puntos de hombro aproximados) y dibuja los resultados en una superposición `canvas`.
3. En la acción del usuario ("Enviar landmarks"), el frontend envía JSON `CapturePayload` al endpoint `/extract` del backend.
4. Código del backend (`back/app/utils.py`) recibe la lista:
	 - `to_np(...)` convierte puntos de referencia a un array NumPy Nx3 (x, y, z). Esta función es robusta: acepta dicts u objetos pydantic y completa z faltante con 0.0.
	 - `normalize_landmarks(...)` normaliza coordenadas ya sea antropométricamente (usando distancia de hombro si está disponible) o por centroide+escala.
	 - calcula ángulos de dedos (MCP-PIP-DIP) para índice/medio/anular/meñique/pulgar
	 - calcula normal de palma (producto cruzado de vectores definidos por muñeca/índice/meñique)
	 - calcula centroide
5. El servidor devuelve JSON de características.

---

## Archivos de interés (breve)

- `front/index.html` — interfaz de usuario, carga scripts de MediaPipe (intenta `/static/vendor/mediapipe/*` primero), incluye el indicador de estado, video y canvas.
- `front/app.js` — lógica principal del cliente: inicializa MediaPipe, maneja la cámara (Camera API con fallback getUserMedia), dibuja puntos de referencia, construye y envía cargas útiles.
- `front/styles.css` — estilos de interfaz de usuario e indicador de estado.
- `back/app/main.py` — aplicación FastAPI, montaje de archivos estáticos en `/static`, CORS habilitado (desarrollo), endpoint `/extract`.
- `back/app/schemas.py` — modelos Pydantic (validación).
- `back/app/utils.py` — procesamiento principal: `to_np`, normalización, cálculo de ángulos, normal de palma, `process_landmarks`.
- `back/app/mediapipe_worker.py` — asistente para extraer puntos de referencia de un frame de imagen usando MediaPipe en Python (útil si se desea procesamiento de frames del lado del servidor).

---

## Cómo ejecutar localmente

1. Cree y active un entorno virtual de Python e instale los paquetes requeridos. Ejemplo (Windows PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install fastapi uvicorn numpy opencv-python mediapipe pydantic
```

2. Inicie el servidor backend (desde la raíz del repositorio):

```powershell
uvicorn back.app.main:app --reload --host 127.0.0.1 --port 8000
```

3. Abra el frontend en su navegador:

- Visite: `http://127.0.0.1:8000/` — el servidor sirve `front/index.html` y los activos estáticos están disponibles en `/static/`.

4. Permita el acceso a la cámara. La página ejecutará MediaPipe en el navegador. Presione "Enviar landmarks" para enviar datos al servidor.

Notas:
- Se recomienda descargar los archivos JavaScript de MediaPipe (`camera_utils.js`, `drawing_utils.js`, `hands.js`) en `front/vendor/mediapipe/` y servirlos desde `/static/vendor/mediapipe/` para evitar advertencias de Prevención de Seguimiento del navegador al cargar desde CDN.

---

## Notas de depuración y problemas comunes

- 405 Method Not Allowed al hacer POST a `/extract` — causa: los archivos estáticos se montaron en la raíz `/` e interceptaron rutas de API (corregido: ahora estáticos montados en `/static`).
- ReferenceError: `Hands` / `FilesetResolver` — causa: mezclar API de MediaPipe Tasks con API clásica `hands.js`. Solución: usar la API `Hands` clásica (como se implementa en `front/app.js`).
- CORS / falta de coincidencia de origen (`localhost` vs `127.0.0.1`) — establezca `BACKEND_URL` en el cliente a `window.location.origin` o asegure el mismo origen. El backend configura CORS con `allow_origins=["*"]` para desarrollo.
- Advertencias de Prevención de Seguimiento para cdn.jsdelivr.net — descargar archivos de proveedores y servirlos desde su origen para reducir estas advertencias.
- TypeError 'Landmark' object is not subscriptable — causa: el backend intentó indexar instancias de modelo Pydantic como dicts; corregido convirtiendo modelos a dicts e hiciendo `to_np` robusto.
- KeyError 'z' — causa: algunos anclajes de pose incluían solo x, y (sin z). `normalize_landmarks` ahora acepta z faltante (por defecto a 0.0) y recurre a normalización de centroide si los anclajes clave carecen de x/y.

---

## Mejoras sugeridas

1. Validación de frontend: asegúrese de que cada punto de referencia tenga `x` e `y` antes de enviar; establezca `z` a 0.0 si falta y requiera 21 puntos de referencia (o advierta de lo contrario).
2. Agregue un pequeño `scripts/download_mediapipe.ps1` para obtener los tres archivos JS de MediaPipe en `front/vendor/mediapipe`.
3. Agregue pruebas unitarias para `back/app/utils.py::process_landmarks` con conjuntos de puntos de referencia sintéticos (caso normal, campos faltantes, casos extremos de mano única/sin mano).
4. En producción, restrinja orígenes CORS y sirva archivos estáticos a través de un servidor web adecuado; fije versiones de dependencia en `requirements.txt`.



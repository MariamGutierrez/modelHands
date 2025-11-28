// Configuración
const VIDEO_WIDTH = 640;
const VIDEO_HEIGHT = 480;
// Use the current origin so requests match the page origin (avoids CORS between localhost vs 127.0.0.1)
const BACKEND_URL = window.location.origin;

// Elementos del DOM
const video = document.getElementById('video');
const canvas = document.getElementById('overlay');
const ctx = canvas.getContext('2d');
const sendButton = document.getElementById('send');

// Variables globales
let landmarks = [];
let poseAnchors = {};
let hands = null;
let camera = null;

// Esperar a que las librerías de MediaPipe estén disponibles en window
async function waitForMediaPipe(timeout = 8000) {
    const start = Date.now();
    while (!(window.Hands && window.Camera)) {
        if (Date.now() - start > timeout) return false;
        await new Promise(r => setTimeout(r, 100));
    }
    return true;
}

// Control del indicador de estado en la UI
function setStatus(state, message) {
    const el = document.getElementById('status');
    if (!el) return;
    el.classList.remove('loading', 'ready', 'error');
    if (state) el.classList.add(state);
    const text = el.querySelector('.status-text');
    if (text && message) text.textContent = message;
}

// Inicializar MediaPipe Hands
async function initializeMediaPipe() {
    // Usar la API clásica de MediaPipe (hands.js + camera_utils.js)
    hands = new Hands({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        }
    });

    hands.setOptions({
        maxNumHands: 2,
        modelComplexity: 1,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });

    hands.onResults((results) => {
        // Ajustar tamaño del canvas al video si hace falta
        if (video.videoWidth && video.videoHeight) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
        } else {
            canvas.width = VIDEO_WIDTH;
            canvas.height = VIDEO_HEIGHT;
        }

        landmarks = [];
        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
            results.multiHandLandmarks.forEach((handLandmarks) => {
                handLandmarks.forEach((lm, id) => {
                    landmarks.push({
                        id: id,
                        x: lm.x,
                        y: lm.y,
                        z: lm.z || 0,
                        visibility: 1
                    });
                });
            });

            poseAnchors = {
                nose: { x: landmarks[0]?.x || 0, y: landmarks[0]?.y || 0 },
                left_shoulder: { x: landmarks[11]?.x || 0, y: landmarks[11]?.y || 0 },
                right_shoulder: { x: landmarks[12]?.x || 0, y: landmarks[12]?.y || 0 }
            };
        }

        // Dibujar resultado
        drawLandmarks();
    });

    // Inicializar cámara mediante Camera de camera_utils
    try {
        camera = new Camera(video, {
            onFrame: async () => {
                await hands.send({image: video});
            },
            width: VIDEO_WIDTH,
            height: VIDEO_HEIGHT
        });
        await camera.start();
        console.log('MediaPipe y Camera() inicializados correctamente');
        setStatus('ready', 'Listo — cámara activa');
    } catch (err) {
        console.warn('Error iniciando Camera(), intentar fallback con getUserMedia:', err);

        // Fallback: usar getUserMedia y enviar frames manualmente a hands
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: { width: VIDEO_WIDTH, height: VIDEO_HEIGHT } });
            video.srcObject = stream;
            await video.play();
            console.log('Cámara iniciada vía getUserMedia (fallback). Iniciando bucle manual de frames.');
            setStatus('ready', 'Listo — cámara activa (fallback)');

            // Bucle manual para enviar frames a hands
            const manualLoop = async () => {
                try {
                    await hands.send({ image: video });
                } catch (sendErr) {
                    // Si hands.send falla por falta de recursos, lo registramos
                    console.error('Error enviando frame a hands:', sendErr);
                }
                requestAnimationFrame(manualLoop);
            };

            requestAnimationFrame(manualLoop);
        } catch (gmErr) {
            console.error('Fallback con getUserMedia falló:', gmErr);
            // Mostrar mensaje útil al usuario
            const notice = document.createElement('div');
            notice.className = 'notice';
            notice.textContent = 'No se pudo iniciar la cámara en este dispositivo / navegador. Revisa permisos o prueba otro navegador.';
            document.querySelector('.container')?.appendChild(notice);
            setStatus('error', 'Error: no se pudo iniciar la cámara');
        }
    }
}

// Inicializar cámara
async function initializeCamera() {
    // Ya manejado por camera_utils dentro de initializeMediaPipe
    return;
}

// Procesar frames de video
// La captura y el envío de frames se realiza vía Camera -> hands.onResults
// por lo que no necesitamos un bucle manual aquí.

// Dibujar landmarks en el canvas
function drawLandmarks() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Dibujar conexiones entre puntos
    const connections = [
        [0, 1], [1, 2], [2, 3], [3, 4],           // pulgar
        [0, 5], [5, 6], [6, 7], [7, 8],           // índice
        [0, 9], [9, 10], [10, 11], [11, 12],      // medio
        [0, 13], [13, 14], [14, 15], [15, 16],    // anular
        [0, 17], [17, 18], [18, 19], [19, 20],    // meñique
        [5, 9], [9, 13], [13, 17]                 // conexiones entre dedos
    ];

    ctx.strokeStyle = '#00FF00';
    ctx.lineWidth = 2;

    connections.forEach(([start, end]) => {
        const p1 = landmarks[start];
        const p2 = landmarks[end];
        
        if (p1 && p2 && p1.visibility > 0.5 && p2.visibility > 0.5) {
            ctx.beginPath();
            ctx.moveTo(p1.x * canvas.width, p1.y * canvas.height);
            ctx.lineTo(p2.x * canvas.width, p2.y * canvas.height);
            ctx.stroke();
        }
    });

    // Dibujar puntos
    ctx.fillStyle = '#FF0000';
    landmarks.forEach((landmark) => {
        if (landmark.visibility > 0.5) {
            ctx.beginPath();
            ctx.arc(
                landmark.x * canvas.width,
                landmark.y * canvas.height,
                5,
                0,
                2 * Math.PI
            );
            ctx.fill();
        }
    });
}

// Enviar landmarks al backend
async function sendLandmarks() {
    if (landmarks.length === 0) {
        alert('No hay landmarks detectados. Por favor, acerca tu mano a la cámara.');
        return;
    }

    const payload = {
        sign_id: 'sign_' + Date.now(),
        type: 'hand',
        device_id: 'web_camera',
        timestamp: new Date().toISOString(),
        landmarks: landmarks,
        pose_anchors: poseAnchors
    };

    try {
        const response = await fetch(`${BACKEND_URL}/extract`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const text = await response.text().catch(() => null);
            console.error('Respuesta no OK del backend:', response.status, text);
            throw new Error(`Error del servidor: ${response.status} ${text ? '- ' + text : ''}`);
        }

        const result = await response.json();
        console.log('Respuesta del backend:', result);
        alert('¡Landmarks enviados correctamente!');
    } catch (error) {
        console.error('Error al enviar landmarks:', error);
        alert('Error al enviar los landmarks. Verifica la conexión con el backend.');
    }
}

// Event listeners
sendButton.addEventListener('click', sendLandmarks);

// Inicialización
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Inicializando aplicación...');
    setStatus('loading', 'Cargando librerías...');
    const ok = await waitForMediaPipe();
    if (!ok) {
        console.error('MediaPipe libs no se cargaron en el tiempo esperado. Asegúrate de que camera_utils.js y hands.js estén disponibles.');
        setStatus('error', 'Error: librerías de MediaPipe no cargaron');
        return;
    }
    try {
        await initializeMediaPipe();
    } catch (e) {
        console.error('initializeMediaPipe falló:', e);
        setStatus('error', 'Error al inicializar MediaPipe');
    }
});

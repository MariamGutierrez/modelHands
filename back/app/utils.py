import numpy as np

# -------------------------------
# Helpers matemáticos
# -------------------------------

def to_np(lm_list):
    """Convierte lista de landmarks (dicts) a matriz Nx3 NumPy."""
    arr = []
    for lm in lm_list:
        # lm puede ser dict-like o un objeto pydantic
        if isinstance(lm, dict):
            x = lm.get('x', 0.0)
            y = lm.get('y', 0.0)
            z = lm.get('z', 0.0)
        else:
            # objeto con atributos (pydantic model u otro)
            if hasattr(lm, 'dict'):
                d = lm.dict()
                x = d.get('x', 0.0)
                y = d.get('y', 0.0)
                z = d.get('z', 0.0)
            else:
                x = getattr(lm, 'x', 0.0)
                y = getattr(lm, 'y', 0.0)
                z = getattr(lm, 'z', 0.0)
        arr.append([x, y, z])
    return np.array(arr, dtype=np.float32)


def angle_between_points(a, b, c):
    """
    Calcula el ángulo formado por los puntos a-b-c (ángulo en 'b').
    Devuelve un valor en grados.
    """
    ba = a - b
    bc = c - b
    cosang = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    ang = np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0)))
    return float(ang)


def compute_palm_normal(landmarks_np):
    """
    Calcula el vector normal de la palma usando:
        - Wrist (0)
        - Index knuckle (5)
        - Pinky knuckle (17)
    """
    p0 = landmarks_np[0]
    p5 = landmarks_np[5]
    p17 = landmarks_np[17]

    v1 = p5 - p0
    v2 = p17 - p0

    normal = np.cross(v1, v2)
    normal_norm = normal / (np.linalg.norm(normal) + 1e-8)
    return normal_norm.tolist()


def normalize_landmarks(landmarks_np, pose_anchors=None):
    """
    Normaliza landmarks usando distancia entre hombros (si existe pose_anchors),
    o normalización por centroide y factor de escala.
    """
    if pose_anchors:
        # Normalización antropométrica
        # pose_anchors puede contener solo x,y; usar valores por defecto si falta z
        ls_anchor = pose_anchors.get('left_shoulder', {}) if isinstance(pose_anchors, dict) else getattr(pose_anchors, 'left_shoulder', {})
        rs_anchor = pose_anchors.get('right_shoulder', {}) if isinstance(pose_anchors, dict) else getattr(pose_anchors, 'right_shoulder', {})

        ls_x = ls_anchor.get('x') if isinstance(ls_anchor, dict) else getattr(ls_anchor, 'x', None)
        ls_y = ls_anchor.get('y') if isinstance(ls_anchor, dict) else getattr(ls_anchor, 'y', None)
        ls_z = ls_anchor.get('z', 0.0) if isinstance(ls_anchor, dict) else getattr(ls_anchor, 'z', 0.0)

        rs_x = rs_anchor.get('x') if isinstance(rs_anchor, dict) else getattr(rs_anchor, 'x', None)
        rs_y = rs_anchor.get('y') if isinstance(rs_anchor, dict) else getattr(rs_anchor, 'y', None)
        rs_z = rs_anchor.get('z', 0.0) if isinstance(rs_anchor, dict) else getattr(rs_anchor, 'z', 0.0)

        # Si falta x/y en alguno, fallback a centroid-based normalization
        if ls_x is None or ls_y is None or rs_x is None or rs_y is None:
            # caemos a la normalización por centroide
            centroid = landmarks_np.mean(axis=0)
            lm_centered = landmarks_np - centroid
            scale = np.mean(np.linalg.norm(lm_centered, axis=1)) + 1e-8
            lm_norm = lm_centered / scale
            return lm_norm

        ls = np.array([ls_x, ls_y, ls_z])
        rs = np.array([rs_x, rs_y, rs_z])

        shoulder_dist = np.linalg.norm(ls - rs) + 1e-8
        lm_norm = (landmarks_np - landmarks_np.mean(axis=0)) / shoulder_dist

    else:
        # Normalización por centroide
        centroid = landmarks_np.mean(axis=0)
        lm_centered = landmarks_np - centroid

        # Factor de escala: distancia media entre puntos
        scale = np.mean(np.linalg.norm(lm_centered, axis=1)) + 1e-8
        lm_norm = lm_centered / scale

    return lm_norm


# ------------------------------
# PROCESO PRINCIPAL
# ------------------------------

def process_landmarks(landmarks_list, pose_anchors=None):
    """
    Recibe una lista de landmarks (dicts) y anchors opcionales.
    Devuelve:
      - landmarks normalizados
      - ángulos relevantes
      - vector normal de palma
      - centroid
    """

    # 1. Convertir a NumPy para cálculos
    lm_np = to_np(landmarks_list)

    # 2. Normalización
    lm_norm = normalize_landmarks(lm_np, pose_anchors)

    # 3. Cálculo de ángulos MCP-PIP-DIP
    # Indices de dedos en MediaPipe Hands:
    # Dedos:  [MCP, PIP, DIP, TIP]
    finger_joints = {
        "index":  [5, 6, 7, 8],
        "middle": [9, 10, 11, 12],
        "ring":   [13, 14, 15, 16],
        "pinky":  [17, 18, 19, 20],
        "thumb":  [1, 2, 3, 4]
    }

    angles = []

    for name, joints in finger_joints.items():
        a = lm_norm[joints[0]]
        b = lm_norm[joints[1]]
        c = lm_norm[joints[2]]
        ang = angle_between_points(a, b, c)
        angles.append(ang)

    # 4. Vector normal de palma
    palm_normal = compute_palm_normal(lm_np)

    # 5. Centroid
    centroid = lm_np.mean(axis=0).tolist()

    # 6. Preparar salida final
    features = {
        "landmarks_norm": lm_norm.tolist(),
        "angles": angles,
        "palm_normal": palm_normal,
        "centroid": {
            "x": centroid[0],
            "y": centroid[1],
            "z": centroid[2]
        }
    }

    return features

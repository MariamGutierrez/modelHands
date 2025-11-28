from pydantic import BaseModel
from typing import List, Dict

class Landmark(BaseModel):
    id: int
    x: float
    y: float
    z: float
    visibility: float

class PoseAnchors(BaseModel):
    nose: Dict[str, float]
    left_shoulder: Dict[str, float]
    right_shoulder: Dict[str, float]

class CapturePayload(BaseModel):
    sign_id: str
    type: str
    device_id: str
    timestamp: str
    landmarks: List[Landmark] = None
    pose_anchors: PoseAnchors = None

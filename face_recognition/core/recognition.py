import numpy as np
import cv2
from core.model_loader import get_model
from core.database import get_all
from config import RECOGNITION_THRESHOLD


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Cả hai đã được L2-normalize nên dot product = cosine similarity
    return float(np.dot(a, b))


def recognize_faces(image_bytes: bytes) -> list[dict]:
    """
    Nhận vào raw image bytes.
    Trả về list các kết quả, mỗi kết quả là:
    {
        "name": str,          # tên người hoặc "Unknown"
        "confidence": float,  # cosine similarity score
        "bbox": list[int],    # [x1, y1, x2, y2]
    }
    """
    model = get_model()
    db = get_all()

    # Decode bytes → numpy array → BGR image
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise ValueError("Không decode được ảnh.")

    faces = model.get(frame)

    if len(faces) == 0:
        return []

    results = []
    for face in faces:
        embedding = _l2_normalize(face.embedding)
        bbox = [int(x) for x in face.bbox]

        if len(db) == 0:
            results.append({"name": "Unknown", "confidence": 0.0, "bbox": bbox})
            continue

        # So sánh với tất cả người trong database
        best_name = "Unknown"
        best_score = -1.0

        for name, db_embedding in db.items():
            score = _cosine_similarity(embedding, db_embedding)
            if score > best_score:
                best_score = score
                best_name = name

        if best_score < RECOGNITION_THRESHOLD:
            best_name = "Unknown"

        results.append({
            "name": best_name,
            "confidence": round(best_score, 4),
            "bbox": bbox,
        })

    return results

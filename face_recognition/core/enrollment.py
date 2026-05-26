import cv2
import numpy as np
from PIL import Image

from core.database import save_person, save_thumbnail
from core.model_loader import get_model
from config import FRAME_SKIP, DETECTION_CONFIDENCE


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def _face_crop_jpeg(frame_bgr: np.ndarray, bbox: list[int]) -> bytes | None:
    x1, y1, x2, y2 = bbox
    h, w = frame_bgr.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    crop = frame_bgr[y1:y2, x1:x2]
    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(crop_rgb)
    buf = __import__("io").BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def extract_embeddings_from_video(video_path: str) -> tuple[list[np.ndarray], np.ndarray | None]:
    """
    Đọc video, lấy embedding từ các frame hợp lệ.
    Trả về (embeddings, frame_bgr đầu tiên có mặt) để tạo thumbnail.
    """
    model = get_model()
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"Không mở được video: {video_path}")

    embeddings = []
    preview_frame = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % FRAME_SKIP == 0:
            faces = model.get(frame)
            for face in faces:
                if face.det_score < DETECTION_CONFIDENCE:
                    continue
                embedding = _l2_normalize(face.embedding)
                embeddings.append(embedding)
                if preview_frame is None:
                    preview_frame = frame.copy()

        frame_idx += 1

    cap.release()
    return embeddings, preview_frame


def _finalize_enroll(
    name: str,
    embeddings: list[np.ndarray],
    preview_frame: np.ndarray | None,
    *,
    overwrite: bool,
) -> dict:
    if len(embeddings) == 0:
        return {
            "success": False,
            "message": (
                "Không tìm thấy khuôn mặt hợp lệ "
                f"(confidence < {DETECTION_CONFIDENCE})."
            ),
            "frames_used": 0,
        }

    mean_embedding = np.mean(embeddings, axis=0)
    final_embedding = _l2_normalize(mean_embedding)
    save_person(name, final_embedding, frames_used=len(embeddings), overwrite=overwrite)

    if preview_frame is not None:
        model = get_model()
        faces = model.get(preview_frame)
        for face in faces:
            if face.det_score >= DETECTION_CONFIDENCE:
                bbox = [int(x) for x in face.bbox]
                thumb = _face_crop_jpeg(preview_frame, bbox)
                if thumb:
                    save_thumbnail(name, thumb)
                break

    return {
        "success": True,
        "message": f"Đã đăng ký thành công: {name}",
        "frames_used": len(embeddings),
    }


def enroll_from_image_bytes(name: str, image_bytes: bytes, *, overwrite: bool = False) -> dict:
    """Đăng ký từ một ảnh (webcam trình duyệt)."""
    model = get_model()
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return {"success": False, "message": "Không đọc được ảnh.", "frames_used": 0}

    embeddings = []
    for face in model.get(frame):
        if face.det_score < DETECTION_CONFIDENCE:
            continue
        embeddings.append(_l2_normalize(face.embedding))

    return _finalize_enroll(name, embeddings, frame, overwrite=overwrite)


def enroll_person(name: str, video_path: str, *, overwrite: bool = False) -> dict:
    try:
        embeddings, preview_frame = extract_embeddings_from_video(video_path)
    except ValueError as e:
        return {"success": False, "message": str(e), "frames_used": 0}

    return _finalize_enroll(name, embeddings, preview_frame, overwrite=overwrite)

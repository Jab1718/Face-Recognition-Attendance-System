import insightface
from insightface.app import FaceAnalysis
from config import MODEL_DIR

_app = None

def get_model() -> FaceAnalysis:
    """
    Load insightface model một lần duy nhất (singleton).
    RetinaFace detection + ArcFace R50 embedding, chạy trên CPU.
    """
    global _app
    if _app is None:
        _app = FaceAnalysis(
            name="buffalo_l",       # RetinaFace + ArcFace R50
            root=MODEL_DIR,
            providers=["CPUExecutionProvider"],
        )
        _app.prepare(ctx_id=-1, det_size=(640, 640))
    return _app

import os
import tempfile
from urllib.parse import unquote
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

# Import thêm logic điểm danh
from core.database import (
    delete_person, 
    get_thumbnail_bytes, 
    list_people_detail,
    init_attendance_db,
    log_attendance,
    get_attendance_logs
)
from core.enrollment import enroll_from_image_bytes, enroll_person
from core.recognition import recognize_faces
from core.webcam import record_webcam_video

API_VERSION = "2.2"

app = FastAPI(title="Face Recognition API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tự tạo bảng khi server chạy
@app.on_event("startup")
def startup_event():
    init_attendance_db()


def _parse_bool(value: str) -> bool:
    return str(value).lower() in ("true", "1", "yes")

def _enroll_via_webcam(name: str, overwrite: bool) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp_path = tmp.name

    record = record_webcam_video(tmp_path)
    if not record["success"]:
        os.unlink(tmp_path)
        raise HTTPException(status_code=422, detail=record["message"])

    try:
        result = enroll_person(name=name, video_path=tmp_path, overwrite=overwrite)
    finally:
        os.unlink(tmp_path)

    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["message"])
    return result

@app.get("/health")
def health():
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "enroll_webcam": True,
        "endpoints": {
            "upload": "POST /enroll",
            "webcam": "POST /enroll/webcam",
            "attendance": "GET /attendance"
        },
    }

@app.post("/enroll/webcam")
def enroll_from_webcam(
    name: str = Form(...),
    overwrite: str = Form("false"),
):
    return _enroll_via_webcam(name.strip(), _parse_bool(overwrite))

@app.post("/enroll")
async def enroll(
    name: str = Form(...),
    video: UploadFile = File(...),
    overwrite: str = Form("false"),
):
    ow = _parse_bool(overwrite)
    person = name.strip()

    if not video.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file video: mp4, avi, mov, mkv, webm")

    suffix = os.path.splitext(video.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await video.read())
        tmp_path = tmp.name

    try:
        result = enroll_person(name=person, video_path=tmp_path, overwrite=ow)
    finally:
        os.unlink(tmp_path)

    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["message"])
    return result

@app.post("/enroll/snapshot")
async def enroll_snapshot(
    name: str = Form(...),
    image: UploadFile = File(...),
    overwrite: str = Form("false"),
):
    image_bytes = await image.read()
    result = enroll_from_image_bytes(
        name=name.strip(),
        image_bytes=image_bytes,
        overwrite=_parse_bool(overwrite),
    )
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["message"])
    return result


# LUỒNG GHI NHẬN ĐIỂM DANH TỰ ĐỘNG
@app.post("/recognize")
async def recognize(image: UploadFile = File(...)):
    image_bytes = await image.read()
    try:
        results = recognize_faces(image_bytes)
        for face in results:
            if face["name"] != "Unknown":
                # Gọi thẳng logic lưu Database
                att_data = log_attendance(face["name"], face["confidence"])
                face["attendance"] = att_data 
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"faces": results}


# LẤY LỊCH SỬ ĐIỂM DANH
@app.get("/attendance")
def get_attendance(date: str = None):
    return {"logs": get_attendance_logs(date)}


@app.get("/people")
def get_people():
    return {"people": list_people_detail()}

@app.get("/people/{name}/avatar")
def get_avatar(name: str):
    name = unquote(name)
    data = get_thumbnail_bytes(name)
    if data is None:
        raise HTTPException(status_code=404, detail="Không có ảnh đại diện")
    return Response(content=data, media_type="image/jpeg")

@app.delete("/people/{name}")
def remove_person(name: str):
    name = unquote(name)
    success = delete_person(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy: {name}")
    return {"message": f"Đã xóa: {name}"}
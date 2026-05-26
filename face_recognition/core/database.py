import os
import pickle
import sqlite3
from datetime import datetime, timezone, timedelta

import numpy as np

from config import DATABASE_PATH, MIN_FRAMES_STABLE, THUMBNAIL_DIR

# --- LOGIC CŨ LƯU KHUÔN MẶT (PICKLE) ---
def _load() -> dict:
    if not os.path.exists(DATABASE_PATH):
        return {}
    with open(DATABASE_PATH, "rb") as f:
        return pickle.load(f)

def _save(db: dict) -> None:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    with open(DATABASE_PATH, "wb") as f:
        pickle.dump(db, f)

def _normalize_entry(value) -> dict:
    if isinstance(value, np.ndarray):
        return {
            "embedding": value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "stable",
            "frames_used": 0,
        }
    return value

def _status_from_frames(frames_used: int) -> str:
    if frames_used < MIN_FRAMES_STABLE:
        return "needs_update"
    return "stable"

def save_person(name: str, embedding: np.ndarray, *, frames_used: int, overwrite: bool = False) -> None:
    db = _load()
    created_at = datetime.now(timezone.utc).isoformat()
    if name in db and not overwrite:
        entry = _normalize_entry(db[name])
        created_at = entry.get("created_at", created_at)

    db[name] = {
        "embedding": embedding,
        "created_at": created_at,
        "status": _status_from_frames(frames_used),
        "frames_used": frames_used,
    }
    _save(db)

def save_embedding(name: str, embedding: np.ndarray) -> None:
    save_person(name, embedding, frames_used=MIN_FRAMES_STABLE, overwrite=True)

def get_embedding(name: str) -> np.ndarray | None:
    db = _load()
    if name not in db:
        return None
    return _normalize_entry(db[name])["embedding"]

def delete_person(name: str) -> bool:
    db = _load()
    if name not in db:
        return False
    del db[name]
    _save(db)
    thumb_path = os.path.join(THUMBNAIL_DIR, f"{name}.jpg")
    if os.path.exists(thumb_path):
        os.remove(thumb_path)
    return True

def list_people() -> list[str]:
    return list(_load().keys())

def list_people_detail() -> list[dict]:
    db = _load()
    people = []
    for name in sorted(db.keys()):
        entry = _normalize_entry(db[name])
        people.append({
            "name": name,
            "created_at": entry.get("created_at", ""),
            "status": entry.get("status", "stable"),
            "frames_used": entry.get("frames_used", 0),
            "has_thumbnail": os.path.exists(_thumbnail_path(name)),
        })
    return people

def get_all() -> dict[str, np.ndarray]:
    db = _load()
    return {name: _normalize_entry(entry)["embedding"] for name, entry in db.items()}

def _thumbnail_path(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return os.path.join(THUMBNAIL_DIR, f"{safe}.jpg")

def save_thumbnail(name: str, image_bytes: bytes) -> None:
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    with open(_thumbnail_path(name), "wb") as f:
        f.write(image_bytes)

def get_thumbnail_bytes(name: str) -> bytes | None:
    path = _thumbnail_path(name)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()

# --- TÍNH NĂNG MỚI: LOGIC SQLITE ĐIỂM DANH ---
ATTENDANCE_DB = "database/attendance.db"

def init_attendance_db():
    """Khởi tạo bảng điểm danh nếu chưa có."""
    os.makedirs(os.path.dirname(ATTENDANCE_DB), exist_ok=True)
    with sqlite3.connect(ATTENDANCE_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                timestamp DATETIME,
                confidence REAL,
                status TEXT
            )
        """)

def log_attendance(name: str, confidence: float) -> dict:
    """Ghi nhận điểm danh, chặn spam 30 phút, đánh giá đúng giờ/đi muộn."""
    with sqlite3.connect(ATTENDANCE_DB) as conn:
        cur = conn.cursor()
        
        # 1. Chống spam 30 phút
        cur.execute("SELECT timestamp FROM attendance WHERE name = ? ORDER BY timestamp DESC LIMIT 1", (name,))
        row = cur.fetchone()
        now = datetime.now()
        
        if row:
            last_time = datetime.fromisoformat(row[0])
            if now - last_time < timedelta(minutes=30):
                return {"status": "cooldown", "message": "Đã điểm danh trước đó"}

        # 2. Đánh giá trạng thái (Mốc 08:30 sáng)
        limit_time = now.replace(hour=8, minute=30, second=0, microsecond=0)
        status = "Đúng giờ" if now <= limit_time else "Đi muộn"

        # 3. Ghi vào database
        cur.execute("INSERT INTO attendance (name, timestamp, confidence, status) VALUES (?, ?, ?, ?)",
                    (name, now.isoformat(), confidence, status))
        conn.commit()

        return {"status": "success", "attendance_status": status, "time": now.strftime("%H:%M:%S")}

def get_attendance_logs(date_str: str = None):
    """Truy vấn dữ liệu điểm danh theo ngày."""
    with sqlite3.connect(ATTENDANCE_DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if date_str:
            # Lọc theo ký tự bắt đầu của ISO string (YYYY-MM-DD)
            cur.execute("SELECT * FROM attendance WHERE timestamp LIKE ? ORDER BY timestamp DESC", (f"{date_str}%",))
        else:
            cur.execute("SELECT * FROM attendance ORDER BY timestamp DESC LIMIT 100")
        return [dict(row) for row in cur.fetchall()]
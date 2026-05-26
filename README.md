<div align="center">

# 🧑 AI Face Check-in System

**Real-time facial recognition attendance system powered by InsightFace, FastAPI, and Streamlit**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![InsightFace](https://img.shields.io/badge/InsightFace-buffalo__l-blue?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

</div>

---

## ✨ Features

- **Real-time recognition** via browser webcam — automatically logs attendance when a registered face is detected
- **Anti-spam protection** — blocks duplicate check-ins within a 30-minute window
- **Punctuality tracking** — auto-classifies each record as *On time* or *Late* based on an 08:30 cutoff
- **Flexible enrollment** — register staff via live webcam (10-second recording), video upload, or single snapshot
- **3-page dashboard** — live check-in view, staff management, and full attendance history with CSV export
- **REST API** — clean FastAPI backend decoupled from the UI; easily extensible

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Face detection | InsightFace `buffalo_l` — RetinaFace |
| Face embedding | InsightFace `buffalo_l` — ArcFace R50 |
| Matching | L2-normalized cosine similarity |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Embedding store | Pickle (`.pkl`) |
| Attendance store | SQLite |

---

## 📁 Project Structure

```
face_recognition/
├── config.py               # Global constants
├── requirements.txt
├── run_api.bat             # Windows: start backend
├── run_ui.bat              # Windows: start frontend
├── stop_api.bat            # Windows: stop backend
│
├── api/
│   └── main.py             # FastAPI app — all REST endpoints
│
├── core/
│   ├── model_loader.py     # InsightFace singleton loader (CPU)
│   ├── database.py         # Embedding store (pickle) + attendance (SQLite)
│   ├── enrollment.py       # Video / image → embedding → save
│   ├── recognition.py      # Image → cosine similarity → name + confidence
│   └── webcam.py           # Server-side webcam recording (local use)
│
├── ui/
│   ├── app.py              # Streamlit app — 3-page navigation
│   ├── components.py       # Enroll modal, staff table, API helpers
│   └── styles.py           # Modern CSS theme (Inter font, CSS variables)
│
├── database/               # Auto-created: faces.pkl + attendance.db
└── models/                 # Auto-downloaded: InsightFace buffalo_l model
```

---

## ⚙️ Installation

**Requirements:** Python 3.10+, a webcam (for live check-in and enrollment)

```bash
git clone https://github.com/Jab1718/Face-Recognition-Attendance-System.git
cd Face-Recognition-Attendance-System/face_recognition
pip install -r requirements.txt
```

> The InsightFace `buffalo_l` model (~500 MB) is downloaded automatically into `models/` on first run.

---

## 🚀 Running

### Windows (batch scripts)

```
stop_api.bat  →  run_api.bat  →  run_ui.bat
```

### Manual (any OS)

```bash
# Terminal 1 — Backend (run from the project root)
uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload

# Terminal 2 — Frontend
streamlit run ui/app.py
```

Verify the backend is up: http://127.0.0.1:8001/health should return:
```json
{ "status": "ok", "api_version": "2.2", "enroll_webcam": true }
```

Open the UI: **http://localhost:8501**

---

## 🖥 UI Pages

| Page | Description |
|---|---|
| **🎯 Attendance** | Live camera feed, single-shot or 3-second timer mode, instant recognition result card with status badge, today's attendance timeline, one-click CSV export |
| **👥 Staff Management** | Summary metrics, staff table with avatar + embedding status, search, add / update / delete |
| **📊 Attendance History** | Date picker, on-time vs. late breakdown, full sortable table, CSV export |

Embedding status: 🟢 Stable · 🟡 Needs update

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server status and version |
| `POST` | `/enroll` | Enroll from uploaded video file |
| `POST` | `/enroll/snapshot` | Enroll from a single image (browser webcam) |
| `POST` | `/enroll/webcam` | Enroll using server-side webcam |
| `POST` | `/recognize` | Recognize faces + auto-log attendance |
| `GET` | `/attendance?date=YYYY-MM-DD` | Query attendance records by date |
| `GET` | `/people` | List all registered staff with metadata |
| `GET` | `/people/{name}/avatar` | Get avatar thumbnail (JPEG) |
| `DELETE` | `/people/{name}` | Remove a person from the system |

---

## ⚙️ Configuration (`config.py`)

| Parameter | Default | Description |
|---|---|---|
| `FRAME_SKIP` | `10` | Process 1 frame every N frames during enrollment |
| `DETECTION_CONFIDENCE` | `0.9` | Minimum face detection score |
| `RECOGNITION_THRESHOLD` | `0.45` | Minimum cosine similarity to confirm identity |
| `MIN_FRAMES_STABLE` | — | Frames required for an embedding to reach *stable* status |
| `ENROLL_DURATION_SEC` | — | Recording duration for server-side webcam enrollment |
| `MODEL_DIR` | `models/` | InsightFace model directory |
| `DATABASE_PATH` | `database/faces.pkl` | Embedding store path |
| `THUMBNAIL_DIR` | `database/thumbnails/` | Avatar thumbnail directory |

---

## 📝 Notes

- The backend and frontend must run **simultaneously**; the UI communicates entirely via REST API.
- The **08:30 cutoff** for punctuality classification can be changed in `core/database.py → log_attendance()`.
- Duplicate check-ins are blocked for **30 minutes** per person.
- Enrollment via the UI records a **10-second video** in the browser (no server-side camera required).
- The `API_URL` used by the UI can be overridden with the `API_URL` environment variable.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

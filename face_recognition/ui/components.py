import io
import os
import time
from datetime import datetime
from urllib.parse import quote

import requests
import streamlit as st
import streamlit.components.v1 as st_components
from PIL import Image, ImageDraw

from config import API_URL as _DEFAULT_API_URL

API_URL = os.environ.get("API_URL", _DEFAULT_API_URL).rstrip("/")
ENROLL_DURATION = 10

STATUS_LABELS = {
    "stable": ("Đã nhận diện ổn định", "status-stable"),
    "needs_update": ("Cần cập nhật", "status-needs_update"),
    "error": ("Chưa nhận diện / Lỗi", "status-error"),
}


def api_get_people() -> list[dict] | None:
    try:
        resp = requests.get(f"{API_URL}/people", timeout=10)
        if resp.status_code == 200:
            return resp.json()["people"]
    except requests.RequestException:
        pass
    return None


def api_health() -> tuple[bool, str]:
    """Kiểm tra API song song 2 endpoint; tổng timeout ~3s thay vì 15s."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _check(path: str) -> tuple[bool, str]:
        try:
            resp = requests.get(f"{API_URL}{path}", timeout=3)
            if resp.status_code == 200:
                return True, API_URL
            return False, f"HTTP {resp.status_code} tại {path}"
        except requests.RequestException as e:
            return False, str(e)

    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {ex.submit(_check, p): p for p in ("/health", "/people")}
        last_err = "Không kết nối được"
        for fut in as_completed(futures):
            ok, msg = fut.result()
            if ok:
                return True, msg
            last_err = msg
    return False, last_err


def api_supports_webcam_enroll() -> tuple[bool, str]:
    """
    API mới: GET /health có api_version hoặc enroll_webcam,
    và POST /enroll/webcam không trả 404.
    """
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("enroll_webcam") is True:
                return True, f"v{data.get('api_version', '?')}"
            eps = data.get("endpoints", {})
            if isinstance(eps, dict) and "webcam" in eps:
                return True, f"v{data.get('api_version', '?')}"
    except requests.RequestException:
        pass

    try:
        probe = requests.post(
            f"{API_URL}/enroll/webcam",
            data={"name": "__health_probe__", "overwrite": "false"},
            timeout=20,
        )
        if probe.status_code == 404:
            return False, "404 /enroll/webcam"
        detail = str(probe.json().get("detail", "")) if probe.headers.get("content-type", "").startswith("application/json") else ""
        if "video" in detail.lower() and "required" in detail.lower():
            return False, "API cũ (bắt buộc video)"
        return True, "probe OK"
    except requests.RequestException as e:
        return False, str(e)


def api_error_message(resp: requests.Response | None) -> str:
    if resp is None:
        return "Không nhận được phản hồi từ API."
    if resp.status_code == 422:
        try:
            detail = resp.json().get("detail")
            if isinstance(detail, list) and detail:
                msg = detail[0].get("msg", "") if isinstance(detail[0], dict) else str(detail[0])
                if "video" in str(detail).lower() and "required" in str(detail).lower():
                    return (
                        "API đang dùng endpoint cũ (bắt buộc upload video). "
                        "Chạy `stop_api.bat` rồi `run_api.bat` (API port 8001)."
                    )
                return str(detail[0]) if not isinstance(detail[0], dict) else msg
        except Exception:
            pass
    if resp.status_code == 404:
        url = getattr(resp, "url", "")
        return (
            f"Endpoint không tồn tại (404){': ' + url if url else ''}. "
            "Tắt terminal API cũ, chạy lại từ thư mục dự án:\n"
            "`cd D:\\face_recognition` → "
            "`uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload`"
        )
    try:
        body = resp.json()
        detail = body.get("detail", body)
        if isinstance(detail, list):
            return str(detail[0]) if detail else resp.text
        return str(detail)
    except Exception:
        text = (resp.text or "").strip()
        return text[:300] if text else f"Lỗi HTTP {resp.status_code}"


def avatar_url(name: str) -> str:
    return f"{API_URL}/people/{quote(name, safe='')}/avatar"


def format_date(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso_str[:16]


def draw_recognition_result(image_bytes: bytes, faces: list[dict]) -> Image.Image:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    for face in faces:
        x1, y1, x2, y2 = face["bbox"]
        color = "#ef4444" if face["name"] == "Unknown" else "#22c55e"
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        label = f"{face['name']} ({face['confidence']:.2f})"
        draw.text((x1, max(0, y1 - 18)), label, fill=color)
    return img


def filter_people(
    people: list[dict],
    search: str,
    date_from,
    date_to,
) -> list[dict]:
    result = people
    if search.strip():
        q = search.strip().lower()
        result = [p for p in result if q in p["name"].lower()]

    if date_from or date_to:
        filtered = []
        for p in result:
            if not p.get("created_at"):
                continue
            try:
                dt = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).date()
            except ValueError:
                continue
            if date_from and dt < date_from:
                continue
            if date_to and dt > date_to:
                continue
            filtered.append(p)
        result = filtered
    return result


def render_user_table(people: list[dict], on_update, on_delete) -> None:
    if not people:
        st.info("Không có dữ liệu phù hợp bộ lọc.")
        return

    # Header row
    h1, h2, h3, h4, h5, h6 = st.columns([1, 3, 3, 3, 1, 1])
    h1.caption("Ảnh")
    h2.caption("Tên")
    h3.caption("Ngày tạo")
    h4.caption("Trạng thái")
    # h5, h6: nút — không cần header
    st.divider()

    for p in people:
        name = p["name"]
        status_key = p.get("status", "stable")
        status_label, _ = STATUS_LABELS.get(status_key, STATUS_LABELS["error"])
        STATUS_ICONS = {"stable": "🟢", "needs_update": "🟡", "error": "🔴"}
        icon = STATUS_ICONS.get(status_key, "🔴")

        c_avatar, c_name, c_date, c_status, c_upd, c_del = st.columns([1, 3, 3, 3, 1, 1])

        with c_avatar:
            if p.get("has_thumbnail"):
                try:
                    resp = requests.get(avatar_url(name), timeout=3)
                    if resp.status_code == 200:
                        st.image(resp.content, width=48)
                    else:
                        st.markdown("👤")
                except requests.RequestException:
                    st.markdown("👤")
            else:
                st.markdown("👤")

        c_name.markdown(f"**{name}**")
        c_date.caption(format_date(p.get("created_at", "")))
        c_status.caption(f"{icon} {status_label}")

        with c_upd:
            if st.button("✏️", key=f"upd_{name}", help="Cập nhật", use_container_width=True):
                on_update(name)
        with c_del:
            if st.button("🗑", key=f"del_{name}", help="Xóa", use_container_width=True):
                on_delete(name)

        st.divider()


def _reset_enroll_recording():
    for key in ("enroll_record_start",):
        st.session_state.pop(key, None)


@st.experimental_dialog("Thêm / Cập nhật người mới")
def enroll_modal(prefill_name: str = ""):
    if "enroll_step" not in st.session_state:
        st.session_state.enroll_step = "form"
    if "enroll_name" not in st.session_state:
        st.session_state.enroll_name = prefill_name

    step = st.session_state.enroll_step
    is_update = bool(prefill_name)
    overwrite = is_update

    name = st.text_input(
        "Tên người mới",
        value=st.session_state.enroll_name or prefill_name,
        disabled=step == "recording",
    )

    if step == "recording":
        person_name = st.session_state.get("enroll_name", name).strip()
        overwrite_str = "true" if overwrite else "false"

        media_recorder_html = f"""
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif; }}

  #root {{
    display: flex; flex-direction: column; gap: 12px; padding: 4px;
  }}

  #preview {{
    width: 100%; aspect-ratio: 16/9; max-height: 280px;
    background: #0a1628; border-radius: 12px; object-fit: cover;
    border: 2px solid #1976d2; display: block;
  }}

  #status-bar {{
    background: #e3f0ff; border: 1px solid #90b8e0; border-radius: 10px;
    padding: 10px 14px; display: flex; align-items: center; gap: 10px;
  }}

  #dot {{
    width: 11px; height: 11px; border-radius: 50%;
    background: #90b8e0; flex-shrink: 0;
    transition: background 0.3s;
  }}
  #dot.recording {{ background: #c62828; animation: blink 1s infinite; }}
  #dot.done {{ background: #2e7d32; animation: none; }}
  #dot.uploading {{ background: #f9a825; animation: blink 0.5s infinite; }}

  @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}

  #status-text {{ color: #0a2540; font-weight: 600; font-size: 0.9rem; flex: 1; }}
  #countdown {{
    font-size: 1.5rem; font-weight: 700; color: #1565c0;
    min-width: 2.5rem; text-align: right;
  }}

  progress {{
    width: 100%; height: 6px; border-radius: 4px; border: none;
    appearance: none; background: #c8dff5;
  }}
  progress::-webkit-progress-bar {{ background: #c8dff5; border-radius: 4px; }}
  progress::-webkit-progress-value {{ background: #1565c0; border-radius: 4px; transition: width 0.3s; }}

  #result {{
    display: none; padding: 10px 14px; border-radius: 10px;
    font-weight: 600; font-size: 0.9rem;
  }}
  #result.success {{ background: #e8f5e9; border: 1px solid #2e7d32; color: #1b5e20; }}
  #result.error {{ background: #ffebee; border: 1px solid #c62828; color: #b71c1c; }}

  #btn-record {{
    width: 100%; padding: 11px; border: none; border-radius: 10px;
    background: linear-gradient(135deg, #0d47a1, #1976d2);
    color: #fff; font-size: 0.95rem; font-weight: 700;
    cursor: pointer; transition: opacity 0.2s;
  }}
  #btn-record:disabled {{ opacity: 0.45; cursor: not-allowed; }}
</style>

<div id="root">
  <video id="preview" autoplay muted playsinline></video>

  <div id="status-bar">
    <div id="dot"></div>
    <span id="status-text">Nhấn nút để bắt đầu quay</span>
    <span id="countdown"></span>
  </div>

  <progress id="prog" value="0" max="{ENROLL_DURATION}"></progress>

  <div id="result"></div>

  <button id="btn-record">▶ Bắt đầu quay {ENROLL_DURATION}s</button>
</div>

<script>
const API_URL   = "{API_URL}";
const NAME      = "{person_name}";
const OVERWRITE = "{overwrite_str}";
const DURATION  = {ENROLL_DURATION};

const video   = document.getElementById("preview");
const dot     = document.getElementById("dot");
const statusT = document.getElementById("status-text");
const cdEl    = document.getElementById("countdown");
const prog    = document.getElementById("prog");
const resultEl= document.getElementById("result");
const btn     = document.getElementById("btn-record");

let stream, recorder, chunks = [], timer, startTime;

async function startRecording() {{
  btn.disabled = true;
  resultEl.style.display = "none";

  try {{
    stream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
  }} catch(e) {{
    showResult(false, "Không truy cập được camera: " + e.message);
    btn.disabled = false;
    return;
  }}

  video.srcObject = stream;

  // Chọn codec được hỗ trợ
  const mimeTypes = [
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/webm",
    "video/mp4",
  ];
  let mimeType = "";
  for (const t of mimeTypes) {{
    if (MediaRecorder.isTypeSupported(t)) {{ mimeType = t; break; }}
  }}

  recorder = new MediaRecorder(stream, mimeType ? {{ mimeType }} : {{}});
  chunks = [];
  recorder.ondataavailable = e => {{ if (e.data.size > 0) chunks.push(e.data); }};
  recorder.onstop = uploadVideo;
  recorder.start(200);  // chunk mỗi 200ms

  startTime = Date.now();
  dot.className = "recording";
  statusT.textContent = "Đang quay — giữ mặt trong khung hình";

  timer = setInterval(() => {{
    const elapsed = (Date.now() - startTime) / 1000;
    const remaining = Math.max(0, DURATION - elapsed);
    cdEl.textContent = Math.ceil(remaining) + "s";
    prog.value = elapsed;

    if (elapsed >= DURATION) {{
      clearInterval(timer);
      recorder.stop();
      stream.getTracks().forEach(t => t.stop());
      video.srcObject = null;
      dot.className = "uploading";
      statusT.textContent = "Đang gửi lên server...";
      cdEl.textContent = "";
    }}
  }}, 100);
}}

async function uploadVideo() {{
  const ext = (recorder.mimeType || "video/webm").includes("mp4") ? "mp4" : "webm";
  const blob = new Blob(chunks, {{ type: recorder.mimeType || "video/webm" }});
  const formData = new FormData();
  formData.append("name", NAME);
  formData.append("overwrite", OVERWRITE);
  formData.append("video", blob, "enroll." + ext);

  try {{
    const resp = await fetch(API_URL + "/enroll", {{
      method: "POST",
      body: formData,
    }});
    const data = await resp.json();
    if (resp.ok) {{
      showResult(true, data.message + " — " + data.frames_used + " frames");
      prog.value = DURATION;
      dot.className = "done";
      // Báo Streamlit biết enroll xong
      window.parent.postMessage({{
        type: "streamlit:setComponentValue",
        value: {{ success: true, name: NAME, frames: data.frames_used }}
      }}, "*");
    }} else {{
      const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      showResult(false, detail);
      resetBtn();
    }}
  }} catch(e) {{
    showResult(false, "Lỗi kết nối API: " + e.message);
    resetBtn();
  }}
}}

function showResult(ok, msg) {{
  resultEl.style.display = "block";
  resultEl.className = "result " + (ok ? "success" : "error");
  resultEl.textContent = (ok ? "✅ " : "❌ ") + msg;
  statusT.textContent = ok ? "Đăng ký thành công!" : "Thất bại";
  dot.className = ok ? "done" : "";
}}

function resetBtn() {{
  btn.disabled = false;
  btn.textContent = "↺ Thử lại";
  dot.className = "";
}}

btn.addEventListener("click", startRecording);
</script>
"""

        st_components.html(media_recorder_html, height=420, scrolling=False)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Xác nhận đã đăng ký xong", type="primary", use_container_width=True):
                _close_enroll_modal()
                st.rerun()
        with col_b:
            if st.button("Hủy", use_container_width=True):
                st.session_state.enroll_step = "form"
                _reset_enroll_recording()
                st.rerun()
        return

    if step == "confirm":
        resp = st.session_state.get("enroll_result")
        if resp and resp.status_code == 200:
            data = resp.json()
            st.success(f"{data['message']} — {data['frames_used']} frames")
            if st.button("Hoàn tất", type="primary", use_container_width=True):
                _close_enroll_modal()
                st.rerun()
        else:
            st.error(api_error_message(resp))
            if st.button("Thử lại"):
                st.session_state.enroll_step = "form"
                st.rerun()
        return

    ok, err = api_health()
    if ok:
        webcam_ok, ver = api_supports_webcam_enroll()
        if webcam_ok:
            st.success(f"API OK · quay video tự động ({ver}) · {API_URL}")
        else:
            st.warning(
                f"API phản hồi nhưng **chưa có /enroll/webcam** ({ver}). "
                "Chạy `stop_api.bat` rồi `run_api.bat` (API mới dùng port **8001**)."
            )
    else:
        st.warning(
            f"API chưa phản hồi tại **{API_URL}** ({err}). "
            "Chạy `run_api.bat` hoặc: "
            "`uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload`"
        )

    st.markdown("**Quy trình**")
    st.caption(
        "Nhấn **Bắt đầu quay (10s)** → trình duyệt quay video qua camera → tự upload lên API. "
        "Không cần cài đặt gì thêm."
    )
    st.markdown(
        """
        <div class="cam-placeholder" style="max-height:100px;">
            <p>Video 10s từ camera trình duyệt → <code>POST /enroll</code></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Hoặc upload file video MP4 bên dưới.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("▶ Bắt đầu quay (10s)", type="primary", use_container_width=True, disabled=not name.strip()):
            st.session_state.enroll_name = name.strip()
            st.session_state.enroll_step = "recording"
            _reset_enroll_recording()
            st.rerun()
    with col_b:
        if st.button("Hủy", use_container_width=True):
            _close_enroll_modal()
            st.rerun()

    video_file = st.file_uploader("Hoặc upload video", type=["mp4", "avi", "mov", "mkv"])
    if video_file and name.strip():
        if st.button("Xác nhận từ video upload", use_container_width=True):
            with st.spinner("Đang enroll..."):
                resp = requests.post(
                    f"{API_URL}/enroll",
                    data={
                        "name": name.strip(),
                        "overwrite": "true" if overwrite else "false",
                    },
                    files={"video": (video_file.name, video_file.getvalue(), video_file.type)},
                    timeout=120,
                )
            st.session_state.enroll_result = resp
            st.session_state.enroll_step = "confirm"
            st.rerun()


def _close_enroll_modal():
    st.session_state.show_enroll_modal = False
    st.session_state.enroll_step = "form"
    st.session_state.enroll_name = ""
    st.session_state.pop("enroll_result", None)
    st.session_state.pop("enroll_prefill", None)
    _reset_enroll_recording()


def open_enroll_modal(name: str = ""):
    st.session_state.show_enroll_modal = True
    st.session_state.enroll_prefill = name
    st.session_state.enroll_step = "form"
    st.session_state.enroll_name = name
    _reset_enroll_recording()
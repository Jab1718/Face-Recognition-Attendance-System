import io
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from PIL import Image

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ui.components import (
    API_URL,
    api_error_message,
    api_get_people,
    api_health,
    api_supports_webcam_enroll,
    draw_recognition_result,
    enroll_modal,
    filter_people,
    open_enroll_modal,
    render_user_table,
)
from ui.styles import MODERN_CSS

# --- INIT SESSION STATE ---
if "capture_mode" not in st.session_state: st.session_state.capture_mode = "single"
if "show_enroll_modal" not in st.session_state: st.session_state.show_enroll_modal = False
if "camera_on" not in st.session_state: st.session_state.camera_on = False
if "last_capture_id" not in st.session_state: st.session_state.last_capture_id = None
if "result_img" not in st.session_state: st.session_state.result_img = None
if "result_faces" not in st.session_state: st.session_state.result_faces = []


def _init_enroll_modal():
    if st.session_state.show_enroll_modal:
        enroll_modal(prefill_name=st.session_state.get("enroll_prefill", ""))

def _st_image(img, **kwargs):
    try:
        st.image(img, use_container_width=True, **kwargs)
    except TypeError:
        st.image(img, width=None, **kwargs)

def _recognize_and_show(img_bytes: bytes) -> None:
    with st.spinner("Đang phân tích AI..."):
        try:
            resp = requests.post(f"{API_URL}/recognize", files={"image": ("capture.jpg", img_bytes, "image/jpeg")}, timeout=60)
        except requests.RequestException:
            st.error("Không kết nối được API. Hãy đảm bảo API Server đang chạy!")
            return

    if resp.status_code == 200:
        faces = resp.json()["faces"]
        if faces:
            st.session_state.result_img = draw_recognition_result(img_bytes, faces)
            st.session_state.result_faces = faces
        else:
            st.session_state.result_img = None
            st.session_state.result_faces = []
            st.warning("Không phát hiện khuôn mặt nào trong khung hình.")
    else:
        st.session_state.result_img = None
        st.session_state.result_faces = []
        st.error(api_error_message(resp))


# ==========================================
# PAGE 1: ĐIỂM DANH (GỘP LỊCH SỬ)
# ==========================================
def page_camera():
    st.markdown("## 🎯 Điểm Danh")
    st.caption("Hệ thống nhận diện và tự động ghi nhận vào CSDL")
    
    st.markdown("""<style>button[title="Clear photo"] { display: none !important; }</style>""", unsafe_allow_html=True)
    col_cam, col_info = st.columns([6.5, 3.5], gap="large")

    # --- CỘT TRÁI: CAMERA & KẾT QUẢ ---
    with col_cam:
        mode_col, btn_col, action_col = st.columns([2, 1, 1])
        with mode_col:
            st.session_state.capture_mode = st.radio("Chế độ", ["single", "timer"], format_func=lambda x: {"single": "Chụp đơn", "timer": "Hẹn giờ (3s)"}[x], horizontal=True, label_visibility="collapsed")
        with btn_col:
            if not st.session_state.camera_on:
                if st.button("⏺ Bật máy quét", type="primary", use_container_width=True):
                    st.session_state.camera_on = True
                    st.session_state.result_img = None
                    st.session_state.result_faces = []
                    st.rerun()
            else:
                if st.button("⏹ Tắt máy quét", use_container_width=True):
                    st.session_state.camera_on = False
                    st.session_state.last_capture_id = None
                    st.rerun()
        with action_col:
            if st.session_state.result_img is not None:
                if st.button("🔄 Quét lượt mới", type="primary", use_container_width=True):
                    st.session_state.result_img = None
                    st.session_state.result_faces = []
                    st.session_state.camera_on = True
                    st.session_state.last_capture_id = None
                    st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        photo = None
        if st.session_state.result_img is not None:
            _st_image(st.session_state.result_img)
        elif st.session_state.camera_on:
            photo = st.camera_input("Live feed", label_visibility="collapsed", key="main_camera")
            st.markdown("""<style>[data-testid="stCameraInputButton"] {background: linear-gradient(135deg, #0d47a1, #1976d2) !important; color: #ffffff !important; border-radius: 10px !important; width: 100% !important;} [data-testid="stCameraInputButton"]::before { content: "📸 "; }</style>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="cam-placeholder" style="height: 480px; display: flex; flex-direction: column; justify-content: center;"><div class="cam-placeholder-icon" style="font-size: 4rem;">📷</div><p style="font-size: 1.2rem;"><strong>Hệ thống đang nghỉ</strong></p><p>Nhấn <strong>Bật máy quét</strong> để bắt đầu điểm danh</p></div>""", unsafe_allow_html=True)

        if st.session_state.camera_on and photo is not None and st.session_state.result_img is None:
            capture_id = getattr(photo, "file_id", None) or hash(photo.getvalue())
            if capture_id != st.session_state.last_capture_id:
                st.session_state.last_capture_id = capture_id
                if st.session_state.capture_mode == "timer":
                    with st.spinner("Đang chuẩn bị... 3s"): time.sleep(3)
                _recognize_and_show(photo.getvalue())
                st.rerun()

    # --- CỘT PHẢI: THÔNG TIN TRẠNG THÁI & LỊCH SỬ ---
    with col_info:
        now = datetime.now()
        st.markdown(f"""<div style="text-align: right; color: #64748b; margin-bottom: 20px;"><h3 style="margin: 0; color: #0f172a;">{now.strftime('%H:%M')}</h3><p style="margin: 0; font-weight: 500;">{now.strftime('%d/%m/%Y')}</p></div>""", unsafe_allow_html=True)

        # 1. Thẻ trạng thái kết quả tức thời
        st.markdown("#### 👤 Lượt quét vừa rồi")
        if st.session_state.result_img is not None:
            if st.session_state.result_faces:
                for f in st.session_state.result_faces:
                    is_known = f["name"] != "Unknown"
                    color = "#059669" if is_known else "#dc2626"
                    bg = "#ecfdf5" if is_known else "#fef2f2"
                    icon = "✅ NHẬN DIỆN THÀNH CÔNG" if is_known else "⚠️ LẠ MẶT"
                    
                    att_msg = ""
                    if is_known and "attendance" in f:
                        att = f["attendance"]
                        if att.get("status") == "success":
                            badge = f"<span style='background:#16a34a; color:white; padding: 4px 8px; border-radius: 6px;'>{att.get('attendance_status')}</span>"
                            att_msg = f"<div style='margin-top:8px;'>Đã ghi nhận lúc: <b>{att.get('time')}</b> {badge}</div>"
                        elif att.get("status") == "cooldown":
                            att_msg = f"<div style='margin-top:8px; color: #d97706;'>⏳ {att.get('message')}</div>"

                    st.markdown(f"""
                        <div style="background:{bg}; border: 2px solid {color}; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <div style="font-size: 0.85rem; color: {color}; font-weight: 700; text-transform: uppercase; margin-bottom: 10px;">{icon}</div>
                            <div style="font-size: 1.8rem; color: #0f172a; font-weight: 800; margin-bottom: 5px;">{f["name"]}</div>
                            <div style="font-size: 0.95rem; color: #475569;">Độ tin cậy: <b>{f['confidence']*100:.1f}%</b></div>
                            {att_msg}
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Không nhận diện được.")
        else:
            st.markdown("""<div style="background:#f8fafc; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 15px;"><div style="font-size: 2rem; margin-bottom: 10px;">👀</div><div style="font-size: 1rem; color: #64748b; font-weight: 600;">Chờ điểm danh...</div></div>""", unsafe_allow_html=True)

        st.divider()

        # 2. Timeline Điểm danh hôm nay (Kéo trực tiếp từ API)
        st.markdown("#### 📋 Điểm danh hôm nay")
        today_str = now.strftime("%Y-%m-%d")
        try:
            resp = requests.get(f"{API_URL}/attendance?date={today_str}", timeout=5)
            if resp.status_code == 200:
                logs = resp.json().get("logs", [])
                if not logs:
                    st.info("Chưa có ai điểm danh trong hôm nay.")
                else:
                    # Danh sách cuộn (Scrollable timeline)
                    st.markdown("<div style='max-height: 300px; overflow-y: auto; padding-right: 10px;'>", unsafe_allow_html=True)
                    for log in logs:
                        time_str = pd.to_datetime(log['timestamp']).strftime('%H:%M:%S')
                        name = log['name']
                        status = log['status']
                        
                        if status == "Đúng giờ": bg_c = "#16a34a"
                        elif status == "Đi muộn": bg_c = "#ca8a04"
                        else: bg_c = "#64748b"
                        
                        st.markdown(f"""
                            <div style="display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid #f1f5f9;">
                                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: {bg_c}; margin-right: 15px; flex-shrink: 0;"></div>
                                <div style="flex-grow: 1;">
                                    <div style="font-weight: 700; color: #0f172a; font-size: 0.95rem;">{name}</div>
                                    <div style="font-weight: 600; color: {bg_c}; font-size: 0.75rem;">{status}</div>
                                </div>
                                <div style="font-weight: 600; color: #64748b; font-size: 0.85rem;">{time_str}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    df = pd.DataFrame(logs)
                    df["Thời gian"] = pd.to_datetime(df["timestamp"]).dt.strftime("%d/%m/%Y %H:%M:%S")
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 Tải báo cáo hôm nay (CSV)", 
                        data=csv, 
                        file_name=f"diem_danh_{today_str}.csv", 
                        mime="text/csv", 
                        use_container_width=True
                    )
            else:
                st.error(f"Lỗi máy chủ! Mã HTTP: {resp.status_code}. Chi tiết: {resp.text}")
        except Exception:
            st.caption("Đang chờ kết nối máy chủ...")


# ==========================================
# PAGE 2: QUẢN LÝ NHÂN SỰ
# ==========================================
def page_dashboard():
    st.markdown("## 👥 Quản lý Nhân sự")
    st.caption("Quản lý danh sách khuôn mặt và thêm người mới.")
    
    people_raw = api_get_people()
    if people_raw is None:
        st.error(f"Không kết nối API tại **{API_URL}**. Chạy: `run_api.bat`")
        return

    m1, m2, m3 = st.columns(3)
    total = len(people_raw)
    stable = sum(1 for p in people_raw if p.get("status") == "stable")
    m1.metric("👥 Tổng số", total)
    m2.metric("🟢 Ổn định", stable)
    m3.metric("🟡 Cần cập nhật", total - stable)
    st.divider()

    c_add, c_search, _, _ = st.columns([1.5, 2, 1.5, 1.5])
    with c_add:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Thêm người mới", type="primary", use_container_width=True):
            open_enroll_modal()
            st.rerun()
    with c_search:
        search = st.text_input("🔍 Tìm kiếm", placeholder="Nhập tên...")

    people = filter_people(people_raw, search=search, date_from=None, date_to=None)

    def on_update(n): open_enroll_modal(n); st.rerun()
    def on_delete(n):
        if requests.delete(f"{API_URL}/people/{quote(n, safe='')}").status_code == 200:
            st.toast(f"Đã xóa: {n}"); st.rerun()

    render_user_table(people, on_update=on_update, on_delete=on_delete)

# ==========================================
# PAGE 3: LỊCH SỬ ĐIỂM DANH
# ==========================================
def page_attendance_history():
    st.markdown("## 📊 Lịch sử Điểm danh")
    st.caption("Xem và xuất báo cáo điểm danh theo ngày.")

    col_date, col_btn, _ = st.columns([2, 1, 3])
    with col_date:
        selected_date = st.date_input("Chọn ngày", value=datetime.now().date())
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        search_clicked = st.button("🔍 Xem", type="primary", use_container_width=True)

    date_str = selected_date.strftime("%Y-%m-%d")

    try:
        resp = requests.get(f"{API_URL}/attendance?date={date_str}", timeout=5)
    except requests.RequestException:
        st.error("Không kết nối được API.")
        return

    if resp.status_code != 200:
        st.error(f"Lỗi máy chủ! HTTP {resp.status_code}")
        return

    logs = resp.json().get("logs", [])

    # --- Metrics ---
    total = len(logs)
    on_time = sum(1 for l in logs if l["status"] == "Đúng giờ")
    late = sum(1 for l in logs if l["status"] == "Đi muộn")

    m1, m2, m3 = st.columns(3)
    m1.metric("📋 Tổng điểm danh", total)
    m2.metric("✅ Đúng giờ", on_time)
    m3.metric("⏰ Đi muộn", late)
    st.divider()

    if not logs:
        st.info(f"Không có dữ liệu điểm danh ngày {selected_date.strftime('%d/%m/%Y')}.")
        return

    # --- Bảng dữ liệu ---
    df = pd.DataFrame(logs)
    df["Thời gian"] = pd.to_datetime(df["timestamp"]).dt.strftime("%H:%M:%S")
    df["Độ tin cậy"] = df["confidence"].apply(lambda x: f"{x*100:.1f}%")
    df_display = df[["name", "Thời gian", "status", "Độ tin cậy"]].rename(columns={
        "name": "Họ tên",
        "status": "Trạng thái",
    })
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # --- Export CSV ---
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 Xuất CSV",
        data=csv,
        file_name=f"diem_danh_{date_str}.csv",
        mime="text/csv",
    )

# ── Shell ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Face Check-in", page_icon="🧑", layout="wide", initial_sidebar_state="expanded")
st.markdown(MODERN_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🏢 Hệ Thống Nhận Diện")
    st.divider()
    # Rút gọn lại chỉ còn 2 tab
    page = st.radio("Điều hướng", ["🎯 Điểm Danh", "👥 Quản lý Nhân Sự", "📊 Lịch sử Điểm danh"], label_visibility="collapsed")
    st.divider()
    ok, err = api_health()
    color = "#059669" if ok else "#dc2626"
    label = "● Trạng thái: ỔN ĐỊNH" if ok else "○ MẤT KẾT NỐI"
    st.markdown(f"<p style='color:{color};font-weight:600;font-size:0.85rem;'>{label}<br><span style='color:#64748b;font-weight:400;'>{API_URL}</span></p>", unsafe_allow_html=True)

if page.startswith("🎯"): page_camera()
elif page.startswith("📊"): page_attendance_history()
else: page_dashboard()

_init_enroll_modal()
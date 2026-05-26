import time

import cv2

from config import ENROLL_DURATION_SEC


def record_webcam_video(
    output_path: str,
    duration_sec: int = ENROLL_DURATION_SEC,
    camera_index: int = 0,
    fps: int = 20,
) -> dict:
    """
    Ghi video từ webcam máy chủ (phù hợp khi chạy UI/API cục bộ).
    Trả về dict success, message, duration.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return {
            "success": False,
            "message": "Không mở được webcam. Kiểm tra quyền camera hoặc thử upload video.",
            "duration": 0,
        }

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frames_written = 0
    target_frames = duration_sec * fps
    start = time.time()

    while frames_written < target_frames:
        ret, frame = cap.read()
        if not ret:
            break
        writer.write(frame)
        frames_written += 1

    cap.release()
    writer.release()
    elapsed = round(time.time() - start, 1)

    if frames_written == 0:
        return {
            "success": False,
            "message": "Không đọc được frame từ webcam.",
            "duration": elapsed,
        }

    return {
        "success": True,
        "message": f"Đã ghi {frames_written} frames ({elapsed}s)",
        "duration": elapsed,
    }

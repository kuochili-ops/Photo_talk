import io
import time
import requests
import streamlit as st
from PIL import Image

st.set_page_config(page_title="人像說話影片生成器", page_icon="🎬", layout="centered")

# 側邊欄：設定
st.sidebar.title("設定")
st.sidebar.markdown("選擇語音與語言。")
voice = st.sidebar.selectbox("語音", ["女聲溫暖", "女聲中性", "男聲溫暖", "男聲中性"])
language = st.sidebar.selectbox("語言", ["zh-TW", "zh-CN", "en-US", "ja-JP"])
max_duration = st.sidebar.slider("影片最長秒數", 3, 60, 20)

st.title("🎬 人像說話影片生成器")
st.caption("上傳人像照片，輸入文字，生成一段人像說話影片。")

# 使用者輸入
img_file = st.file_uploader("上傳人像照片 (JPG/PNG)", type=["jpg", "jpeg", "png"])
text = st.text_area("輸入要說的文字", placeholder="例如：大家好，歡迎來到我的頻道。", height=120)

# 驗證
can_run = img_file is not None and (text is not None and text.strip() != "")

# 顯示影片與下載
def show_video_and_download(video_bytes: bytes, filename: str = "talking_photo.mp4"):
    st.video(video_bytes)
    st.download_button(
        label="下載影片",
        data=video_bytes,
        file_name=filename,
        mime="video/mp4",
        use_container_width=True
    )

# API 設定
API_KEY = st.secrets.get("TALKING_AVATAR_API_KEY")
API_BASE = st.secrets.get("TALKING_AVATAR_API_BASE")

def generate_talking_video(image_bytes: bytes, text: str, voice: str, language: str, max_duration: int) -> bytes:
    if API_KEY is None:
        raise RuntimeError("缺少 TALKING_AVATAR_API_KEY，請在 Streamlit Cloud Secrets 設定。")
    if API_BASE is None:
        raise RuntimeError("缺少 TALKING_AVATAR_API_BASE，請在 Streamlit Cloud Secrets 設定。")

    url = f"{API_BASE}/generate"  # 請依照實際 API 修改
    headers = {"Authorization": f"Bearer {API_KEY}"}

    files = {"image": ("portrait.png", image_bytes, "image/png")}
    data = {
        "text": text,
        "voice": voice,
        "language": language,
        "max_duration": max_duration,
    }

    resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
    resp.raise_for_status()
    payload = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else None

    if payload and "video_url" in payload:
        video_url = payload["video_url"]
        video_resp = requests.get(video_url, timeout=180)
        video_resp.raise_for_status()
        return video_resp.content

    if payload and "job_id" in payload:
        job_id = payload["job_id"]
        status_url = f"{API_BASE}/jobs/{job_id}"
        for _ in range(120):
            status_resp = requests.get(status_url, headers=headers, timeout=30)
            status_resp.raise_for_status()
            status_json = status_resp.json()
            state = status_json.get("status")
            if state in ("succeeded", "completed"):
                video_url = status_json.get("video_url")
                video_resp = requests.get(video_url, timeout=180)
                video_resp.raise_for_status()
                return video_resp.content
            elif state in ("failed", "error"):
                raise RuntimeError(status_json.get("message", "生成失敗"))
            time.sleep(2)
        raise TimeoutError("生成影片逾時，請嘗試縮短文字或更換語音。")

    if resp.content and resp.headers.get("Content-Type", "").startswith("video/"):
        return resp.content

    raise RuntimeError("API 回傳格式不符合預期，請檢查供應商文件。")

# 主流程
if st.button("生成影片", type="primary", disabled=not can_run):
    try:
        image = Image.open(img_file).convert("RGB")
        st.image(image, caption="已上傳人像", use_container_width=True)

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        with st.spinner("正在生成影片，請稍候..."):
            video_bytes = generate_talking_video(
                image_bytes=img_bytes,
                text=text.strip(),
                voice=voice,
                language=language,
                max_duration=max_duration
            )

        st.success("影片生成完成！")
        show_video_and_download(video_bytes)

    except Exception as e:
        st.error(f"錯誤：{e}")
        st.stop()

st.markdown("---")
st.markdown("提示：請使用正面、光線充足的人像照片，效果最佳。")

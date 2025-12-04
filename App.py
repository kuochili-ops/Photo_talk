import io
import time
import requests
import streamlit as st
from PIL import Image
import openai
print(openai.__version__)
st.set_page_config(page_title="人像說話影片生成器", page_icon="🎬", layout="centered")

st.title("🎬 人像說話影片生成器")
st.caption("上傳人像照片，輸入文字，生成一段人像說話影片。")

# 使用者輸入
img_file = st.file_uploader("上傳人像照片 (JPG/PNG)", type=["jpg", "jpeg", "png"])
text = st.text_area("輸入要說的文字", placeholder="例如：大家好，歡迎來到我的頻道。", height=120)

# 語音選擇
voice = st.selectbox("選擇語音風格", ["alloy", "verse", "sage"])

can_run = img_file is not None and (text is not None and text.strip() != "")

# Secrets
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
DID_API_KEY = st.secrets.get("DID_API_KEY")
DID_API_BASE = "https://api.d-id.com/v1"

if not OPENAI_API_KEY or not DID_API_KEY:
    st.error("請先在 Streamlit Secrets 設定 OPENAI_API_KEY 和 DID_API_KEY！")
    st.stop()

openai.api_key = OPENAI_API_KEY

def generate_audio_openai(text: str, voice: str = "alloy") -> bytes:
    """使用 OpenAI TTS 生成語音"""
    response = openai.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )
    return response.read()

def generate_talking_video(image_bytes: bytes, audio_bytes: bytes) -> bytes:
    """呼叫 D-ID API 生成人像說話影片"""
    url = f"{DID_API_BASE}/talks"
    headers = {"Authorization": f"Bearer {DID_API_KEY}"}
    files = {
        "source_image": ("portrait.png", image_bytes, "image/png"),
        "audio": ("speech.wav", audio_bytes, "audio/wav"),
    }
    resp = requests.post(url, headers=headers, files=files, timeout=120)
    resp.raise_for_status()
    payload = resp.json()

    job_id = payload.get("id")
    status_url = f"{DID_API_BASE}/talks/{job_id}"

    progress_bar = st.progress(0)
    for i in range(60):
        status_resp = requests.get(status_url, headers=headers)
        status_resp.raise_for_status()
        status_json = status_resp.json()
        state = status_json.get("status")
        progress_bar.progress(int((i+1)/60*100))
        if state == "done":
            video_url = status_json.get("result_url")
            video_resp = requests.get(video_url)
            video_resp.raise_for_status()
            return video_resp.content
        elif state == "error":
            raise RuntimeError(status_json.get("error", "生成失敗"))
        time.sleep(2)

    raise TimeoutError("生成影片逾時")

def show_video_and_download(video_bytes: bytes, filename: str = "talking_photo.mp4"):
    st.video(video_bytes)
    st.download_button(
        label="下載影片",
        data=video_bytes,
        file_name=filename,
        mime="video/mp4",
        use_container_width=True
    )

if st.button("生成影片", type="primary", disabled=not can_run):
    try:
        image = Image.open(img_file).convert("RGB")
        st.image(image, caption="已上傳人像", use_container_width=True)

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        with st.spinner("正在生成語音..."):
            audio_bytes = generate_audio_openai(text.strip(), voice=voice)

        st.audio(audio_bytes, format="audio/wav")

        with st.spinner("正在生成影片..."):
            video_bytes = generate_talking_video(img_bytes, audio_bytes)

        st.success("影片生成完成！")
        show_video_and_download(video_bytes)

    except Exception as e:
        st.error(f"錯誤：{e}")
        st.stop()

st.markdown("---")
st.markdown("提示：請使用正面、光線充足的人像照片，效果最佳。")

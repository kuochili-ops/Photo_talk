import io
import time
import requests
import streamlit as st
from PIL import Image

st.set_page_config(page_title="人像說話影片生成器", page_icon="🎬", layout="centered")

st.title("🎬 人像說話影片生成器")
st.caption("上傳人像照片，輸入文字，生成一段人像說話影片。")

# 使用者輸入
img_url = st.text_input("輸入人像圖片 URL (必須可公開存取)")
text = st.text_area("輸入要說的文字", placeholder="例如：大家好，歡迎來到我的頻道。", height=120)

# 語音選擇 (Azure 提供多種 voice)
voice = st.selectbox("選擇語音風格", ["zh-TW-HsiaoYuNeural", "zh-TW-YatingNeural", "en-US-JennyNeural"])

can_run = img_url.strip() != "" and (text is not None and text.strip() != "")

# Secrets
AZURE_SPEECH_KEY = st.secrets.get("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = st.secrets.get("AZURE_SPEECH_REGION", "japaneast")
DID_API_KEY = st.secrets.get("DID_API_KEY")

if not AZURE_SPEECH_KEY or not DID_API_KEY:
    st.error("請先在 Streamlit Secrets 設定 AZURE_SPEECH_KEY、AZURE_SPEECH_REGION 和 DID_API_KEY！")
    st.stop()

def generate_audio_azure(text: str, voice: str = "zh-TW-HsiaoYuNeural") -> str:
    """使用 Azure Speech Service 生成語音，並回傳可存取的 URL"""
    endpoint = f"https://{AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm"
    }
    ssml = f"""
    <speak version='1.0' xml:lang='zh-TW'>
      <voice name='{voice}'>
        {text}
      </voice>
    </speak>
    """
    resp = requests.post(endpoint, headers=headers, data=ssml.encode("utf-8"))
    resp.raise_for_status()

    # ⚠️ 這裡需要把音訊檔上傳到一個可公開存取的 URL
    # 範例：先存到本地，再手動上傳到 GitHub/S3/Google Drive
    with open("speech.wav", "wb") as f:
        f.write(resp.content)

    st.audio(resp.content, format="audio/wav")
    st.warning("請將 speech.wav 上傳到雲端並取得公開 URL，然後貼到下方欄位。")
    return None  # 暫時不回傳 URL，需人工上傳

def generate_talking_video(image_url: str, audio_url: str) -> str:
    """呼叫 D-ID API 生成人像說話影片"""
    url = "https://api.d-id.com/talks"
    headers = {"Authorization": f"Bearer {DID_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "source_url": image_url,
        "script": {
            "type": "audio",
            "audio_url": audio_url
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    job_id = resp.json().get("id")

    status_url = f"https://api.d-id.com/talks/{job_id}"
    progress_bar = st.progress(0)

    for i in range(60):
        status_resp = requests.get(status_url, headers=headers)
        status_resp.raise_for_status()
        status_json = status_resp.json()
        state = status_json.get("status")
        progress_bar.progress(int((i+1)/60*100))
        if state == "done":
            return status_json.get("result_url")
        elif state == "error":
            raise RuntimeError(status_json.get("error", "生成失敗"))
        time.sleep(2)

    raise TimeoutError("生成影片逾時")

if st.button("生成影片", type="primary", disabled=not can_run):
    try:
        with st.spinner("正在生成語音..."):
            generate_audio_azure(text.strip(), voice=voice)

        audio_url = st.text_input("請輸入剛剛上傳的 speech.wav 公開 URL")
        if audio_url.strip() != "":
            with st.spinner("正在生成影片..."):
                video_url = generate_talking_video(img_url.strip(), audio_url.strip())
            st.success("影片生成完成！")
            st.video(video_url)
            st.markdown(f"[下載影片]({video_url})")

    except Exception as e:
        st.error(f"錯誤：{e}")
        st.stop()

st.markdown("---")
st.markdown("提示：請使用正面、光線充足的人像照片，效果最佳。")        "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm"
    }
    ssml = f"""
    <speak version='1.0' xml:lang='zh-TW'>
      <voice name='{voice}'>
        {text}
      </voice>
    </speak>
    """
    resp = requests.post(endpoint, headers=headers, data=ssml.encode("utf-8"))
    resp.raise_for_status()
    return resp.content

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
        width="stretch"
    )

if st.button("生成影片", type="primary", disabled=not can_run):
    try:
        image = Image.open(img_file).convert("RGB")
        st.image(image, caption="已上傳人像", width="stretch")

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        with st.spinner("正在生成語音..."):
            audio_bytes = generate_audio_azure(text.strip(), voice=voice)

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

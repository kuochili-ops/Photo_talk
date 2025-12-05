import time
import requests
import streamlit as st
st.write("Azure Key:", "已設定" if "AZURE_SPEECH_KEY" in st.secrets else "缺失")
st.write("Region:", st.secrets.get("AZURE_SPEECH_REGION", "未設定"))
st.write("D-ID Key:", "已設定" if "DID_API_KEY" in st.secrets else "缺失")
st.set_page_config(page_title="人像說話影片生成器", page_icon="🎬", layout="centered")

st.title("🎬 人像說話影片生成器")
st.caption("輸入人像圖片 URL，輸入文字，生成一段人像說話影片。")

# 使用者輸入
img_url = st.text_input("輸入人像圖片 URL (必須可公開存取)")
text = st.text_area("輸入要說的文字", placeholder="例如：大家好，歡迎來到我的頻道。", height=120)

# 語音選擇 (Azure 提供多種 voice)
voice = st.selectbox("選擇語音風格", ["zh-TW-HsiaoYuNeural", "zh-TW-YatingNeural", "en-US-JennyNeural"])

can_run = img_url.strip() != "" and (text is not None and text.strip() != "")

# Secrets 檢查
missing_keys = []
for key in ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "DID_API_KEY"]:
    if key not in st.secrets:
        missing_keys.append(key)

if missing_keys:
    st.error(f"缺少必要的 Secrets: {', '.join(missing_keys)}\n請在 .streamlit/secrets.toml 或 Cloud Secrets 設定這些金鑰。")
    st.stop()

AZURE_SPEECH_KEY = st.secrets["AZURE_SPEECH_KEY"]
AZURE_SPEECH_REGION = st.secrets["AZURE_SPEECH_REGION"]
DID_API_KEY = st.secrets["DID_API_KEY"]

def generate_audio_azure(text: str, voice: str = "zh-TW-HsiaoYuNeural") -> bytes:
    """使用 Azure Speech Service 生成語音"""
    endpoint = f"ㄣㄣ = f"https://<region>.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
    headers = {n
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
    return resp.content

def generate_talking_video(image_url: str, audio_url: str) -> str:
    """呼叫 D-ID API 生成人像說話影片 (使用 URL)"""
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
            audio_bytes = generate_audio_azure(text.strip(), voice=voice)

        # ⚠️ 這裡需要把 speech.wav 上傳到雲端，取得公開 URL
        with open("speech.wav", "wb") as f:
            f.write(audio_bytes)
        st.audio(audio_bytes, format="audio/wav")
        st.warning("請將 speech.wav 上傳到雲端並取得公開 URL，然後貼到下方欄位。")

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
st.markdown("提示：請使用正面、光線充足的人像照片，效果最佳。")

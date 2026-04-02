import os
import json
import requests
import yaml
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, "../..", ".env")
load_dotenv(dotenv_path)

# ================= 动态读取配置 =================
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "../..", "data", ".config.yaml")

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
        minimax_config = config_data.get("TTS", {}).get("MinimaxTTSHTTPStream", {})
        
        GROUP_ID = minimax_config.get("group_id")
        API_KEY = minimax_config.get("api_key")
        
        if not GROUP_ID or not API_KEY:
            raise ValueError("在 .config.yaml 中找不到 MiniMax 的 group_id 或 api_key！")
except Exception as e:
    print(f"[错误] 读取配置文件失败: {e}")
    exit(1)

print(f"[*] 成功从配置文件加载 Group ID，准备调用语音合成接口...")

# ================= 语音合成参数配置 =================
# 你刚刚复刻成功的专属音色 ID
VOICE_ID = os.getenv("VOICE_ID") 

# 你想让这个音色说的话
TEXT_TO_SPEAK = os.getenv("VOICE_DOWNLOAD_TEXT")

# 指定模型，直接读取配置中的模型，若没有则默认使用 speech-02-turbo
MODEL = minimax_config.get("model", "speech-02-turbo")

# 输出音频的保存路径与名称
OUTPUT_FILE = os.getenv("VOICE_DOWNLOAD_OUTPUT")
# =================================================

def generate_speech():
    url = f"https://api.minimax.io/v1/t2a_v2?GroupId={GROUP_ID}"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate"  # <--- 新增这行，强制告诉服务器不要用 br 压缩
    }
    
    # 构造请求数据
    payload = {
        "model": MODEL,
        "text": TEXT_TO_SPEAK,
        "stream": False,  # 这里使用非流式请求，一次性生成完整音频以便保存为文件
        "voice_setting": {
            "voice_id": VOICE_ID,
            "speed": 1.0,   # 语速 (通常在 0.5 - 2.0 之间)
            "vol": 1.0,     # 音量 (通常在 0.1 - 10.0 之间)
            "pitch": 0      # 语调 (-12 到 12 之间，0为默认)
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",  # 要求 API 返回 mp3 格式
            "channel": 1
        }
    }
    
    print(f"[*] 正在请求 MiniMax API 合成语音，请稍候...")
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code != 200:
        print(f"[错误] HTTP 请求失败! 状态码: {response.status_code}, 返回: {response.text}")
        return
        
    resp_json = response.json()
    base_resp = resp_json.get("base_resp", {})
    
    if base_resp.get("status_code") != 0:
        print(f"[错误] 业务请求失败! 错误信息: {base_resp}")
        return
        
    # 获取音频十六进制字符串数据
    audio_hex = resp_json.get("data", {}).get("audio")
    if not audio_hex:
        print(f"[错误] 返回结果中没有音频数据！")
        return
        
    # MiniMax API 返回的音频数据是十六进制的，需要先转为字节流再写入文件
    audio_bytes = bytes.fromhex(audio_hex)
    with open(OUTPUT_FILE, "wb") as f:
        f.write(audio_bytes)
        
    print(f"[+] 语音合成成功！")
    print(f"[+] 音频已保存至当前目录下的: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_speech()
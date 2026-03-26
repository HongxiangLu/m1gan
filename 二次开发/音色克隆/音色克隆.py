import os
import json
import requests
import time
import yaml
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 定位到项目根目录 (二次开发/音色克隆/../../.env)
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

print(f"[*] 成功从配置文件加载 Group ID: {GROUP_ID}")

# ================= 配置区域 =================
# 1. 基础复刻音频 (提供基础音色，10秒到5分钟)
AUDIO_FILE_PATH = os.getenv("VOICE_CLONE_AUDIO_FILE")

# 2. 示例情感音频 (可选，用于增强特定情绪，时长需小于 8 秒)
PROMPT_AUDIO_PATH = os.getenv("VOICE_CLONE_PROMPT_AUDIO")

# 3. 示例音频对应的文本
PROMPT_TEXT = os.getenv("VOICE_CLONE_PROMPT_TEXT")

# 新音色的名字 (长度8-256，只能包含字母、数字、_、-)
CUSTOM_VOICE_ID = os.getenv("VOICE_ID") 

# ==========================================

# Minimax海外版平台
BASE_URL = "https://api.minimax.io"
HEADERS_BASE = {
    "Authorization": f"Bearer {API_KEY}"
}

def upload_audio_file(file_path, purpose="voice_clone"):
    """
    通用上传接口：用于上传复刻音频 或 示例音频
    """
    print(f"[*] 正在上传音频文件: {file_path} ...")
    url = f"{BASE_URL}/v1/files/upload?GroupId={GROUP_ID}"
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到音频文件: {file_path}")

    # 对于复刻和示例音频，purpose分别可能不同，不过根据 MiniMax 文档，上传音频一般固定传 voice_clone
    payload = {"purpose": purpose}
    file_name = os.path.basename(file_path)
    
    with open(file_path, "rb") as f:
        # 简单通过后缀判断 content-type
        content_type = "audio/mpeg" if file_path.lower().endswith('.mp3') else "audio/wav"
        files = [("file", (file_name, f, content_type))]
        response = requests.post(url, headers=HEADERS_BASE, data=payload, files=files)
        
    if response.status_code != 200:
        raise Exception(f"上传失败! 状态码: {response.status_code}, 返回: {response.text}")
        
    resp_json = response.json()
    base_resp = resp_json.get("base_resp", {})
    if base_resp.get("status_code") != 0:
         raise Exception(f"上传业务失败! {base_resp}")
         
    file_id = resp_json.get("file", {}).get("file_id")
    print(f"[+] 上传成功! 获取到 file_id: {file_id}")
    return file_id

def clone_voice(base_file_id, voice_id, prompt_file_id="", prompt_text=""):
    """
    执行复刻请求，支持传入 clone_prompt 以增强情绪
    """
    print(f"[*] 正在请求复刻音色，分配的 voice_id 为: {voice_id} ...")
    url = f"{BASE_URL}/v1/voice_clone?GroupId={GROUP_ID}"
    
    headers = HEADERS_BASE.copy()
    headers["Content-Type"] = "application/json"
    
    payload = {
        "voice_id": voice_id,
        "file_id": base_file_id
    }

    # 如果有示例情感音频，则封装 clone_prompt
    if prompt_file_id:
        print(f"[*] 携带情感增强示例 (Prompt Audio ID: {prompt_file_id})")
        payload["clone_prompt"] = {
            "prompt_audio": prompt_file_id,
            "prompt_text": prompt_text
        }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code != 200:
        raise Exception(f"复刻请求失败! 状态码: {response.status_code}, 返回: {response.text}")
        
    resp_json = response.json()
    base_resp = resp_json.get("base_resp", {})
    if base_resp.get("status_code") != 0:
         raise Exception(f"复刻业务失败! {base_resp}")
         
    print(f"[+] 音色复刻成功!")
    print("-" * 40)
    print(f"你的专属音色 ID (voice_id): {voice_id}")
    print("请将该 voice_id 填入你项目的 .config.yaml 中。")
    print("-" * 40)
    
    return voice_id

if __name__ == "__main__":
    try:
        # 1. 上传基础复刻音频
        cloned_file_id = upload_audio_file(AUDIO_FILE_PATH, purpose="voice_clone")
        time.sleep(1)

        # 2. 如果配置了示例音频，上传示例情感音频
        prompt_file_id = ""
        if PROMPT_AUDIO_PATH and os.path.exists(PROMPT_AUDIO_PATH):
            # 注意这里：purpose 必须传 "prompt_audio"，不能传 "voice_clone"
            prompt_file_id = upload_audio_file(PROMPT_AUDIO_PATH, purpose="prompt_audio")
            time.sleep(1)
        
        # 3. 执行克隆
        clone_voice(cloned_file_id, CUSTOM_VOICE_ID, prompt_file_id, PROMPT_TEXT)
        
    except Exception as e:
        print(f"\n[错误] 发生异常: {e}")

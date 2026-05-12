"""
produce.py

本脚本基于 Google Gemini API (TTS) 批量将剧本文字转化为分角色语音并最终拼接为完整的音频故事。
主要流程：
1. 扫描配置的剧本文件夹（按照数字顺序读取 TXT 分段脚本）。
2. 调用 Gemini API 将文本流式转化为 PCM 音频数据。
3. 利用二进制拼接将多段短音频数据合并为完整的剧情音频。
4. 封装 WAV 头信息并持久化输出至本地。

Date: 2026-05
"""

import os
import wave
from google import genai
from google.genai import types

# ==========================================
# 1. 初始化环境变量与 Gemini 客户端
# ==========================================

# 注意：在生产环境中，请确保不在代码中硬编码 API Key，而是依赖环境变量注入
os.environ['GEMINI_API_KEY'] = ''
client = genai.Client()

def wave_file(filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    """
    将原生 PCM 音频数据封装为 WAV 格式并持久化写入文件。
    
    Args:
        filename (str): 输出的 WAV 音频文件路径。
        pcm (bytes): 原始的 PCM 音频二进制数据。
        channels (int, optional): 音频通道数。默认为 1 (单声道)。
        rate (int, optional): 采样率 (Hz)。Gemini TTS 默认输出为 24000 Hz。
        sample_width (int, optional): 采样位数 (字节)。2 代表 16-bit 深度。
    """
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# ==========================================
# 2. 加载基础系统提示词
# ==========================================
# prompt.txt 包含对大模型 TTS 引擎的角色设定和音色指导规则
with open("prompt.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

# ==========================================
# 3. 配置双人发音参数与语音特征
# ==========================================
# 在此配置不同角色对应的预置语音模型。
# '老师' 绑定了 'Orus' (成熟稳重)，'学生' 绑定了 'Puck' (年轻活泼)。
config = types.GenerateContentConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
            speaker_voice_configs=[
                types.SpeakerVoiceConfig(
                    speaker="老师",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Orus")
                    )
                ),
                types.SpeakerVoiceConfig(
                    speaker="学生",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                    )
                )
            ]
        )
    )
)

# ==========================================
# 4. 核心处理流程：批量扫描、生成与合并
# ==========================================
scripts_dir = "scripts"
audios_dir = "audios"

# 若目标输出目录不存在，则进行创建，保证 IO 安全
if not os.path.exists(audios_dir):
    os.makedirs(audios_dir)

# 遍历 scripts 目录下所有的故事子文件夹
for story_name in os.listdir(scripts_dir):
    story_dir = os.path.join(scripts_dir, story_name)
    if not os.path.isdir(story_dir):
        continue
        
    print(f"正在处理故事：{story_name}")
    
    # 提取当前故事文件夹内所有的 TXT 剧本段落，并严格依据文件名数字进行升序排列
    # 从而保证剧情叙述的连贯性和时序性
    txt_files = [f for f in os.listdir(story_dir) if f.endswith('.txt')]
    txt_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
    
    # 用于在内存中积攒该故事下所有分段的音频二进制数据
    merged_pcm = b""  
    
    for txt_file in txt_files:
        txt_path = os.path.join(story_dir, txt_file)
        with open(txt_path, "r", encoding="utf-8") as f:
            script_part = f.read()
            
        print(f"  正在生成音频段：{txt_file}")
        try:
            # 携带全局提示词与当前分段剧本调用 API 进行语音合成
            response = client.models.generate_content(
                model="gemini-3.1-flash-tts-preview",
                contents=prompt + "\n" + script_part,
                config=config
            )
            # 提取返回 payload 中的 PCM 音频数据部分并拼接到主字节流中
            data = response.candidates[0].content.parts[0].inline_data.data
            merged_pcm += data
        except Exception as e:
            # 加入异常捕获机制，防止某段因网络或限流问题导致整个流程中断
            print(f"  生成音频段 {txt_file} 时出错: {e}")
        
    # ==========================================
    # 5. 落盘存储合并完成的故事音频
    # ==========================================
    if merged_pcm:
        filename = os.path.join(audios_dir, f"{story_name}.wav")
        wave_file(filename, merged_pcm)
        print(f"🎉 故事【{story_name}】音频合并完毕，已保存为：{filename}\n")
    else:
        print(f"⚠️ 故事【{story_name}】没有生成任何音频数据。\n")

print("全部故事音频处理完成！")
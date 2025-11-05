#!/usr/bin/env python3
"""
火山引擎 TTS 交互式合成（持续输入模式）
- 基于 Volcengine 官方协议
- 每次输入自动合成并播放
- 输入 'quit' 退出
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../语音'))

import asyncio
import json
import uuid
import websockets
import pyaudio
from protocols import EventType, MsgType, full_client_request, receive_message

# ==================== 配置 ====================
APP_ID = "2634661217"
ACCESS_TOKEN = "0im2q3lyhxDTTt5GXNtzmNSj2-I_Lb3b"
VOICE_TYPE = "zh_male_naiqimengwa_mars_bigtts"  # 可选其他音色
TTS_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/unidirectional/stream"
SAMPLE_RATE = 24000
# =================================================

def get_resource_id(voice: str) -> str:
    """根据音色选择Resource ID"""
    if voice.startswith("S_"):
        return "volc.megatts.default"
    return "volc.service_type.10029"

async def tts_synthesize(text: str) -> bytes:
    """
    使用火山引擎TTS合成语音
    返回PCM音频数据
    """
    headers = {
        "X-Api-App-Key": APP_ID,
        "X-Api-Access-Key": ACCESS_TOKEN,
        "X-Api-Resource-Id": get_resource_id(VOICE_TYPE),
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }

    try:
        websocket = await websockets.connect(
            TTS_ENDPOINT, 
            extra_headers=headers, 
            max_size=10 * 1024 * 1024
        )
        
        # 准备请求
        request = {
            "user": {"uid": str(uuid.uuid4())},
            "req_params": {
                "speaker": VOICE_TYPE,
                "audio_params": {
                    "format": "pcm",
                    "sample_rate": SAMPLE_RATE,
                    "enable_timestamp": False,
                },
                "text": text,
                "additions": json.dumps({"disable_markdown_filter": False}),
            },
        }
        
        # 发送请求
        await full_client_request(websocket, json.dumps(request).encode())
        
        # 接收音频数据
        audio_data = bytearray()
        while True:
            msg = await receive_message(websocket)
            
            if msg.type == MsgType.FullServerResponse:
                if msg.event == EventType.SessionFinished:
                    break
            elif msg.type == MsgType.AudioOnlyServer:
                audio_data.extend(msg.payload)
            else:
                print(f"⚠️  TTS错误: {msg}")
                break
        
        await websocket.close()
        return bytes(audio_data)
        
    except Exception as e:
        print(f"❌ TTS合成失败: {e}")
        return b""

def play_audio(audio_data: bytes):
    """播放PCM音频数据"""
    if not audio_data:
        print("⚠️  没有音频数据可播放")
        return
    
    p = pyaudio.PyAudio()
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=1024
        )
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()
    except Exception as e:
        print(f"❌ 播放失败: {e}")
    finally:
        p.terminate()

async def main():
    print("=" * 60)
    print("🎙️  火山引擎 TTS 交互式合成")
    print("=" * 60)
    print(f"音色: {VOICE_TYPE}")
    print(f"采样率: {SAMPLE_RATE} Hz")
    print("=" * 60)
    print("💡 输入文本后按回车合成，输入 'quit' 退出\n")
    
    # 屏蔽websockets的INFO日志
    import logging
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("protocols.protocols").setLevel(logging.WARNING)
    
    while True:
        try:
            # 获取用户输入
            text = input(">>> ").strip()
            
            if not text:
                continue
                
            if text.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break
            
            # 合成语音
            print(f"🔄 正在合成: {text}")
            audio_data = await tts_synthesize(text)
            
            if audio_data:
                print(f"▶️  播放中 ({len(audio_data)} 字节)...")
                play_audio(audio_data)
                print(f"✅ 完成\n")
            else:
                print("❌ 合成失败\n")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序退出")
            break
        except EOFError:
            print("\n👋 输入结束")
            break
        except Exception as e:
            print(f"❌ 错误: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
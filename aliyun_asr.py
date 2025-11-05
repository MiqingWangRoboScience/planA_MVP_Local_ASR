import pyaudio
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
import dashscope
# dashscope.api_key = "your-api-key-here"  # 如未设环境变量

mic = None
stream = None

class Callback(RecognitionCallback):
    def on_open(self) -> None:
        global mic, stream
        print("中文识别已启动，请说话...")
        mic = pyaudio.PyAudio()
        stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True)

    def on_close(self) -> None:
        global mic, stream
        print("识别结束。")
        stream.stop_stream()
        stream.close()
        mic.terminate()

    def on_event(self, result: RecognitionResult) -> None:
        sentence = result.get_sentence()
        # 根据知识库示例，这里直接打印 sentence
        print("识别结果: ", sentence)

# 使用 Paraformer V2 专注中文
recognition = Recognition(
    model="paraformer-realtime-v2",
    format="pcm",
    sample_rate=16000,
    language_hints=["zh"],          # 仅识别中文
    disfluency_removal_enabled=True,  # 去掉“嗯”、“啊”等语气词
    callback=Callback()
)

recognition.start()
try:
    while stream:
        data = stream.read(3200, exception_on_overflow=False)
        recognition.send_audio_frame(data)
except KeyboardInterrupt:
    pass
finally:
    recognition.stop()
import asyncio
from piper import PiperVoice
import wave
import os
async def say_thing(text):
    model_path = "src/ai/en_GB-alan-low.onnx"
    config_path = "src/ai/en_GB-alan-low.onnx.json"
    output_path = os.path.join(os.getcwd(), "tts.wav")
    voice = PiperVoice.load(model_path=model_path, config_path=config_path)
    with wave.open("tts.wav", "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    print(f"[TTS] Saved synthesized speech to: {output_path}")

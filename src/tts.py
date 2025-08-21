import asyncio
from piper import PiperVoice
import wave
import os
async def say_thing(text):
    # Define paths to your model and config
    model_path = "src/ai/en_GB-alan-low.onnx"
    config_path = "src/ai/en_GB-alan-low.onnx.json"

    # Output WAV file path
    output_path = os.path.join(os.getcwd(), "tts.wav")

    # Initialize the Piper voice
    voice = PiperVoice.load(model_path=model_path, config_path=config_path)


    # Save to WAV file
    with wave.open("tts.wav", "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)


    print(f"Saved synthesized speech to: {output_path}")

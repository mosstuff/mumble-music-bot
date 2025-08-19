import numpy as np
import soundfile as sf
import time
from mumble import Mumble
from mumble.callbacks import CALLBACK
import jellyfin
import tts
import ffmpeg_wrap
import asyncio

SERVER = "157.180.10.100"
PORT = 3001
USERNAME = "Stählampe"
PASSWORD = ""
CERTFILE = "testbot.pem"

mumble = Mumble(SERVER, USERNAME, password=PASSWORD, port=PORT, certfile=CERTFILE, reconnect=True)
mumble.start()
mumble.is_ready()

def process_text(data):
    if data.message.startswith("!"):
        command = data.message[1:].split()[0]
        
        match command:
            case "play":
                message = f"Lade..."
                mumble.channels[0].send_text_message(message)

                query = data.message[6:]
                result = asyncio.run(play_query(query))
                if result != "":
                    message = f"{result}"
                    mumble.channels[0].send_text_message(message)
            case "help":
                message = f"<h1>Stehlampe -- Help</h1><br><li><ul>!play <i>query</i> -- Plays Song.</ul><ul>!help -- Shows this message.</ul></li>"
                mumble.channels[0].send_text_message(message)

mumble.callbacks.set_callback(CALLBACK.TEXT_MESSAGE_RECEIVED, process_text)

async def play_file(file):
    print("Now playing:" + file)
    data, samplerate = sf.read(file, dtype="int16")

    if data.ndim > 1:
        data = np.mean(data, axis=1).astype(np.int16)


    if samplerate != 48000:
        import librosa
        data = librosa.resample(data.astype(np.float32), orig_sr=samplerate, target_sr=48000)
        data = data.astype(np.int16)

    pcm_bytes = data.tobytes()

    frame_size = 960*500 
    bytes_per_sample = 2  
    chunk_size = frame_size * bytes_per_sample

    for i in range(0, len(pcm_bytes), chunk_size):
        chunk = pcm_bytes[i:i+chunk_size]
        mumble.send_audio.add_sound(chunk)
        await asyncio.sleep(10)

    print("Finished playing audio")

async def play_query(query):
    container, name_artist, url = jellyfin.query(query)
    if url.startswith("https://"):
        tts.say_thing("Now playing: " + name_artist + "!")
        ffmpeg_wrap.make_intermission()
        await asyncio.gather(
                play_file("c_intermission.wav"),
                jellyfin.download_music_and_convert(url, container)
            )
        await play_file("c_convert.wav")
        return ""
    else:
        return("Error! Song not found!")

if __name__ == "__main__":
    print("Startup complete.")
    while True:
        pass
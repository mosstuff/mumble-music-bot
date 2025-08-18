import numpy as np
import soundfile as sf
import time
from mumble import Mumble
import jellyfin

SERVER = "157.180.10.100"
PORT = 3001
USERNAME = "Stählampe"
PASSWORD = ""
CERTFILE = "testbot.pem"

mumble = Mumble(SERVER, USERNAME, password=PASSWORD, port=PORT, certfile=CERTFILE, reconnect=True)
mumble.start()
mumble.is_ready()
jellyfin.make_music("Glowing Lights")
data, samplerate = sf.read("current.wav", dtype="int16")

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
    if len(chunk) < chunk_size:
        break
    mumble.send_audio.add_sound(chunk)
    time.sleep(10)  

print("Finished playing audio")

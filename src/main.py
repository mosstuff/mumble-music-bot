import numpy as np
import soundfile as sf
import time
from mumble import Mumble
from mumble.callbacks import CALLBACK
import jellyfin
import tts
import ffmpeg_wrap
import asyncio
import re

SERVER = "157.180.10.100"
PORT = 3001
USERNAME = "Stählampe"
PASSWORD = ""
CERTFILE = "testbot.pem"

queue = []
is_processing_queue = False
is_playing = False
stop_event = asyncio.Event()

mumble = Mumble(SERVER, USERNAME, password=PASSWORD, port=PORT, certfile=CERTFILE, reconnect=True)

loop = None

currentusers = {}

async def greet_user(username):
    stop_event.clear()
    await play_file(username + ".wav")
    mumble.channels[0].send_text_message(f"Hiya, {username}")

async def chat_threadsfe(msg):
    mumble.channels[0].send_text_message(msg)

def process_text(data):
    global loop
    if not loop:
        return

    if data.message.startswith("!"):
        command = data.message[1:].split()[0]
        command_parts = data.message[1:].split()
        match command:
            case "play":
                mumble.channels[0].send_text_message("Playing.")
                query = data.message[6:]
                asyncio.run_coroutine_threadsafe(play_immedeatly(query), loop)

            case "add":
                mumble.channels[0].send_text_message("Processing...")
                query = data.message[5:]
                asyncio.run_coroutine_threadsafe(add_queue(query), loop)

            case "plist":
                mumble.channels[0].send_text_message("Processing...")
                query = data.message[7:]
                asyncio.run_coroutine_threadsafe(play_pl_immedeatly(query), loop)

            case "url":
                mumble.channels[0].send_text_message("Added.")
                url = data.message[5:]
                asyncio.run_coroutine_threadsafe(play_url_immedeatly(url), loop)

            case "stop":
                asyncio.run_coroutine_threadsafe(stop_queue(), loop)
                mumble.channels[0].send_text_message("Stopped.")
            case "loop":
                global looping
                try:
                    arg = command_parts[1].lower()
                    if arg == "true":
                        looping = True
                        mumble.channels[0].send_text_message("Looping enabled.")
                    elif arg == "false":
                        looping = False
                        mumble.channels[0].send_text_message("Looping disabled.")
                    else:
                        mumble.channels[0].send_text_message("Usage: !loop <true|false>")
                except IndexError:
                    # If no argument is provided, report the current state
                    status = "enabled" if looping else "disabled"
                    mumble.channels[0].send_text_message(f"Looping is currently {status}.")

            case "skip":
                mumble.channels[0].send_text_message("Skipped.")
                asyncio.run_coroutine_threadsafe(skip_queue(), loop)

            case "list":
                songs = []
                for item in queue:
                    if item.get("type") == "query":
                        songs.append(item.get("data").get("name_artist"))
                    elif item.get("type") == "url":
                        songs.append(item.get("data"))
                message = "<h2>Songs in current queue:</h2><br><ul><li>" + '</li><li>'.join(item for item in songs) + '</li></ul>'
                song_items = message.split('</li><li>')
                chunks = []
                chunk_size = 5000
                current_chunk = "<ul><li>"

                for song in song_items:
                    if len(current_chunk) + len(song) + len('</li><li>') > chunk_size:
                        current_chunk += "</li></ul>"
                        chunks.append(current_chunk)
                        current_chunk = "<ul><li>" + song
                    else:
                        current_chunk += "</li><li>" + song

                if current_chunk:
                    current_chunk += "</li></ul>"
                    chunks.append(current_chunk)
                for chunk in chunks:
                    mumble.channels[0].send_text_message(chunk)
                #asyncio.run_coroutine_threadsafe(chat_threadsfe(str(queue)), loop)

            case "songs":
                mumble.channels[0].send_text_message("<a href=\"https://crapflix.mosstuff.de/https://crapflix.mosstuff.de/web/#/music.html\">https://crapflix.mosstuff.de/https://crapflix.mosstuff.de/web/#/music.html</a>")
            
            case "help":
                message = f"<h1>Stehlampe -- Help</h1><br><ul><li>!play <i>query</i> -- Plays a song immediately.</li><li>!add <i>query</i> -- Adds a song to the queue.</li><li>!stop -- Stops playback and clears the queue.</li><li>!help -- Shows this message.</li></ul>"
                mumble.channels[0].send_text_message(message)

def process_join(data):
    global loop
    if not loop:
        return

    username = data.get('name')
    session = data.get('session')
    
    if username and session:
        currentusers[session] = username
        asyncio.run_coroutine_threadsafe(stop_queue(), loop)
        asyncio.run_coroutine_threadsafe(greet_user(username), loop)

def process_leave(user, data):
    try:
        session = user.get('session')
        if session and session in currentusers:
            currentusers.pop(session)
    except Exception as e:
        print(f"[Main] Error in process_leave: {e}")

async def play_file(file):
    global is_playing
    is_playing = True
    print(f"[Player] Now playing: {file}")
    
    try:
        data, samplerate = sf.read(file, dtype="int16")
    except Exception as e:
        print(f"[Player] Error reading audio file {file}: {e}")
        is_playing = False
        return

    if data.ndim > 1:
        data = np.mean(data, axis=1).astype(np.int16)

    if samplerate != 48000:
        try:
            import librosa
            data = librosa.resample(data.astype(np.float32), orig_sr=samplerate, target_sr=48000)
            data = data.astype(np.int16)
        except ImportError:
            print("[Player] librosa not installed. Could not resample audio.")
            is_playing = False
            return

    pcm_bytes = data.tobytes()
    seconds_per_iteration = 1
    chunk_size = 48000 * seconds_per_iteration * 2

    for i in range(0, len(pcm_bytes), chunk_size):
        if stop_event.is_set():
            print("[Player] Playback stopped early.")
            break
        
        chunk = pcm_bytes[i:i+chunk_size]
        mumble.send_audio.add_sound(chunk)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=seconds_per_iteration)
            print("[Player] Playback stopped early during sleep.")
            break
        except asyncio.TimeoutError:
            pass
            
    is_playing = False
    print("[Player] Finished playing audio.")

async def play_id(song):
    print(song)
    stop_event.clear()
    sid = song.get("sid")
    name_artist = song.get("name_artist")
    print(f"[IDplay] Processing ID: {sid}")

    if sid != "" or sid != None:
        await tts.say_thing(f"Now playing: {name_artist}!")
        await ffmpeg_wrap.make_intermission()
        
        download_task = asyncio.create_task(jellyfin.download_id_and_convert(sid))
        
        await play_file("c_intermission.wav")
        
        await download_task

        if not stop_event.is_set():
            await play_file("c_convert.wav")
        return ""
    else:
        return "Error!"

async def play_url(url):
    print(f"[URLplay] Processing url: {url}")
    url = re.sub(r'<[^>]+>', '', url)
    stop_event.clear()

    if url.startswith("https://"):
        await tts.say_thing(f"Now playing a custom URL!")
        await ffmpeg_wrap.make_intermission()
        
        download_task = asyncio.create_task(jellyfin.download_music_and_convert(url, "mp3"))
        
        await play_file("c_intermission.wav")
        
        await download_task

        if not stop_event.is_set():
            await play_file("c_convert.wav")
        return ""
    else:
        return "Error! Song not found!"

async def add_queue(query):
    global queue, is_processing_queue

    query = re.sub(r'<[^>]+>', '', query)

    if query.startswith("https://"):
        queue.append({"type":"url","data":query})
        mumble.channels[0].send_text_message("Added " + query + " to queue!")
        if not is_processing_queue:
            asyncio.create_task(process_queue())
    else:
        sid, name_artist = jellyfin.query(query)
        if sid != "":
            queue.append({"type":"query","data":{"sid":sid,"name_artist":name_artist}})
            mumble.channels[0].send_text_message("Added " + name_artist + " to queue!")
            if not is_processing_queue:
                asyncio.create_task(process_queue())
        else:
            mumble.channels[0].send_text_message("Song not Found!")

async def play_immedeatly(query):
    global queue
    await stop_queue_no_clear()
    sid, name_artist = jellyfin.query(query)
    if sid != "":
        queue.insert(0, {"type":"query","data":{"sid":sid,"name_artist":name_artist}})
    else:
        mumble.channels[0].send_text_message("Song not Found!")
    asyncio.create_task(process_queue())

async def play_url_immedeatly(url):
    global queue
    await stop_queue_no_clear()
    queue.insert(0, {"type":"url","data":url})
    asyncio.create_task(process_queue())

async def play_pl_immedeatly(query):
    global queue
    await stop_queue()
    ids = await jellyfin.get_playlist_ids(query)
    if len(ids.get("ids", [])) > 0:
        print(ids.get("ids", []))
        for id in ids.get("ids", []):
            queue.append({"type":"query","data":id})
            mumble.channels[0].send_text_message("Added: " + id.get("name_artist"))
    else:
        mumble.channels[0].send_text_message("Error: Playlist empty!")
    mumble.channels[0].send_text_message(ids.get("status"))
    asyncio.create_task(process_queue())

async def process_queue():
    global queue, is_processing_queue, looping
    if is_processing_queue:
        return
    
    is_processing_queue = True
    while queue and is_processing_queue:
        current_query = queue.pop(0)
        if looping:
            queue.append(current_query)
        
        if current_query.get("type") == "query":
            result = await play_id(current_query.get("data"))
            if result:
                mumble.channels[0].send_text_message(result)
        elif current_query.get("type") == "url":
            result = await play_url(current_query.get("data"))
            if result:
                mumble.channels[0].send_text_message(result)
                if looping:
                     queue.pop()

    is_processing_queue = False
    print("[Queue] Queue finished.")

async def stop_queue():
    global queue, is_processing_queue, is_playing, looping
    queue.clear()
    is_processing_queue = False
    looping = False
    stop_event.set()

async def stop_queue_no_clear():
    global is_processing_queue
    is_processing_queue = False
    stop_event.set()
    
async def skip_queue():
    global queue, is_processing_queue
    is_processing_queue = False
    stop_event.set()
    stop_event.clear()
    asyncio.create_task(process_queue())

async def main():
    global loop
    loop = asyncio.get_running_loop()
    
    mumble.callbacks.set_callback(CALLBACK.USER_CREATED, process_join)
    mumble.callbacks.set_callback(CALLBACK.TEXT_MESSAGE_RECEIVED, process_text)
    mumble.callbacks.set_callback(CALLBACK.USER_REMOVED, process_leave)
    mumble.start()
    
    while not mumble.is_ready():
        await asyncio.sleep(0.1)
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        print("Mumble Bot is running...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Main] Shutting down.")

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

# --- Configuration ---
SERVER = "157.180.10.100"
PORT = 3001
USERNAME = "Stählampe"
PASSWORD = ""
CERTFILE = "testbot.pem"

# --- Global State ---
queue = []
is_processing_queue = False
is_playing = False
stop_event = asyncio.Event()

# --- Mumble Setup ---
mumble = Mumble(SERVER, USERNAME, password=PASSWORD, port=PORT, certfile=CERTFILE, reconnect=True)

# This will hold the main event loop
loop = None

currentusers = {}

# --- Async Helper for Thread-Safe Greeting ---
async def greet_user(username):
    """Asynchronously sends a welcome message."""
    # This coroutine will be run safely on the main event loop
    stop_event.clear()
    await play_file(username + ".wav")
    mumble.channels[0].send_text_message(f"Hiya, {username}")

async def chat_threadsfe(msg):
    mumble.channels[0].send_text_message(msg)

# --- Synchronous Callbacks (from pymumble's thread) ---

def process_text(data):
    """
    Handles command messages from Mumble.
    Runs in pymumble's background thread.
    """
    global loop
    if not loop:
        return # Don't process commands if the main loop isn't running yet

    if data.message.startswith("!"):
        command = data.message[1:].split()[0]
        
        match command:
            case "play":
                mumble.channels[0].send_text_message("Playing.")
                query = data.message[6:]
                asyncio.run_coroutine_threadsafe(play_immedeatly(query), loop)

            case "add":
                mumble.channels[0].send_text_message("Added.")
                query = data.message[5:]
                asyncio.run_coroutine_threadsafe(add_queue(query), loop)

            case "url":
                mumble.channels[0].send_text_message("Added.")
                url = data.message[5:]
                asyncio.run_coroutine_threadsafe(play_url_immedeatly(url), loop)

            case "stop":
                asyncio.run_coroutine_threadsafe(stop_queue(), loop)
                mumble.channels[0].send_text_message("Stopped.")

            case "skip":
                mumble.channels[0].send_text_message("Skipped.")
                asyncio.run_coroutine_threadsafe(skip_queue(), loop)

            case "list":
                mumble.channels[0].send_text_message("Songs in current queue: " + ', '.join(queue))
                #asyncio.run_coroutine_threadsafe(chat_threadsfe(str(queue)), loop)

            case "songs":
                mumble.channels[0].send_text_message("<a href=\"https://crapflix.mosstuff.de/https://crapflix.mosstuff.de/web/#/music.html\">https://crapflix.mosstuff.de/https://crapflix.mosstuff.de/web/#/music.html</a>")
            
            case "help":
                message = f"<h1>Stehlampe -- Help</h1><br><ul><li>!play <i>query</i> -- Plays a song immediately.</li><li>!add <i>query</i> -- Adds a song to the queue.</li><li>!stop -- Stops playback and clears the queue.</li><li>!help -- Shows this message.</li></ul>"
                mumble.channels[0].send_text_message(message)

def process_join(data):
    """
    Handles user join events.
    Runs in pymumble's background thread.
    """
    global loop
    if not loop:
        return # Don't process commands if the main loop isn't running yet

    username = data.get('name')
    session = data.get('session')
    
    if username and session:
        currentusers[session] = username
        # **CRITICAL FIX**: Schedule the message on the main loop
        # Do NOT call mumble.send_text_message() directly here.
        asyncio.run_coroutine_threadsafe(stop_queue(), loop)
        asyncio.run_coroutine_threadsafe(greet_user(username), loop)

def process_leave(user, data):
    """
    Handles user leave events.
    Runs in pymumble's background thread.
    """
    # This function is fine because it only modifies a dictionary, 
    # which is a thread-safe operation in this context (thanks to Python's GIL).
    # It does not interact with the mumble object or network.
    try:
        session = user.get('session')
        if session and session in currentusers:
            currentusers.pop(session)
    except Exception as e:
        print(f"Error in process_leave: {e}")

# --- Asynchronous Playback Logic (Unchanged) ---

async def play_file(file):
    global is_playing
    is_playing = True
    print(f"Now playing: {file}")
    
    try:
        data, samplerate = sf.read(file, dtype="int16")
    except Exception as e:
        print(f"Error reading audio file {file}: {e}")
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
            print("librosa not installed. Could not resample audio.")
            is_playing = False
            return

    pcm_bytes = data.tobytes()
    seconds_per_iteration = 1
    chunk_size = 48000 * seconds_per_iteration * 2

    for i in range(0, len(pcm_bytes), chunk_size):
        if stop_event.is_set():
            print("Playback stopped early.")
            break
        
        chunk = pcm_bytes[i:i+chunk_size]
        mumble.send_audio.add_sound(chunk)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=seconds_per_iteration)
            print("Playback stopped early during sleep.")
            break
        except asyncio.TimeoutError:
            pass
            
    is_playing = False
    print("Finished playing audio.")

async def play_query(query):
    print(f"Processing query: {query}")
    stop_event.clear()

    container, name_artist, url = jellyfin.query(query)

    if url.startswith("https://"):
        await tts.say_thing(f"Now playing: {name_artist}!")
        await ffmpeg_wrap.make_intermission()
        
        download_task = asyncio.create_task(jellyfin.download_music_and_convert(url, container))
        
        await play_file("c_intermission.wav")
        
        await download_task

        if not stop_event.is_set():
            await play_file("c_convert.wav")
        return ""
    else:
        return "Error! Song not found!"

async def play_url(url):
    print(f"Processing url: {url}")
    url = re.sub(r'<[^>]+>', '', url)
    stop_event.clear()

    if url.startswith("https://"):
        await tts.say_thing(f"Now playing: {url}!")
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
    queue.append(query)
    if not is_processing_queue:
        asyncio.create_task(process_queue())

async def play_immedeatly(query):
    global queue
    await stop_queue()
    queue.insert(0, query)
    asyncio.create_task(process_queue())

async def play_url_immedeatly(url):
    global queue
    await stop_queue()
    result = await play_url(url)
    if result:
            mumble.channels[0].send_text_message(result)


async def process_queue():
    global queue, is_processing_queue
    if is_processing_queue:
        return
    
    is_processing_queue = True
    while queue and is_processing_queue:
        current_query = queue.pop(0)
        result = await play_query(current_query)
        if result:
             mumble.channels[0].send_text_message(result)

    is_processing_queue = False
    print("Queue finished.")

async def stop_queue():
    global queue, is_processing_queue, is_playing
    queue.clear()
    is_processing_queue = False
    stop_event.set()
    
async def skip_queue():
    global queue, is_processing_queue
    is_processing_queue = False
    stop_event.set()
    stop_event.clear()
    asyncio.create_task(process_queue())
# --- Main Application Entry Point ---

async def main():
    global loop
    loop = asyncio.get_running_loop()
    
    mumble.callbacks.set_callback(CALLBACK.USER_CREATED, process_join)
    mumble.callbacks.set_callback(CALLBACK.TEXT_MESSAGE_RECEIVED, process_text)
    mumble.callbacks.set_callback(CALLBACK.USER_REMOVED, process_leave)
    mumble.start()
    
    while not mumble.is_ready():
        await asyncio.sleep(0.1)
        
    print("Startup complete. Bot is ready.")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down.")
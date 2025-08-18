#pip install git+https://github.com/DuckBoss/pymumble@main
from mumble import Mumble
from mumble.callbacks import CALLBACK
import json
import os

datafile = "persist.json"

def save_array(arr, filename=datafile):
    with open(filename, "w") as f:
        json.dump(arr, f)

def load_array(filename=datafile):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []  # Return empty list if file doesn't exist

# Configuration
SERVER = "157.180.10.100"
PORT = 3001  # Default Mumble port
USERNAME = "Stählampe"
PASSWORD = ""  # Leave empty if no password
CERTFILE = 'testbot.pem'  # Path to your certificate file
currentusers = {}
accepted = load_array()

# Connect to the Mumble server
mumble = Mumble(SERVER, USERNAME, password=PASSWORD, port=PORT, certfile=CERTFILE, reconnect=True)
mumble.start()
mumble.is_ready()

def process_join(data):
    """Greet users when they join."""
    username = data.get('name')
    session = data.get('session')
    currentusers[session] = username
    if not username in accepted:
        user = mumble.users.get(session)
        user.deafen()
        message = f"<h2 style=\"color: red; font-weight: bold;\">Nutze <b>!accept</b> um die <a href=\"https://static.mosstuff.de/mtos/de/#/mmoverview\">ToS und Dateschutzrichtlinie</a> zu akzeptieren! (Letztes Update: 17.8.2025 22:34)<a href=\"https://static.mosstuff.de/mtos/de/#/mmoverview\">[EN]</a></h2>"
        user.send_text_message(message)

def process_leave(data, data2):
    try:
        session = data2.get('session')
        currentusers.pop(session)
    except:
        pass

def process_text(data):
    if data.message == "!accept" and not currentusers[data.actor] in accepted:
        user = mumble.users.get(data.actor)
        user.unmute()
        user.register()
        message = f"Vielen Dank! Geniesse deinen Aufenthalt!"
        user.send_text_message(message)
        accepted.append(currentusers[data.actor])
        save_array(accepted)

# Register the callback to detect new users
mumble.callbacks.set_callback(CALLBACK.USER_CREATED, process_join)
mumble.callbacks.set_callback(CALLBACK.TEXT_MESSAGE_RECEIVED, process_text)
mumble.callbacks.set_callback(CALLBACK.USER_REMOVED, process_leave)
bot = mumble.users.get(mumble.users.myself_session)
bot.deafen()

print("Mumble GreetBot is running...")

# Keep the bot running
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Shutting down bot...")
    mumble.stop()

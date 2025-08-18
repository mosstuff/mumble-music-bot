from jellyfin_apiclient_python import JellyfinClient
import ffmpeg
import requests

def make_music(Name):
    client = JellyfinClient()
    client.config.app('music-bot', '0.0.1', 'scary_big_nasa_compuper', 'ghdfjklhhdfghklfghnijophrsthijkophtrsopihjdfgh')
    client.config.data["auth.ssl"] = True
    client.auth.connect_to_address('https://crapflix.mosstuff.de/https://crapflix.mosstuff.de')
    client.auth.login('https://crapflix.mosstuff.de/https://crapflix.mosstuff.de', 'music-bot', 'musik')
    result = client.jellyfin.search_media_items(term=Name, media="Music")
    id = result["Items"][0]["Id"]
    container = result["Items"][0]["Container"]
    url = client.jellyfin.audio_url(id,container)
    response = requests.get(url)
    if response.status_code == 200:
        with open("current." + container, 'wb') as f:
            f.write(response.content)
    else:
        print("Failed:", response.status_code)

    ffmpeg.input("current.mp3").output(
        "current.wav",
        acodec='pcm_s16le',
        ar='48000',
        ac=2,
    ).run(overwrite_output=True)

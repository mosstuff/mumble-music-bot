from jellyfin_apiclient_python import JellyfinClient
import ffmpeg
import requests
import asyncio
import ffmpeg_wrap

def query(Name):
    print("Quering: " + Name)
    client = JellyfinClient()
    client.config.app('music-bot', '0.0.1', 'scary_big_nasa_compuper', 'ghdfjklhhdfghklfghnijophrsthijkophtrsopihjdfgh')
    client.config.data["auth.ssl"] = True
    client.auth.connect_to_address('https://crapflix.mosstuff.de/https://crapflix.mosstuff.de')
    client.auth.login('https://crapflix.mosstuff.de/https://crapflix.mosstuff.de', 'music-bot', 'musik')
    result = client.jellyfin.search_media_items(term=Name, media="Music")
    if len(result["Items"]) >= 1:
        id = result["Items"][0]["Id"]
        container = result["Items"][0]["Container"]
        name_artist = result["Items"][0]["Name"] + " by " + ' ,'.join(result["Items"][0]["Artists"])
        url = client.jellyfin.audio_url(id,container)
        print("Found: " + name_artist + ".")
        return container, name_artist, url
    else:
        return("","","")


async def download(url, container):
    response = requests.get(url)
    if response.status_code == 200:
        with open("jellyfin." + container, 'wb') as f:
            f.write(response.content)
            return("jellyfin." + container)
    else:
        print("Failed:", response.status_code)
        return("")

async def download_music_and_convert(url, container):
    print("Downloading: " + url)
    file = await download(url, container)
    print("Downloaded. Started conversion to WAV.")
    await ffmpeg_wrap.convert_proper(file)
    print("Finished converting. Music ready.")

from jellyfinapi.jellyfinapi_client import JellyfinapiClient
from jellyfinapi.configuration import Environment
from jellyfinapi.models.base_item_kind_enum import BaseItemKindEnum
import ffmpeg
import aiohttp
import asyncio
import ffmpeg_wrap

api_key = ''

client = JellyfinapiClient(
    x_emby_token=api_key,
    server_url="https://crapflix.mosstuff.de"
    )

def query(query):
     print("[Jellyfin] Quering: " + query)
     search_controller = client.search
     result =search_controller.get(search_term=query,include_item_types=BaseItemKindEnum.AUDIO)
     if len(result.search_hints) > 0:
        name_artist = result.search_hints[0].name + " by " + ' ,'.join(result.search_hints[0].artists)
        return result.search_hints[0].item_id, name_artist
        #return "bin",name_artist,"https://crapflix.mosstuff.de/Items/" + result.search_hints[0].item_id + "/Download?api_key=" + api_key
     else:
        return "",""

async def get_playlist_ids(playlist_name):
    print("[Jellyfin] Querying playlist:", playlist_name)
    search_controller = client.search
    result = search_controller.get(search_term=playlist_name,include_item_types=BaseItemKindEnum.PLAYLIST)
    if len(result.search_hints) > 0:
        pl_id = result.search_hints[0].item_id
        playlists_controller = client.playlists
        try:
            result = playlists_controller.get_playlist_items(pl_id, "d9a1b273dc5443d4a166579b33be99b2")
        except:
            result = ""
        ids = []
        if result != "":
            for item in result.items:
                ids.append({"sid":item.id,"name_artist":item.name + " by " + ' ,'.join(item.artists)})
            print(ids)
            return {"status": "Success!","ids": ids} #success
        else:
            return {"status": "Error: Playlist is private!","ids": []} #Playlist Private
    else:
        return {"status": "Error: Playlist not found!","ids": []} #Not Found
    

async def download(url, container):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                with open("jellyfin." + container, 'wb') as f:
                    f.write(content)
                    return "jellyfin." + container
            else:
                print("[Downloader] Failed:", response.status)
                return ""


async def download_music_and_convert(url, container):
    print("[DnC] Downloading: " + url)
    file = await download(url, container)
    print("[DnC] Downloaded. Started conversion to WAV.")
    await ffmpeg_wrap.convert_proper(file)
    print("[DnC] Finished converting. Music ready.")

async def download_id_and_convert(id):
    print("[IDnC] Prepping URL for: " + id)
    await download_music_and_convert("https://crapflix.mosstuff.de/Items/" + id + "/Download?api_key=" + api_key, "bin")

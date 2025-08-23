import ffmpeg
import asyncio
async def convert_proper(file):
    print("[ffmpeg] Converting " + file + " to c_convert.wav ...")
    def run_ffmpeg():
        ffmpeg.input(file).output(
            "c_convert.wav",
            acodec='pcm_s16le',
            ar='48000',
            ac=2,
            af = 'loudnorm',
            loglevel="quiet"
        ).run(overwrite_output=True)
    await asyncio.to_thread(run_ffmpeg)

async def make_intermission():
    print("[ffmpeg] Merging intermission...")
    ffmpeg.concat(
        ffmpeg.input("intermission3.wav"),
        ffmpeg.input("tts.wav"),
        v=0,
        a=1
    ).output(
        "c_intermission.wav",
        acodec='pcm_s16le',
        ar=48000,
        ac=2,
        loglevel="quiet"
    ).run(overwrite_output=True)
    print("[ffmpeg] Finished Merging.")
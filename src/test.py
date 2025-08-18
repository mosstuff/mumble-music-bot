# /// script
# dependencies = [
#     "pymumble>=2",
# ]
# ///
from mumble import Mumble

with Mumble("157.180.10.100", "Stählampe") as m:
  usernames = [
      user["name"]
      for user in m.my_channel().get_users()
      if user["session"] != m.users.myself_session
  ]
  m.my_channel().send_text_message(
      "Hello, " + ", ".join(usernames) + ". You're all Brian! You're all individuals!"
  )

  # If you have `espeak` installed:
  import subprocess

  wav = subprocess.Popen(
      ["espeak", "--stdout", "'People called Romanes, they go the house?'"],
      stdout=subprocess.PIPE,
  ).stdout
  sound = subprocess.Popen(
      ["ffmpeg", "-i", "-", "-ac", "1", "-f", "s32le", "-"],
      stdout=subprocess.PIPE,
      stdin=wav,
  ).stdout.read()
  m.send_audio.add_sound(sound)
  m.send_audio.queue_empty.wait()
import pyttsx3
engine = pyttsx3.init()
def say_thing(text):
    print("Generationg TTS for: '" + text + "'")
    engine.save_to_file(text, 'tts.mp3')
    engine.runAndWait()
# app/voice/tts.py
import tempfile
import pygame

def speak_text(client, text: str):
    audio = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    )

    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_audio.write(audio.read())
    temp_audio.close()

    pygame.mixer.init()
    pygame.mixer.music.load(temp_audio.name)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)




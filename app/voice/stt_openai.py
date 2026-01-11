# app/voice/stt_openai.py
def speech_to_text(client, audio_path: str) -> str:
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",   # correct model name
            file=audio_file
        )
    return transcription.text

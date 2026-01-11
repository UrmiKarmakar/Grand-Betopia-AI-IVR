# app/voice/voice_loop.py
from .stt import record_audio
from .stt_openai import speech_to_text
from .tts import speak_text

def voice_chat_loop(client, ask_rag_fn):
    while True:
        audio_path = record_audio()
        user_text = speech_to_text(client, audio_path)

        if not user_text.strip():
            continue

        print(f"\n🎤 You: {user_text}")

        if user_text.lower() in ["exit", "quit", "stop"]:
            speak_text(client, "Goodbye!")
            break

        answer = ask_rag_fn(user_text)

        print(f"\n🤖 Bot: {answer}")
        speak_text(client, answer)

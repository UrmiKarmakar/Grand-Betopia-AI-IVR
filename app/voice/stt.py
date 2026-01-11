# app/voice/stt.py
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile

def record_audio(duration=6, samplerate=16000):
    print(" Listening...")
    audio = sd.rec(
        int(duration * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype="int16"
    )
    sd.wait()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    wav.write(temp_file.name, samplerate, audio)

    return temp_file.name

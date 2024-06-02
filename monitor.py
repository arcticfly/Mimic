import pyaudio
import numpy as np
import wave
import time

# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
THRESHOLD = 1000  # Scale to an appropriate value for 16-bit audio
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "file.wav"
BUFFER_SECONDS = 0.5  # How many seconds to keep in buffer before the trigger

# Initialize PyAudio
p = pyaudio.PyAudio()

# Open stream
stream = p.open(
    format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK
)


def is_loud(data, threshold):
    """Check if the data contains sounds louder than the threshold."""
    print(np.max(np.frombuffer(data, dtype=np.int16)))
    amplitude = np.max(np.frombuffer(data, dtype=np.int16))
    return amplitude > threshold


def record_sound(buffer, duration=RECORD_SECONDS):
    print("Recording...")
    frames = list(buffer)  # Start with buffered audio
    for i in range(0, int(RATE / CHUNK * duration) - len(buffer)):
        data = stream.read(CHUNK)
        frames.append(data)
    print("Recording ended.")
    return frames


def save_playback(frames):
    print("Saving the recording...")
    wf = wave.open(WAVE_OUTPUT_FILENAME, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()
    print("Playback...")
    play_sound()
    print("Monitoring...")


def play_sound():
    wf = wave.open(WAVE_OUTPUT_FILENAME, "rb")
    play_stream = p.open(
        format=p.get_format_from_width(wf.getsampwidth()),
        channels=wf.getnchannels(),
        rate=wf.getframerate(),
        output=True,
    )
    data = wf.readframes(CHUNK)
    while data:
        play_stream.write(data)
        data = wf.readframes(CHUNK)
    play_stream.stop_stream()
    play_stream.close()
    wf.close()


buffer_frames = []
max_buffer_frames = int(RATE / CHUNK * BUFFER_SECONDS)

try:
    while True:
        input_data = stream.read(CHUNK, exception_on_overflow=False)
        buffer_frames.append(input_data)
        if len(buffer_frames) > max_buffer_frames:
            buffer_frames.pop(0)  # Remove oldest frame to maintain buffer size

        if is_loud(input_data, THRESHOLD):
            frames = record_sound(buffer_frames)
            save_playback(frames)
            buffer_frames = []  # Clear buffer after recording
        # time.sleep(0.1)  # Small delay to prevent high CPU usage
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Stopped monitoring.")

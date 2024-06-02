import pyaudio
import numpy as np
import wave
import asyncio

# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
THRESHOLD = 1000  # Scale to an appropriate value for 16-bit audio
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "file.wav"
BUFFER_SECONDS = 0.5  # How many seconds to keep in buffer before the trigger


class AudioMonitor:
    def __init__(self):
        self.monitoring = False
        self.buffer_frames = []
        self.max_buffer_frames = int(RATE / CHUNK * BUFFER_SECONDS)

    def is_loud(self, data, threshold):
        """Check if the data contains sounds louder than the threshold."""
        print(np.max(np.frombuffer(data, dtype=np.int16)))
        amplitude = np.max(np.frombuffer(data, dtype=np.int16))
        return amplitude > threshold

    def record_sound(self, buffer, duration=RECORD_SECONDS):
        print("Recording...")
        frames = list(buffer)  # Start with buffered audio
        for i in range(0, int(RATE / CHUNK * duration) - len(buffer)):
            data = stream.read(CHUNK)
            frames.append(data)
        return frames

    def save_playback(self, frames):
        wf = wave.open(WAVE_OUTPUT_FILENAME, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        wf.close()
        self.play_sound()

    def play_sound(self):
        print("Playing back...")
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

    async def monitor(self):
        i = 0
        try:
            global p, stream
            # Initialize PyAudio
            p = pyaudio.PyAudio()

            # Open stream
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
            print("Started monitoring...")
            while self.monitoring:
                input_data = stream.read(CHUNK, exception_on_overflow=False)
                self.buffer_frames.append(input_data)
                if len(self.buffer_frames) > self.max_buffer_frames:
                    self.buffer_frames.pop(
                        0
                    )  # Remove oldest frame to maintain buffer size

                if self.is_loud(input_data, THRESHOLD):
                    frames = self.record_sound(self.buffer_frames)
                    self.save_playback(frames)
                    self.buffer_frames = []  # Clear buffer after recording

                if i == 30:
                    i = 0
                    # Allow other tasks to run
                    await asyncio.sleep(0.001)
                i += 1
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("Stopped monitoring.")

    async def start_monitoring(self):
        self.monitoring = True
        await self.monitor()

    def stop_monitoring(self):
        self.monitoring = False
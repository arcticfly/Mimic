import pyaudio
import numpy as np
import wave
import asyncio
import scipy.signal
from typing import Callable
import time


# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
THRESHOLD = 30000  # Scale to an appropriate value for 16-bit audio
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "file.wav"
BUFFER_SECONDS = 0.5  # How many seconds to keep in buffer before the trigger
GAIN_FACTOR = 50  # Adjust this factor based on desired output volume


class AudioMonitor:
    def __init__(self):
        self.monitoring: bool = False
        self.buffer_frames: list[bytes] = []
        self.max_buffer_frames: int = int(RATE / CHUNK * BUFFER_SECONDS)
        # Filter setup
        self.nyquist: float = RATE / 2
        self.cutoff: float = 150  # Cutoff frequency for bass boost
        self.b, self.a = scipy.signal.butter(
            1, self.cutoff / self.nyquist, btype="lowpass"
        )
        self.send_message: Callable[[str], None] = None

    def get_amplitude(self, data: bytes) -> int:
        processed_frame = self.amplify_bass([data])
        print(np.max(np.frombuffer(processed_frame, dtype=np.int16)))
        return np.max(np.frombuffer(processed_frame, dtype=np.int16))

    def amplify_bass(self, frames: list[bytes]) -> bytes:
        """Apply bass boost filter with frequency weighting and gain adjustment to the audio frames."""
        # Concatenate byte frames into a single array
        raw_data = b"".join(frames)
        # Convert byte data to numpy array
        signal = np.frombuffer(raw_data, dtype=np.int16)
        # Using a higher-order filter for a steeper cutoff
        b, a = scipy.signal.butter(4, self.cutoff / self.nyquist, btype="low")
        # Apply the low-pass filter
        filtered_signal = scipy.signal.lfilter(b, a, signal)
        # Apply a gain factor to compensate for any attenuation
        filtered_signal = filtered_signal * GAIN_FACTOR
        # Ensure the signal does not exceed 16-bit limits after gain
        filtered_signal = np.clip(filtered_signal, -32768, 32767)
        # Convert filtered data back to bytes
        processed_data = filtered_signal.astype(np.int16).tobytes()
        return processed_data

    def record_sound(
        self, buffer: list[bytes], duration: float = RECORD_SECONDS
    ) -> bytes:
        print("Recording...")
        frames = list(buffer)  # Start with buffered audio
        for i in range(0, int(RATE / CHUNK * duration) - len(buffer)):
            data = stream.read(CHUNK)
            frames.append(data)
        processed_frames = self.amplify_bass(frames)
        print("done recording")
        return processed_frames

    def save_playback(self, frames: bytes):
        wf = wave.open(WAVE_OUTPUT_FILENAME, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(frames)
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

                amplitude = self.get_amplitude(input_data)

                if amplitude > THRESHOLD:
                    if self.send_message:
                        self.send_message(
                            f"Loud sound detected - amplitude: {amplitude}"
                        )
                        await asyncio.sleep(0.01)
                    frames = self.record_sound(self.buffer_frames)
                    self.save_playback(frames)
                    await asyncio.sleep(0.001)
                    self.buffer_frames = []  # Clear buffer after recording
                    stream.stop_stream()
                    stream.close()
                    stream = p.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK,
                    )
                    print("moving on")

                if i == 10:
                    i = 0
                    # Allow other tasks to run
                    await asyncio.sleep(0.001)
                i += 1
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("Stopped monitoring.")

    async def start_monitoring(self, send_message: Callable[[str], None] | None = None):
        self.monitoring = True
        self.send_message = send_message
        await self.monitor()

    def stop_monitoring(self):
        self.monitoring = False

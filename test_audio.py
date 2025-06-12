import pyaudio
import numpy as np
import time


def test_audio():
    # Audio parameters
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 44100
    threshold = 0.005  # Our detection threshold

    audio = pyaudio.PyAudio()

    print(f"Testing audio detection with threshold: {threshold}")
    print("Make some LOUD sounds (clap, speak loudly, etc.)")
    print("Background noise levels will be shown, triggers will be highlighted")
    print("-" * 60)

    try:
        stream = audio.open(
            format=format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=0,  # MacBook Pro Microphone
            frames_per_buffer=chunk,
        )

        for i in range(100):  # 10 seconds of testing
            try:
                data = stream.read(chunk, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)

                if len(audio_data) > 0:
                    mean_square = np.mean(audio_data**2)
                    if mean_square >= 0 and not np.isnan(mean_square):
                        rms = np.sqrt(mean_square)
                        normalized_level = rms / 32768.0

                        if normalized_level > threshold:
                            print(
                                f"🔥 TRIGGER! Audio level: {normalized_level:.6f} (above {threshold})"
                            )
                        elif normalized_level > 0.002:
                            print(
                                f"Audio level: {normalized_level:.6f} (below threshold)"
                            )

            except Exception as e:
                print(f"Error reading audio: {e}")

            time.sleep(0.1)

        stream.stop_stream()
        stream.close()

    except Exception as e:
        print(f"Failed to open audio device: {e}")

    audio.terminate()


if __name__ == "__main__":
    test_audio()

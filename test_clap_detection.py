import pyaudio
import numpy as np
import time


def test_clap_detection(device_index=0):
    # Audio parameters
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 44100

    audio = pyaudio.PyAudio()

    # Get device info
    device_info = audio.get_device_info_by_index(device_index)
    print(f"Testing Device {device_index}: {device_info['name']}")
    print("=" * 60)
    print("CLAP LOUDLY or make sharp sounds!")
    print("Watching for audio spikes...")
    print("Press Ctrl+C to stop")
    print("-" * 60)

    try:
        stream = audio.open(
            format=format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=chunk,
        )

        # Keep track of recent levels for comparison
        recent_levels = []
        max_recent = 0

        while True:
            try:
                data = stream.read(chunk, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)

                if len(audio_data) > 0:
                    # Calculate RMS
                    mean_square = np.mean(audio_data**2)
                    if mean_square >= 0 and not np.isnan(mean_square):
                        rms = np.sqrt(mean_square)
                        normalized_level = rms / 32768.0

                        # Also calculate peak level (maximum absolute value)
                        peak_level = np.max(np.abs(audio_data)) / 32768.0

                        # Keep track of recent levels
                        recent_levels.append(normalized_level)
                        if (
                            len(recent_levels) > 50
                        ):  # Keep last 50 readings (~5 seconds)
                            recent_levels.pop(0)

                        avg_recent = np.mean(recent_levels)
                        max_recent = max(max_recent, normalized_level)

                        # Detect significant spikes
                        if (
                            normalized_level > avg_recent * 3
                            and normalized_level > 0.002
                        ):
                            print(
                                f"🔥 CLAP DETECTED! RMS: {normalized_level:.6f}, Peak: {peak_level:.6f}"
                            )
                        elif normalized_level > 0.001:
                            print(
                                f"Audio: RMS={normalized_level:.6f}, Peak={peak_level:.6f}, Avg={avg_recent:.6f}"
                            )

                        # Show max level achieved so far
                        if len(recent_levels) % 100 == 0:  # Every ~10 seconds
                            print(f"📊 Max level so far: {max_recent:.6f}")

            except Exception as e:
                print(f"Error reading audio: {e}")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print(f"\n📊 Final Stats:")
        print(f"Maximum level achieved: {max_recent:.6f}")
        print(f"Average recent level: {avg_recent:.6f}")

    except Exception as e:
        print(f"Failed to open audio device {device_index}: {e}")
        return False

    finally:
        if "stream" in locals():
            stream.stop_stream()
            stream.close()
        audio.terminate()

    return True


def test_all_devices():
    """Test all available input devices"""
    audio = pyaudio.PyAudio()

    input_devices = []
    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        if device_info["maxInputChannels"] > 0:
            input_devices.append(i)

    audio.terminate()

    print(f"Found {len(input_devices)} input devices: {input_devices}")

    for device_id in input_devices:
        print(f"\n{'=' * 60}")
        success = test_clap_detection(device_id)
        if not success:
            continue

        response = input(f"\nTry next device? (y/n): ").lower()
        if response != "y":
            break


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        device_id = int(sys.argv[1])
        test_clap_detection(device_id)
    else:
        print("Testing default device (0) first...")
        print("Usage: python test_clap_detection.py [device_number]")
        print("Or just run without arguments to test device 0")
        print()
        test_clap_detection(0)

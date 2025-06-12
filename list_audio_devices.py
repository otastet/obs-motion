import pyaudio


def list_audio_devices():
    audio = pyaudio.PyAudio()

    print("Available Audio Input Devices:")
    print("=" * 50)

    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)

        # Only show input devices
        if device_info["maxInputChannels"] > 0:
            print(f"Device {i}: {device_info['name']}")
            print(f"  - Max Input Channels: {device_info['maxInputChannels']}")
            print(f"  - Default Sample Rate: {device_info['defaultSampleRate']}")
            print(
                f"  - Host API: {audio.get_host_api_info_by_index(device_info['hostApi'])['name']}"
            )
            print()

    # Get default input device
    try:
        default_device = audio.get_default_input_device_info()
        print(
            f"Default Input Device: {default_device['index']} - {default_device['name']}"
        )
    except:
        print("No default input device found")

    audio.terminate()


if __name__ == "__main__":
    list_audio_devices()

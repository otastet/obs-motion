from obswebsocket import obsws, requests
from config import OBS_HOST, OBS_PORT, OBS_PASSWORD


def check_recording_settings():
    try:
        # Connect to OBS
        ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
        ws.connect()
        print("Connected to OBS successfully!")

        # Get recording folder
        try:
            folder_response = ws.call(requests.GetRecordingFolder())
            print(f"Recording folder: {folder_response.datain}")
        except Exception as e:
            print(f"Could not get recording folder: {e}")

        # Try to get output settings (might not be available in all versions)
        try:
            # This might not work in all OBS WebSocket versions
            output_response = ws.call(requests.GetOutputInfo("adv_file_output"))
            print(f"Output info: {output_response.datain}")
        except Exception as e:
            print(f"Could not get output info: {e}")

        ws.disconnect()

    except Exception as e:
        print(f"Error connecting to OBS: {e}")


if __name__ == "__main__":
    check_recording_settings()

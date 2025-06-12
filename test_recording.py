from obswebsocket import obsws, requests
from config import OBS_HOST, OBS_PORT, OBS_PASSWORD
import time


def test_recording():
    try:
        # Connect to OBS
        ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
        ws.connect()
        print("Connected to OBS successfully!")

        # Check current recording status
        status = ws.call(requests.GetRecordingStatus())
        print(f"Current recording status: {status.datain}")

        # Try to start recording
        print("Attempting to start recording...")
        try:
            result = ws.call(requests.StartRecording())
            print(f"Start recording result: {result.datain}")
        except Exception as e:
            print(f"Failed to start recording: {e}")

        # Check status again
        time.sleep(1)
        status = ws.call(requests.GetRecordingStatus())
        print(f"Recording status after start: {status.datain}")

        # Wait a bit then stop
        print("Waiting 3 seconds...")
        time.sleep(3)

        # Stop recording
        print("Stopping recording...")
        try:
            result = ws.call(requests.StopRecording())
            print(f"Stop recording result: {result.datain}")
        except Exception as e:
            print(f"Failed to stop recording: {e}")

        # Final status check
        status = ws.call(requests.GetRecordingStatus())
        print(f"Final recording status: {status.datain}")

        ws.disconnect()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_recording()

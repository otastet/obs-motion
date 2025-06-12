import asyncio
import logging
import threading
import time
from datetime import datetime
from obswebsocket import obsws, requests
from config import OBS_HOST, OBS_PORT, OBS_PASSWORD, RECORDING_DURATION


class OBSController:
    def __init__(self):
        self.ws = None
        self.is_recording = False
        self.recording_task = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Connect to OBS WebSocket"""
        try:
            self.ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
            self.ws.connect()
            self.logger.info(f"Connected to OBS at {OBS_HOST}:{OBS_PORT}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to OBS: {e}")
            return False

    def is_connected(self):
        """Check if connected to OBS WebSocket"""
        return self.ws is not None and hasattr(self.ws, "ws") and self.ws.ws is not None

    def disconnect(self):
        """Disconnect from OBS WebSocket"""
        if self.ws:
            self.ws.disconnect()
            self.logger.info("Disconnected from OBS")

    def start_recording(self, trigger_type="unknown"):
        """Start recording and schedule automatic stop after duration"""
        if self.is_recording:
            self.logger.info("Recording already in progress")
            return False

        try:
            # Check if OBS is already recording
            status = self.ws.call(requests.GetRecordingStatus())
            if status.datain["isRecording"]:
                self.logger.info("OBS is already recording")
                return False

            # Start recording
            self.ws.call(requests.StartRecording())
            self.is_recording = True
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(
                f"Recording started at {timestamp} (triggered by: {trigger_type})"
            )

            # Schedule automatic stop
            self.recording_task = threading.Thread(target=self._auto_stop_recording)
            self.recording_task.daemon = True  # Make it a daemon thread
            self.recording_task.start()
            return True

        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            return False

    def stop_recording(self):
        """Stop recording manually"""
        if not self.is_recording:
            self.logger.info("No recording in progress")
            return False

        try:
            self.ws.call(requests.StopRecording())
            self.is_recording = False
            if self.recording_task and self.recording_task.is_alive():
                # Don't join daemon threads, just let them finish naturally
                pass
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.info(f"Recording stopped at {timestamp}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop recording: {e}")
            return False

    def _auto_stop_recording(self):
        """Automatically stop recording after the specified duration"""
        try:
            time.sleep(RECORDING_DURATION)
            self.stop_recording()
            self.logger.info(
                f"Recording automatically stopped after {RECORDING_DURATION} seconds"
            )
        except Exception as e:
            self.logger.error(f"Auto-stop recording error: {e}")

    def get_recording_status(self):
        """Get current recording status"""
        try:
            status = self.ws.call(requests.GetRecordingStatus())
            return status.datain["isRecording"]
        except Exception as e:
            self.logger.error(f"Failed to get recording status: {e}")
            return False

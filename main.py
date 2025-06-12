#!/usr/bin/env python3
"""
OBS Auto Recording App
Automatically triggers OBS recording when motion or audio is detected.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime

from obs_controller import OBSController
from motion_detector import MotionDetector
from audio_detector import AudioDetector
from config import RECORDING_DURATION


class AutoRecordingApp:
    def __init__(self):
        self.obs_controller = OBSController()
        self.motion_detector = None
        self.audio_detector = None
        self.is_running = False
        self.logger = self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("obs_auto_record.log"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        return logging.getLogger(__name__)

    def on_detection(self, trigger_type):
        """Callback function when motion or audio is detected"""
        self.logger.info(f"Detection triggered by: {trigger_type}")
        success = self.obs_controller.start_recording(trigger_type)
        if success:
            self.logger.info(f"Recording will run for {RECORDING_DURATION} seconds")
        else:
            self.logger.warning(
                "Failed to start recording or recording already in progress"
            )

    def start(self):
        """Start the auto recording system"""
        self.logger.info("Starting OBS Auto Recording App...")

        # Connect to OBS
        if not self.obs_controller.connect():
            self.logger.error(
                "Failed to connect to OBS. Make sure OBS is running with WebSocket server enabled."
            )
            return False

        # Initialize motion detector
        # self.motion_detector = MotionDetector(on_motion_callback=self.on_detection)
        # self.motion_detector.start_detection()

        # Initialize audio detector
        self.audio_detector = AudioDetector(on_audio_callback=self.on_detection)
        self.audio_detector.start_detection()

        self.is_running = True
        self.logger.info("Auto recording system started successfully!")
        self.logger.info("Monitoring for motion and audio...")

        return True

    def stop(self):
        """Stop the auto recording system"""
        self.logger.info("Stopping auto recording system...")
        self.is_running = False

        # Stop detectors
        if self.motion_detector:
            self.motion_detector.stop_detection()
        if self.audio_detector:
            self.audio_detector.stop_detection()

        # Stop any ongoing recording
        if self.obs_controller.is_recording:
            self.obs_controller.stop_recording()

        # Disconnect from OBS
        self.obs_controller.disconnect()

        self.logger.info("Auto recording system stopped")

    def run(self):
        """Main run loop"""
        if not self.start():
            return

        try:
            # Print status every 30 seconds
            last_status_time = 0

            while self.is_running:
                current_time = time.time()

                # Print status update
                if current_time - last_status_time >= 30:
                    recording_status = (
                        "RECORDING"
                        if self.obs_controller.is_recording
                        else "MONITORING"
                    )
                    self.logger.info(f"Status: {recording_status}")
                    last_status_time = current_time

                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.stop()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nReceived shutdown signal. Stopping...")
    sys.exit(0)


def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run the app
    app = AutoRecordingApp()

    print("=" * 60)
    print("OBS Auto Recording App")
    print("=" * 60)
    print("Prerequisites:")
    print("1. OBS Studio must be running")
    print("2. OBS WebSocket server must be enabled (Tools > obs-websocket Settings)")
    print("3. Camera and microphone must be accessible")
    print("4. Configure settings in .env file or use defaults")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60)

    try:
        app.run()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

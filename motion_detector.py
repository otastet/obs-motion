import cv2
import numpy as np
import threading
import time
import logging
from config import (
    CAMERA_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    MOTION_THRESHOLD,
    MOTION_SENSITIVITY,
    COOLDOWN_PERIOD,
)


class MotionDetector:
    def __init__(self, on_motion_callback=None):
        self.on_motion_callback = on_motion_callback
        self.cap = None
        self.background_subtractor = None
        self.is_running = False
        self.thread = None
        self.last_detection_time = 0
        self.logger = logging.getLogger(__name__)

    def initialize_camera(self):
        """Initialize camera capture"""
        try:
            self.cap = cv2.VideoCapture(CAMERA_INDEX)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

            if not self.cap.isOpened():
                raise Exception("Could not open camera")

            # Initialize background subtractor
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=50, detectShadows=True
            )

            self.logger.info(f"Camera initialized: {FRAME_WIDTH}x{FRAME_HEIGHT}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {e}")
            return False

    def start_detection(self):
        """Start motion detection in a separate thread"""
        if self.is_running:
            self.logger.info("Motion detection already running")
            return

        if not self.initialize_camera():
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._detection_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Motion detection started")

    def stop_detection(self):
        """Stop motion detection"""
        self.is_running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
        self.logger.info("Motion detection stopped")

    def _detection_loop(self):
        """Main detection loop"""
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.warning("Failed to read frame from camera")
                    continue

                # Apply background subtraction
                fg_mask = self.background_subtractor.apply(frame)

                # Remove noise
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

                # Find contours
                contours, _ = cv2.findContours(
                    fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                # Check for significant motion
                motion_detected = False
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > MOTION_THRESHOLD:
                        motion_detected = True
                        break

                if motion_detected:
                    current_time = time.time()
                    # Check cooldown period
                    if current_time - self.last_detection_time >= COOLDOWN_PERIOD:
                        self.last_detection_time = current_time
                        self.logger.info("Motion detected!")
                        if self.on_motion_callback:
                            self.on_motion_callback("motion")

                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in motion detection loop: {e}")
                time.sleep(1)

    def get_preview_frame(self):
        """Get current frame for preview (optional)"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None

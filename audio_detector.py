import pyaudio
import numpy as np
import threading
import time
import logging
from config import AUDIO_THRESHOLD, AUDIO_DEVICE_INDEX, COOLDOWN_PERIOD


class AudioDetector:
    def __init__(self, on_audio_callback=None):
        self.on_audio_callback = on_audio_callback
        self.audio = None
        self.stream = None
        self.is_running = False
        self.thread = None
        self.last_detection_time = 0
        self.logger = logging.getLogger(__name__)

        # Audio parameters
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100

        # Peak-based detection parameters
        self.peak_threshold = 0.5  # Use 0.5 as peak threshold for clap detection
        self.rms_threshold = AUDIO_THRESHOLD  # Keep RMS as backup for sustained sounds

        # Current levels for GUI display
        self.current_peak = 0.0
        self.current_rms = 0.0
        self.current_audio_data = np.array([])
        self.levels_lock = threading.Lock()

    def initialize_audio(self):
        """Initialize audio capture"""
        try:
            self.audio = pyaudio.PyAudio()

            # List available audio devices (for debugging)
            self.logger.info("Available audio devices:")
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                self.logger.info(
                    f"  Device {i}: {info['name']} - {info['maxInputChannels']} input channels"
                )

            # Open audio stream
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=AUDIO_DEVICE_INDEX,
                frames_per_buffer=self.chunk,
            )

            self.logger.info(
                f"Audio initialized: device {AUDIO_DEVICE_INDEX}, rate {self.rate}Hz"
            )
            self.logger.info(
                f"Peak threshold: {self.peak_threshold:.3f}, RMS threshold: {self.rms_threshold:.6f}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize audio: {e}")
            return False

    def start_detection(self):
        """Start audio detection in a separate thread"""
        if self.is_running:
            self.logger.info("Audio detection already running")
            return

        if not self.initialize_audio():
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._detection_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Audio detection started")

    def stop_detection(self):
        """Stop audio detection"""
        self.is_running = False
        if self.thread:
            self.thread.join()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        self.logger.info("Audio detection stopped")

    def _detection_loop(self):
        """Main detection loop with peak-based detection"""
        while self.is_running:
            try:
                # Read audio data
                data = self.stream.read(self.chunk, exception_on_overflow=False)

                # Convert to numpy array
                audio_data = np.frombuffer(data, dtype=np.int16)

                if len(audio_data) > 0:
                    # Calculate peak level for sharp sounds (primary detection method)
                    peak_level = np.max(np.abs(audio_data)) / 32768.0

                    # Calculate RMS for sustained sounds (backup detection)
                    mean_square = np.mean(audio_data**2)
                    if mean_square >= 0 and not np.isnan(mean_square):
                        rms = np.sqrt(mean_square)
                        normalized_rms = rms / 32768.0
                    else:
                        normalized_rms = 0.0

                    # Update current levels and raw audio data for GUI
                    with self.levels_lock:
                        self.current_peak = peak_level
                        self.current_rms = normalized_rms
                        # Store normalized audio data for oscilloscope
                        self.current_audio_data = (
                            audio_data.astype(np.float32) / 32768.0
                        )

                    # Primary detection: Peak-based (great for claps, snaps, etc.)
                    peak_triggered = peak_level > self.peak_threshold

                    # Backup detection: RMS-based (for sustained sounds)
                    rms_triggered = normalized_rms > self.rms_threshold

                    if peak_triggered or rms_triggered:
                        current_time = time.time()
                        # Check cooldown period
                        if current_time - self.last_detection_time >= COOLDOWN_PERIOD:
                            self.last_detection_time = current_time

                            # Log which detection method triggered
                            if peak_triggered:
                                detection_type = "PEAK"
                                main_level = peak_level
                            else:
                                detection_type = "RMS"
                                main_level = normalized_rms

                            self.logger.info(
                                f"Audio detected! [{detection_type}] Peak: {peak_level:.3f}, RMS: {normalized_rms:.6f}"
                            )

                            if self.on_audio_callback:
                                self.on_audio_callback("audio")

            except Exception as e:
                self.logger.error(f"Error in audio detection loop: {e}")
                time.sleep(0.1)

    def get_current_level(self):
        """Get current peak level (for monitoring)"""
        with self.levels_lock:
            return self.current_peak

    def get_current_levels(self):
        """Get both current peak and RMS levels"""
        with self.levels_lock:
            return self.current_peak, self.current_rms

    def get_current_rms(self):
        """Get current RMS level"""
        with self.levels_lock:
            return self.current_rms

    def get_current_audio_data(self):
        """Get current raw audio data for oscilloscope display"""
        with self.levels_lock:
            return (
                self.current_audio_data.copy()
                if len(self.current_audio_data) > 0
                else np.array([])
            )

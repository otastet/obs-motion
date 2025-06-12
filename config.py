import os
from dotenv import load_dotenv

load_dotenv()

# OBS WebSocket Configuration
OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", 4444))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")

# Motion Detection Configuration
MOTION_THRESHOLD = int(
    os.getenv("MOTION_THRESHOLD", 1000)
)  # Minimum area of motion to trigger
MOTION_SENSITIVITY = int(
    os.getenv("MOTION_SENSITIVITY", 25)
)  # Motion detection sensitivity (0-255)

# Audio Detection Configuration
AUDIO_THRESHOLD = float(
    os.getenv("AUDIO_THRESHOLD", 0.01)
)  # Minimum audio level to trigger
AUDIO_DEVICE_INDEX = int(os.getenv("AUDIO_DEVICE_INDEX", 0))  # Audio input device index

# Recording Configuration
RECORDING_DURATION = int(
    os.getenv("RECORDING_DURATION", 3600)
)  # Recording duration in seconds (1 hour)
COOLDOWN_PERIOD = int(
    os.getenv("COOLDOWN_PERIOD", 30)
)  # Cooldown period between detections (seconds)

# Camera Configuration
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))  # Camera device index
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", 640))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", 480))

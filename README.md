# OBS Auto Recording App

An intelligent application that automatically triggers OBS Studio recordings when motion or audio is detected. Perfect for security monitoring, wildlife observation, or any scenario where you need automatic recording based on environmental triggers.

## Features

- **Motion Detection**: Uses computer vision to detect movement in camera feed
- **Audio Detection**: Monitors microphone input for sound above threshold
- **Automatic Recording**: Triggers 1-hour OBS recordings when activity is detected
- **Cooldown Period**: Prevents multiple triggers in quick succession
- **Configurable Settings**: Customize thresholds, devices, and recording duration
- **Logging**: Comprehensive logging of all activities and detections

## Prerequisites

1. **OBS Studio** must be installed and running
2. **OBS WebSocket Plugin** must be enabled:
   - In OBS: Tools > obs-websocket Settings
   - Enable WebSocket server
   - Note the port (default: 4455) and set password if needed
3. **Python 3.7+** must be installed
4. **Camera and microphone** must be accessible to the system

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` to configure your settings (optional, defaults work for most setups)

## Configuration

All settings can be configured via the `.env` file:

### OBS Settings
- `OBS_HOST`: OBS WebSocket host (default: localhost)
- `OBS_PORT`: OBS WebSocket port (default: 4455)
- `OBS_PASSWORD`: OBS WebSocket password (if set)

### Motion Detection
- `MOTION_THRESHOLD`: Minimum motion area to trigger (default: 1000)
- `MOTION_SENSITIVITY`: Motion detection sensitivity 0-255 (default: 25)
- `CAMERA_INDEX`: Camera device index (default: 0)
- `FRAME_WIDTH`: Camera frame width (default: 640)
- `FRAME_HEIGHT`: Camera frame height (default: 480)

### Audio Detection
- `AUDIO_THRESHOLD`: Minimum audio level to trigger 0-1 (default: 0.01)
- `AUDIO_DEVICE_INDEX`: Audio input device index (default: 0)

### Recording Settings
- `RECORDING_DURATION`: Recording length in seconds (default: 3600 = 1 hour)
- `COOLDOWN_PERIOD`: Seconds between detections (default: 30)

## Usage

1. **Start OBS Studio** and ensure WebSocket server is enabled
2. **Run the application**:
   ```bash
   python main.py
   ```
3. The app will start monitoring for motion and audio
4. When detected, it will automatically start OBS recording for the configured duration
5. Press `Ctrl+C` to stop the application

## How It Works

1. **Initialization**: Connects to OBS WebSocket and initializes camera/audio
2. **Monitoring**: Continuously monitors camera feed and audio input
3. **Detection**: When motion or audio exceeds thresholds, triggers recording
4. **Recording**: Starts OBS recording for specified duration (default: 1 hour)
5. **Cooldown**: Prevents retriggering for cooldown period
6. **Auto-Stop**: Automatically stops recording after duration expires

## Troubleshooting

### Common Issues

**"Failed to connect to OBS"**
- Ensure OBS Studio is running
- Check that WebSocket server is enabled in OBS settings
- Verify host/port/password in `.env` file

**"Could not open camera"**
- Check camera permissions
- Try different `CAMERA_INDEX` values (0, 1, 2, etc.)
- Ensure camera isn't being used by another application

**"Failed to initialize audio"**
- Check microphone permissions
- Try different `AUDIO_DEVICE_INDEX` values
- Run the app to see available audio devices in logs

**"No motion detected"**
- Adjust `MOTION_THRESHOLD` (lower = more sensitive)
- Adjust `MOTION_SENSITIVITY` (lower = more sensitive)
- Ensure adequate lighting for camera

**"No audio detected"**
- Lower `AUDIO_THRESHOLD` value
- Check microphone levels in system settings
- Ensure microphone isn't muted

### Finding Device Indices

The application logs available cameras and audio devices on startup. Check the logs to find the correct indices for your devices.

## Logs

The application creates detailed logs in `obs_auto_record.log` and displays them in the console. Monitor these logs to understand detection events and troubleshoot issues.

## Advanced Usage

### Custom Triggers
You can extend the detection system by modifying the callback functions in `main.py` to add custom logic or additional trigger conditions.

### Multiple Cameras
To monitor multiple cameras, you can run multiple instances with different `CAMERA_INDEX` values.

### Scene-Specific Recording
Modify `obs_controller.py` to switch to specific scenes before recording or use different recording settings.

## License

This project is open source and available under the MIT License. 
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import logging
from datetime import datetime
import os
import math
from dotenv import load_dotenv
import numpy as np

# Import your existing modules
from obs_controller import OBSController
from audio_detector import AudioDetector
from motion_detector import MotionDetector

# Load environment variables
load_dotenv()


class CircularMeterKnob(tk.Canvas):
    """Combined circular level meter and threshold knob widget"""

    def __init__(
        self,
        parent,
        min_val=0,
        max_val=1,
        initial_val=0.5,
        resolution=0.01,
        size=120,
        callback=None,
        label="",
        meter_color="#4CAF50",
        **kwargs,
    ):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg="#2b2b2b",
            highlightthickness=0,
            **kwargs,
        )

        self.min_val = min_val
        self.max_val = max_val
        self.current_val = initial_val
        self.resolution = resolution
        self.size = size
        self.callback = callback
        self.label = label
        self.meter_color = meter_color

        self.center_x = size // 2
        self.center_y = size // 2
        self.outer_radius = size // 2 - 10
        self.inner_radius = size // 2 - 25
        self.knob_radius = 6

        # Current level for meter display
        self.current_level = 0.0
        self.level_lock = threading.Lock()

        self.dragging = False

        self.draw_widget()
        self.bind_events()

    def draw_widget(self):
        """Draw the combined meter and knob"""
        self.delete("all")

        # Draw outer track circle
        self.create_oval(
            self.center_x - self.outer_radius,
            self.center_y - self.outer_radius,
            self.center_x + self.outer_radius,
            self.center_y + self.outer_radius,
            outline="#555555",
            width=2,
            fill="#1e1e1e",
        )

        # Draw inner track circle
        self.create_oval(
            self.center_x - self.inner_radius,
            self.center_y - self.inner_radius,
            self.center_x + self.inner_radius,
            self.center_y + self.inner_radius,
            outline="#333333",
            width=1,
            fill="#2b2b2b",
        )

        # Calculate angles (start from -135° and go clockwise, 270° total range)
        with self.level_lock:
            current_level = self.current_level

        # Draw level meter arc (from bottom, following same direction as knob)
        level_ratio = min(current_level / self.max_val, 1.0)
        level_extent = level_ratio * 270
        if level_extent > 0:
            self.create_arc(
                self.center_x - self.inner_radius + 2,
                self.center_y - self.inner_radius + 2,
                self.center_x + self.inner_radius - 2,
                self.center_y + self.inner_radius - 2,
                start=-135,
                extent=level_extent,
                outline=self.meter_color,
                width=6,
                style="arc",
            )

        # Calculate threshold knob position
        threshold_ratio = (self.current_val - self.min_val) / (
            self.max_val - self.min_val
        )
        # Invert the ratio to match the inverted mouse interaction
        # Higher values should appear at lower angles (counterclockwise from start)
        inverted_ratio = 1.0 - threshold_ratio
        threshold_extent = inverted_ratio * 270

        # Draw threshold arc (outer ring) - extent matches inverted knob position
        if threshold_extent > 0:
            self.create_arc(
                self.center_x - self.outer_radius + 3,
                self.center_y - self.outer_radius + 3,
                self.center_x + self.outer_radius - 3,
                self.center_y + self.outer_radius - 3,
                start=-135,
                extent=threshold_extent,
                outline="#FF9800",
                width=4,
                style="arc",
            )

        # Calculate knob handle position (at the END of the orange arc)
        # The knob should be at the end of the arc
        knob_angle = -135 + threshold_extent  # End of the arc
        knob_angle_rad = math.radians(knob_angle)
        arc_radius = self.outer_radius - 3  # Same radius as the orange arc
        knob_x = self.center_x + arc_radius * math.cos(knob_angle_rad)
        knob_y = self.center_y + arc_radius * math.sin(knob_angle_rad)

        # Draw threshold knob handle
        self.create_oval(
            knob_x - self.knob_radius,
            knob_y - self.knob_radius,
            knob_x + self.knob_radius,
            knob_y + self.knob_radius,
            fill="#FFC107",
            outline="#FF9800",
            width=2,
        )

        # Draw center area with values
        center_bg = self.create_oval(
            self.center_x - 25,
            self.center_y - 25,
            self.center_x + 25,
            self.center_y + 25,
            fill="#1e1e1e",
            outline="#444444",
            width=1,
        )

        # Draw current level value
        level_text = (
            f"{current_level:.3f}" if self.max_val >= 1 else f"{current_level:.6f}"
        )
        self.create_text(
            self.center_x,
            self.center_y - 8,
            text=level_text,
            fill="white",
            font=("Arial", 8, "bold"),
        )

        # Draw threshold value
        threshold_text = (
            f"{self.current_val:.2f}"
            if self.max_val >= 1
            else f"{self.current_val:.4f}"
        )
        self.create_text(
            self.center_x,
            self.center_y + 8,
            text=threshold_text,
            fill="#FFC107",
            font=("Arial", 8, "bold"),
        )

        # Draw label below
        if self.label:
            self.create_text(
                self.center_x,
                self.center_y + self.outer_radius + 15,
                text=self.label,
                fill="white",
                font=("Arial", 11, "bold"),
            )

        # Draw legend
        self.create_text(
            self.center_x,
            self.center_y + self.outer_radius + 30,
            text="Level | Threshold",
            fill="#888888",
            font=("Arial", 8),
        )

    def bind_events(self):
        """Bind mouse events"""
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)

    def on_click(self, event):
        """Handle mouse click"""
        # Calculate current knob position using same logic as drawing
        threshold_ratio = (self.current_val - self.min_val) / (
            self.max_val - self.min_val
        )
        threshold_extent = threshold_ratio * 270
        knob_angle = -135 + threshold_extent  # End of the arc
        knob_angle_rad = math.radians(knob_angle)
        arc_radius = self.outer_radius - 3
        knob_x = self.center_x + arc_radius * math.cos(knob_angle_rad)
        knob_y = self.center_y + arc_radius * math.sin(knob_angle_rad)

        # Check if click is near the knob handle
        dx = event.x - knob_x
        dy = event.y - knob_y
        distance_to_knob = math.sqrt(dx * dx + dy * dy)

        # Also allow clicks anywhere on the outer arc for convenience
        dx_center = event.x - self.center_x
        dy_center = event.y - self.center_y
        distance_from_center = math.sqrt(dx_center * dx_center + dy_center * dy_center)

        # Respond to clicks either near the knob or on the outer arc area
        if distance_to_knob <= 15 or (
            distance_from_center >= self.inner_radius + 10
            and distance_from_center <= self.outer_radius + 5
        ):
            self.dragging = True
            self.update_threshold_from_mouse(event.x, event.y)

    def on_drag(self, event):
        """Handle mouse drag"""
        if self.dragging:
            self.update_threshold_from_mouse(event.x, event.y)

    def on_release(self, event):
        """Handle mouse release"""
        self.dragging = False

    def update_threshold_from_mouse(self, x, y):
        """Update threshold value based on mouse position along the arc"""
        dx = x - self.center_x
        dy = y - self.center_y

        if dx == 0 and dy == 0:
            return

        # Calculate angle from mouse position
        angle = math.degrees(math.atan2(dy, dx))

        # Normalize angle to -135° to +135° range (270° total sweep)
        if angle < -135:
            angle = -135
        elif angle > 135:
            # Handle the wrap-around case
            if angle > 180:
                angle = -135
            else:
                angle = 135

        # Convert angle to value (0 to 1 ratio)
        # This should make clockwise movement increase the value
        value_ratio = (angle + 135) / 270
        new_val = self.min_val + value_ratio * (self.max_val - self.min_val)

        # Apply resolution and bounds
        new_val = round(new_val / self.resolution) * self.resolution
        new_val = max(self.min_val, min(self.max_val, new_val))

        # Update value if changed
        if abs(new_val - self.current_val) > self.resolution / 2:
            self.current_val = new_val
            self.draw_widget()

            if self.callback:
                self.callback(self.current_val)

    def set_threshold(self, value):
        """Set threshold value programmatically"""
        value = max(self.min_val, min(self.max_val, value))
        if value != self.current_val:
            self.current_val = value
            self.draw_widget()

    def set_level(self, level):
        """Set current level for meter display"""
        with self.level_lock:
            self.current_level = level
        self.draw_widget()

    def get_threshold(self):
        """Get current threshold value"""
        return self.current_val

    def get_level(self):
        """Get current level value"""
        with self.level_lock:
            return self.current_level


class OscilloscopeWidget(tk.Canvas):
    """Real-time oscilloscope display for audio waveform"""

    def __init__(self, parent, width=400, height=150, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg="#0a0a0a",  # Darker background
            highlightthickness=2,
            highlightbackground="#00ff41",  # Matrix green border
            **kwargs,
        )

        self.width = width
        self.height = height
        self.center_y = height // 2
        self.waveform_data = np.zeros(width)
        self.data_lock = threading.Lock()

        # Cool colors
        self.grid_color = "#001a00"  # Dark green grid
        self.waveform_color = "#00ff41"  # Bright matrix green
        self.center_line_color = "#004400"  # Medium green center line
        self.glow_color = "#88ff88"  # Light green glow

        self.draw_grid()

    def draw_grid(self):
        """Draw the cool oscilloscope grid"""
        self.delete("all")

        # Draw subtle horizontal grid lines
        for i in range(0, self.height + 1, self.height // 8):
            self.create_line(0, i, self.width, i, fill=self.grid_color, width=1)

        # Draw subtle vertical grid lines
        for i in range(0, self.width + 1, self.width // 16):
            self.create_line(i, 0, i, self.height, fill=self.grid_color, width=1)

        # Draw center line (0V reference) with glow effect
        self.create_line(
            0,
            self.center_y,
            self.width,
            self.center_y,
            fill=self.center_line_color,
            width=3,
        )

        # Add corner indicators for that retro scope look
        corner_size = 10
        # Top-left
        self.create_line(0, 0, corner_size, 0, fill=self.waveform_color, width=2)
        self.create_line(0, 0, 0, corner_size, fill=self.waveform_color, width=2)
        # Top-right
        self.create_line(
            self.width - corner_size,
            0,
            self.width,
            0,
            fill=self.waveform_color,
            width=2,
        )
        self.create_line(
            self.width, 0, self.width, corner_size, fill=self.waveform_color, width=2
        )
        # Bottom-left
        self.create_line(
            0,
            self.height - corner_size,
            0,
            self.height,
            fill=self.waveform_color,
            width=2,
        )
        self.create_line(
            0, self.height, corner_size, self.height, fill=self.waveform_color, width=2
        )
        # Bottom-right
        self.create_line(
            self.width,
            self.height - corner_size,
            self.width,
            self.height,
            fill=self.waveform_color,
            width=2,
        )
        self.create_line(
            self.width - corner_size,
            self.height,
            self.width,
            self.height,
            fill=self.waveform_color,
            width=2,
        )

    def update_waveform(self, audio_data):
        """Update the waveform display with new audio data"""
        if len(audio_data) == 0:
            return

        with self.data_lock:
            # Downsample audio data to fit display width
            if len(audio_data) > self.width:
                # Take every nth sample
                step = len(audio_data) // self.width
                self.waveform_data = audio_data[::step][: self.width]
            else:
                # Pad or repeat data to fill width
                self.waveform_data = np.resize(audio_data, self.width)

            # Normalize to display range with some headroom
            if np.max(np.abs(self.waveform_data)) > 0:
                self.waveform_data = (
                    self.waveform_data / np.max(np.abs(self.waveform_data)) * 0.8
                )  # Scale to 80% for better visual

        self.draw_waveform()

    def draw_waveform(self):
        """Draw the current waveform with cool effects"""
        self.draw_grid()

        with self.data_lock:
            if len(self.waveform_data) < 2:
                return

            # Create points for the main waveform
            points = []
            for i, sample in enumerate(self.waveform_data):
                x = i
                y = self.center_y - (sample * (self.height // 2 - 15))
                points.extend([x, y])

            # Draw glow effect (thicker, lighter line behind)
            if len(points) >= 4:
                self.create_line(points, fill=self.glow_color, width=4, smooth=True)

            # Draw main waveform line (thinner, brighter line on top)
            if len(points) >= 4:
                self.create_line(points, fill=self.waveform_color, width=2, smooth=True)

            # Add peak indicators for high amplitude sections
            for i, sample in enumerate(self.waveform_data):
                if abs(sample) > 0.7:  # High amplitude
                    x = i
                    y = self.center_y - (sample * (self.height // 2 - 15))
                    # Draw a small bright dot at peaks
                    self.create_oval(
                        x - 2, y - 2, x + 2, y + 2, fill="#ffff00", outline="#ffff00"
                    )


class OBSAutoRecorderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OBS Auto Recording App - GUI")
        self.root.geometry("800x800")
        self.root.configure(bg="#2b2b2b")

        # Initialize components
        self.obs_controller = None
        self.audio_detector = None
        self.motion_detector = None

        # State variables
        self.is_running = False
        self.current_peak = 0.0
        self.current_rms = 0.0
        self.peak_threshold = 0.5
        self.rms_threshold = 0.003

        # Setup logging
        self.setup_logging()

        # Create GUI
        self.create_widgets()

        # Start audio monitoring thread
        self.start_audio_monitoring()

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("obs_auto_recorder_gui.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def create_widgets(self):
        """Create the GUI widgets"""
        # Title
        title_label = tk.Label(
            self.root,
            text="OBS Auto Recording App",
            font=("Arial", 18, "bold"),
            bg="#2b2b2b",
            fg="white",
        )
        title_label.pack(pady=10)

        # Connection Status Frame
        status_frame = tk.Frame(self.root, bg="#2b2b2b")
        status_frame.pack(pady=10, padx=20, fill="x")

        tk.Label(
            status_frame,
            text="OBS Connection:",
            font=("Arial", 12),
            bg="#2b2b2b",
            fg="white",
        ).pack(side="left")
        self.status_label = tk.Label(
            status_frame,
            text="Disconnected",
            font=("Arial", 12, "bold"),
            bg="#2b2b2b",
            fg="red",
        )
        self.status_label.pack(side="left", padx=(10, 0))

        # Oscilloscope Frame
        scope_frame = tk.LabelFrame(
            self.root,
            text="Audio Waveform (Real-time)",
            font=("Arial", 12, "bold"),
            bg="#2b2b2b",
            fg="white",
        )
        scope_frame.pack(pady=10, padx=20, fill="x")

        self.oscilloscope = OscilloscopeWidget(scope_frame, width=750, height=150)
        self.oscilloscope.pack(pady=10)

        # Combined Audio Meters Frame
        meters_frame = tk.LabelFrame(
            self.root,
            text="Audio Detection Controls",
            font=("Arial", 12, "bold"),
            bg="#2b2b2b",
            fg="white",
        )
        meters_frame.pack(pady=20, padx=20, fill="x")

        # Meters container
        meters_container = tk.Frame(meters_frame, bg="#2b2b2b")
        meters_container.pack(pady=20)

        # Peak Meter-Knob
        peak_frame = tk.Frame(meters_container, bg="#2b2b2b")
        peak_frame.pack(side="left", padx=40)

        self.peak_meter_knob = CircularMeterKnob(
            peak_frame,
            min_val=0.1,
            max_val=1.0,
            initial_val=self.peak_threshold,
            resolution=0.05,
            size=140,
            callback=self.update_peak_threshold,
            label="PEAK",
            meter_color="#FF5722",
        )
        self.peak_meter_knob.pack()

        # RMS Meter-Knob
        rms_frame = tk.Frame(meters_container, bg="#2b2b2b")
        rms_frame.pack(side="left", padx=40)

        self.rms_meter_knob = CircularMeterKnob(
            rms_frame,
            min_val=0.001,
            max_val=0.01,
            initial_val=self.rms_threshold,
            resolution=0.0005,
            size=140,
            callback=self.update_rms_threshold,
            label="RMS",
            meter_color="#2196F3",
        )
        self.rms_meter_knob.pack()

        # Detection indicator
        indicator_frame = tk.Frame(self.root, bg="#2b2b2b")
        indicator_frame.pack(pady=10)

        tk.Label(
            indicator_frame,
            text="Detection Status:",
            font=("Arial", 12),
            bg="#2b2b2b",
            fg="white",
        ).pack(side="left")

        self.detection_indicator = tk.Canvas(
            indicator_frame, width=30, height=30, bg="#2b2b2b", highlightthickness=0
        )
        self.detection_indicator.pack(side="left", padx=(10, 0))
        self.detection_circle = self.detection_indicator.create_oval(
            5, 5, 25, 25, fill="gray", outline="darkgray", width=2
        )

        # Control Buttons Frame
        control_frame = tk.Frame(self.root, bg="#2b2b2b")
        control_frame.pack(pady=20)

        self.connect_button = tk.Button(
            control_frame,
            text="Connect to OBS",
            command=self.connect_obs,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=10,
        )
        self.connect_button.pack(side="left", padx=10)

        self.start_button = tk.Button(
            control_frame,
            text="Start Monitoring",
            command=self.start_monitoring,
            font=("Arial", 12, "bold"),
            bg="#2196F3",
            fg="white",
            padx=20,
            pady=10,
            state="disabled",
        )
        self.start_button.pack(side="left", padx=10)

        self.stop_button = tk.Button(
            control_frame,
            text="Stop Monitoring",
            command=self.stop_monitoring,
            font=("Arial", 12, "bold"),
            bg="#f44336",
            fg="white",
            padx=20,
            pady=10,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=10)

        # Log Display Frame
        log_frame = tk.LabelFrame(
            self.root,
            text="Activity Log",
            font=("Arial", 12, "bold"),
            bg="#2b2b2b",
            fg="white",
        )
        log_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Create scrollable text widget for logs
        self.log_text = tk.Text(
            log_frame, height=6, bg="#1e1e1e", fg="white", font=("Consolas", 9)
        )
        scrollbar = tk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add initial log message
        self.add_log("GUI initialized. Ready to connect to OBS.")

    def update_peak_threshold(self, value):
        """Update peak threshold"""
        self.peak_threshold = float(value)
        if self.audio_detector:
            self.audio_detector.peak_threshold = self.peak_threshold

    def update_rms_threshold(self, value):
        """Update RMS threshold"""
        self.rms_threshold = float(value)
        if self.audio_detector:
            self.audio_detector.rms_threshold = self.rms_threshold

    def add_log(self, message):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)

        # Keep only last 100 lines
        lines = self.log_text.get("1.0", tk.END).split("\n")
        if len(lines) > 100:
            self.log_text.delete("1.0", f"{len(lines) - 100}.0")

    def connect_obs(self):
        """Connect to OBS"""
        try:
            self.obs_controller = OBSController()
            if self.obs_controller.connect():
                self.status_label.config(text="Connected", fg="green")
                self.start_button.config(state="normal")
                self.add_log("Successfully connected to OBS")
            else:
                self.status_label.config(text="Failed", fg="red")
                self.add_log("Failed to connect to OBS")
                messagebox.showerror(
                    "Connection Error",
                    "Failed to connect to OBS. Please check your settings.",
                )
        except Exception as e:
            self.add_log(f"Error connecting to OBS: {e}")
            messagebox.showerror("Connection Error", f"Error: {e}")

    def start_monitoring(self):
        """Start audio and motion monitoring"""
        try:
            # Initialize audio detector with callback
            self.audio_detector = AudioDetector(
                on_audio_callback=self.on_audio_detected
            )
            self.audio_detector.peak_threshold = self.peak_threshold
            self.audio_detector.rms_threshold = self.rms_threshold
            self.audio_detector.start_detection()

            # Initialize motion detector
            self.motion_detector = MotionDetector(
                on_motion_callback=self.on_motion_detected
            )
            self.motion_detector.start_detection()

            self.is_running = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.connect_button.config(state="disabled")

            self.add_log("Started audio and motion monitoring")

        except Exception as e:
            self.add_log(f"Error starting monitoring: {e}")
            messagebox.showerror("Monitoring Error", f"Error: {e}")

    def stop_monitoring(self):
        """Stop audio and motion monitoring"""
        try:
            self.is_running = False

            if self.audio_detector:
                self.audio_detector.stop_detection()
                self.audio_detector = None

            if self.motion_detector:
                self.motion_detector.stop_detection()
                self.motion_detector = None

            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.connect_button.config(state="normal")

            # Reset indicators
            self.detection_indicator.itemconfig(self.detection_circle, fill="gray")
            self.peak_meter_knob.set_level(0.0)
            self.rms_meter_knob.set_level(0.0)

            self.add_log("Stopped monitoring")

        except Exception as e:
            self.add_log(f"Error stopping monitoring: {e}")

    def on_audio_detected(self, detection_type):
        """Handle audio detection"""
        self.add_log(f"Audio detected! ({detection_type})")

        # Flash detection indicator
        self.detection_indicator.itemconfig(
            self.detection_circle, fill="red", outline="darkred"
        )
        self.root.after(
            300,
            lambda: self.detection_indicator.itemconfig(
                self.detection_circle, fill="gray", outline="darkgray"
            ),
        )

        if self.obs_controller and self.obs_controller.is_connected():
            self.obs_controller.start_recording()

    def on_motion_detected(self, detection_type):
        """Handle motion detection"""
        self.add_log(f"Motion detected! ({detection_type})")

        # Flash detection indicator
        self.detection_indicator.itemconfig(
            self.detection_circle, fill="orange", outline="darkorange"
        )
        self.root.after(
            300,
            lambda: self.detection_indicator.itemconfig(
                self.detection_circle, fill="gray", outline="darkgray"
            ),
        )

        if self.obs_controller and self.obs_controller.is_connected():
            self.obs_controller.start_recording()

    def start_audio_monitoring(self):
        """Start the audio level monitoring thread"""

        def monitor_audio():
            while True:
                if self.audio_detector and self.is_running:
                    try:
                        # Get current audio levels (both peak and RMS)
                        peak_level, rms_level = self.audio_detector.get_current_levels()

                        # Get raw audio data for oscilloscope
                        raw_audio_data = self.audio_detector.get_current_audio_data()

                        # Update GUI in main thread
                        self.root.after(
                            0,
                            self.update_audio_display,
                            peak_level,
                            rms_level,
                            raw_audio_data,
                        )

                    except Exception as e:
                        pass  # Ignore errors during monitoring
                else:
                    # When not running, still update with zero values
                    self.root.after(
                        0, self.update_audio_display, 0.0, 0.0, np.array([])
                    )

                time.sleep(0.05)  # Update 20 times per second

        monitor_thread = threading.Thread(target=monitor_audio, daemon=True)
        monitor_thread.start()

    def update_audio_display(self, peak_level, rms_level, raw_audio_data=None):
        """Update the audio level display with both peak and RMS levels"""
        # Update the circular meter-knobs
        self.peak_meter_knob.set_level(peak_level)
        self.rms_meter_knob.set_level(rms_level)

        # Get raw audio data for oscilloscope if not provided
        if raw_audio_data is None and hasattr(
            self.audio_detector, "get_current_audio_data"
        ):
            raw_audio_data = self.audio_detector.get_current_audio_data()

        # Update oscilloscope
        if raw_audio_data is not None and len(raw_audio_data) > 0:
            self.oscilloscope.update_waveform(raw_audio_data)

        # Update status display
        status_text = f"Peak: {peak_level:.3f} | RMS: {rms_level:.6f}"
        if peak_level > self.peak_meter_knob.current_val:
            status_text += " | PEAK DETECTED!"
        self.status_label.config(text=status_text)

    def on_closing(self):
        """Handle window closing"""
        if self.is_running:
            self.stop_monitoring()
        if self.obs_controller:
            self.obs_controller.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = OBSAutoRecorderGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

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
import random
from scipy import fft

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


class ArtisticAudioVisualizer(tk.Canvas):
    """Artistic audio visualizer with multiple visualization modes"""

    def __init__(self, parent, width=800, height=200, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg="#000011",  # Deep space blue
            highlightthickness=2,
            highlightbackground="#4444ff",
            **kwargs,
        )

        self.width = width
        self.height = height
        self.center_x = width // 2
        self.center_y = height // 2

        # Visualization modes
        self.modes = [
            "spectrum",
            "radial_wave",
            "particles",
            "geometric",
            "flowing_wave",
        ]
        self.current_mode = 0

        # Audio data storage
        self.waveform_data = np.zeros(width)
        self.spectrum_data = np.zeros(128)  # FFT bins
        self.data_lock = threading.Lock()

        # Enhanced audio analysis
        self.audio_history = []  # Store recent audio for better analysis
        self.max_history_length = 10
        self.bass_energy = 0.0
        self.mid_energy = 0.0
        self.treble_energy = 0.0
        self.overall_energy = 0.0
        self.peak_detection_threshold = 0.3
        self.energy_smoothing = 0.8  # Smoothing factor for energy changes

        # Animation state
        self.frame_count = 0
        self.particles = []
        self.trails = []
        self.energy_boost = 1.0  # Dynamic energy multiplier
        self.last_peak_time = 0

        # Color palettes
        self.color_palettes = [
            ["#ff0080", "#ff8000", "#ffff00", "#80ff00", "#00ff80"],  # Neon rainbow
            ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7"],  # Warm sunset
            ["#a8e6cf", "#dcedc1", "#ffd3a5", "#ffd8a8", "#f8b195"],  # Soft pastels
            [
                "#667eea",
                "#764ba2",
                "#f093fb",
                "#f5576c",
                "#4facfe",
            ],  # Purple-pink gradient
            ["#00c9ff", "#92fe9d", "#ffcd3c", "#fd746c", "#ff9068"],  # Ocean vibes
        ]
        self.current_palette = 0

        # Initialize particles for particle mode
        self.init_particles()

        # Bind click to cycle modes
        self.bind("<Button-1>", self.cycle_mode)

        self.draw_background()

    def init_particles(self):
        """Initialize particle system"""
        self.particles = []
        for _ in range(80):  # Increased particle count
            particle = {
                "x": random.randint(0, self.width),
                "y": random.randint(0, self.height),
                "vx": random.uniform(-1, 1),
                "vy": random.uniform(-1, 1),
                "size": random.uniform(1, 3),
                "life": random.uniform(0.5, 1.0),
                "color_index": random.randint(0, 4),
                "energy_response": random.uniform(
                    0.5, 2.0
                ),  # Individual energy sensitivity
                "base_size": random.uniform(1, 3),
            }
            self.particles.append(particle)

    def cycle_mode(self, event=None):
        """Cycle through visualization modes"""
        self.current_mode = (self.current_mode + 1) % len(self.modes)
        self.current_palette = (self.current_palette + 1) % len(self.color_palettes)
        self.draw_background()

    def get_color_from_palette(self, index, alpha=1.0):
        """Get color from current palette"""
        colors = self.color_palettes[self.current_palette]
        return colors[index % len(colors)]

    def analyze_audio_frequencies(self, audio_data):
        """Analyze audio into frequency bands for more responsive visuals"""
        if len(audio_data) < 256:
            return

        # Calculate FFT
        fft_data = np.abs(fft.fft(audio_data[:512]))[:256]

        # Normalize
        if np.max(fft_data) > 0:
            fft_data = fft_data / np.max(fft_data)

        # Split into frequency bands
        bass_range = fft_data[1:20]  # Low frequencies
        mid_range = fft_data[20:80]  # Mid frequencies
        treble_range = fft_data[80:128]  # High frequencies

        # Calculate energy for each band with enhanced sensitivity
        new_bass = np.mean(bass_range) * 3.0  # Boost bass response
        new_mid = np.mean(mid_range) * 2.0  # Boost mid response
        new_treble = np.mean(treble_range) * 2.5  # Boost treble response
        new_overall = np.mean(np.abs(audio_data)) * 4.0  # Overall energy boost

        # Smooth the energy changes but keep responsiveness
        smoothing = self.energy_smoothing
        self.bass_energy = self.bass_energy * smoothing + new_bass * (1 - smoothing)
        self.mid_energy = self.mid_energy * smoothing + new_mid * (1 - smoothing)
        self.treble_energy = self.treble_energy * smoothing + new_treble * (
            1 - smoothing
        )
        self.overall_energy = self.overall_energy * smoothing + new_overall * (
            1 - smoothing
        )

        # Detect peaks for extra visual effects
        if new_overall > self.peak_detection_threshold:
            self.last_peak_time = self.frame_count
            self.energy_boost = min(3.0, self.energy_boost + 0.5)
        else:
            self.energy_boost = max(1.0, self.energy_boost * 0.95)

    def draw_background(self):
        """Draw animated background"""
        self.delete("all")

        # Draw animated background grid or pattern
        if self.current_mode in ["spectrum", "flowing_wave"]:
            # Grid background with energy response
            grid_intensity = min(255, int(self.overall_energy * 100))
            grid_color = f"#{grid_intensity:02x}{grid_intensity // 2:02x}{grid_intensity // 4:02x}"

            for i in range(0, self.width, 40):
                self.create_line(i, 0, i, self.height, fill=grid_color, width=1)
            for i in range(0, self.height, 20):
                self.create_line(0, i, self.width, i, fill=grid_color, width=1)
        elif self.current_mode == "radial_wave":
            # Concentric circles that pulse with bass
            base_spacing = 30
            pulse_spacing = base_spacing - int(self.bass_energy * 15)
            for radius in range(
                20, max(self.width, self.height), max(15, pulse_spacing)
            ):
                intensity = min(255, int(self.bass_energy * 150))
                circle_color = (
                    f"#{intensity // 4:02x}{intensity // 3:02x}{intensity:02x}"
                )
                self.create_oval(
                    self.center_x - radius,
                    self.center_y - radius,
                    self.center_x + radius,
                    self.center_y + radius,
                    outline=circle_color,
                    width=1,
                )

    def update_waveform(self, audio_data):
        """Update visualization with new audio data"""
        if len(audio_data) == 0:
            return

        with self.data_lock:
            # Store waveform data
            if len(audio_data) > self.width:
                step = len(audio_data) // self.width
                self.waveform_data = audio_data[::step][: self.width]
            else:
                self.waveform_data = np.resize(audio_data, self.width)

            # Enhanced audio analysis
            self.analyze_audio_frequencies(audio_data)

            # Store audio history for trend analysis
            self.audio_history.append(np.mean(np.abs(audio_data)))
            if len(self.audio_history) > self.max_history_length:
                self.audio_history.pop(0)

            # Calculate FFT for spectrum analysis with better resolution
            if len(audio_data) >= 512:
                fft_data = np.abs(fft.fft(audio_data[:512]))[:128]
                self.spectrum_data = (
                    fft_data / np.max(fft_data) if np.max(fft_data) > 0 else fft_data
                )

        self.frame_count += 1
        self.draw_visualization()

    def draw_visualization(self):
        """Draw the current visualization mode"""
        mode = self.modes[self.current_mode]

        if mode == "spectrum":
            self.draw_spectrum_analyzer()
        elif mode == "radial_wave":
            self.draw_radial_waveform()
        elif mode == "particles":
            self.draw_particle_system()
        elif mode == "geometric":
            self.draw_geometric_patterns()
        elif mode == "flowing_wave":
            self.draw_flowing_waveform()

        # Draw mode indicator with energy level
        energy_text = f"Energy: {self.overall_energy:.2f}"
        self.create_text(
            self.width - 10,
            10,
            text=f"Mode: {mode.title()} | {energy_text}",
            fill="#666666",
            font=("Arial", 10),
            anchor="ne",
        )

    def draw_spectrum_analyzer(self):
        """Draw frequency spectrum as artistic bars"""
        self.draw_background()

        with self.data_lock:
            spectrum = self.spectrum_data

        bar_width = self.width / len(spectrum)
        max_height = self.height - 40

        for i, magnitude in enumerate(spectrum):
            # Enhanced sensitivity - show even small frequencies
            if magnitude > 0.005:  # Lower threshold
                x = i * bar_width
                # Apply energy boost and frequency-specific scaling
                freq_boost = 1.0
                if i < 20:  # Bass frequencies
                    freq_boost = 1.0 + self.bass_energy * 2
                elif i < 80:  # Mid frequencies
                    freq_boost = 1.0 + self.mid_energy * 1.5
                else:  # Treble frequencies
                    freq_boost = 1.0 + self.treble_energy * 1.8

                height = magnitude * max_height * freq_boost * self.energy_boost
                height = min(height, max_height)  # Cap at max height

                # Create gradient effect with more segments for smoother look
                segments = max(1, int(height / 3))
                for seg in range(segments):
                    seg_height = min(3, height - seg * 3)
                    if seg_height <= 0:
                        break

                    color_index = int((seg / segments) * 4)
                    color = self.get_color_from_palette(color_index)

                    self.create_rectangle(
                        x,
                        self.height - seg * 3 - seg_height,
                        x + bar_width - 1,
                        self.height - seg * 3,
                        fill=color,
                        outline="",
                    )

                # Enhanced glow effect for high energy
                if height > max_height * 0.5 or self.overall_energy > 0.3:
                    glow_width = 2 + int(self.overall_energy * 4)
                    self.create_rectangle(
                        x - glow_width,
                        self.height - height - 10,
                        x + bar_width + glow_width,
                        self.height - height + 5,
                        outline=self.get_color_from_palette(0),
                        width=glow_width,
                    )

    def draw_radial_waveform(self):
        """Draw waveform in a radial/circular pattern"""
        self.draw_background()

        with self.data_lock:
            waveform = self.waveform_data

        if len(waveform) == 0:
            return

        # Dynamic radius based on energy
        base_radius = 40 + int(self.overall_energy * 40)
        max_radius_extension = 60 + int(self.overall_energy * 80)

        points = []
        glow_points = []

        # Multiple rings for richer visual
        for ring in range(3):
            ring_points = []
            ring_scale = 1.0 - (ring * 0.2)
            ring_radius = base_radius * ring_scale

            for i, sample in enumerate(waveform):
                angle = (i / len(waveform)) * 2 * math.pi
                # Enhanced animation with energy response
                animated_angle = angle + (
                    self.frame_count * 0.03 * (1 + self.overall_energy)
                )

                # Different frequency responses for different rings
                if ring == 0:  # Outer ring - overall energy
                    radius = (
                        ring_radius
                        + abs(sample) * max_radius_extension * self.energy_boost
                    )
                elif ring == 1:  # Middle ring - mid frequencies
                    radius = ring_radius + abs(sample) * max_radius_extension * 0.7 * (
                        1 + self.mid_energy
                    )
                else:  # Inner ring - bass frequencies
                    radius = ring_radius + abs(sample) * max_radius_extension * 0.5 * (
                        1 + self.bass_energy
                    )

                x = self.center_x + radius * math.cos(animated_angle)
                y = self.center_y + radius * math.sin(animated_angle)

                ring_points.extend([x, y])

                # Create glow points for high amplitude (more sensitive)
                if abs(sample) > 0.3 or self.overall_energy > 0.2:
                    glow_radius = radius + 15 + int(self.treble_energy * 20)
                    glow_x = self.center_x + glow_radius * math.cos(animated_angle)
                    glow_y = self.center_y + glow_radius * math.sin(animated_angle)
                    glow_points.extend([glow_x, glow_y])

            # Draw ring
            if len(ring_points) >= 4:
                color = self.get_color_from_palette(ring)
                width = 3 - ring
                self.create_line(ring_points, fill=color, width=width, smooth=True)

        # Draw glow effect
        if len(glow_points) >= 4:
            self.create_line(
                glow_points, fill=self.get_color_from_palette(1), width=6, smooth=True
            )

        # Enhanced center pulse
        pulse_size = 15 + (self.overall_energy * 50) + (self.bass_energy * 30)
        pulse_color = self.get_color_from_palette(2)
        self.create_oval(
            self.center_x - pulse_size,
            self.center_y - pulse_size,
            self.center_x + pulse_size,
            self.center_y + pulse_size,
            fill=pulse_color,
            outline=self.get_color_from_palette(3),
            width=3,
        )

    def draw_particle_system(self):
        """Draw particle system that reacts to audio"""
        self.draw_background()

        # Update particles with enhanced audio response
        for particle in self.particles:
            # Move particles
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]

            # Enhanced audio reaction
            energy_factor = particle["energy_response"]

            # Different particles respond to different frequencies
            if particle["color_index"] < 2:  # Bass-responsive particles
                response_energy = self.bass_energy * energy_factor
            elif particle["color_index"] < 4:  # Mid-responsive particles
                response_energy = self.mid_energy * energy_factor
            else:  # Treble-responsive particles
                response_energy = self.treble_energy * energy_factor

            if response_energy > 0.05:  # Lower threshold for more responsiveness
                # Add energy-based movement
                particle["vx"] += random.uniform(-1, 1) * response_energy
                particle["vy"] += random.uniform(-1, 1) * response_energy
                particle["size"] = particle["base_size"] + response_energy * 8

                # Limit velocity to prevent particles from going too fast
                max_vel = 5 + response_energy * 3
                particle["vx"] = max(-max_vel, min(max_vel, particle["vx"]))
                particle["vy"] = max(-max_vel, min(max_vel, particle["vy"]))
            else:
                particle["size"] = max(particle["base_size"], particle["size"] * 0.9)
                # Apply friction when no audio
                particle["vx"] *= 0.98
                particle["vy"] *= 0.98

            # Wrap around screen
            if particle["x"] < 0:
                particle["x"] = self.width
            elif particle["x"] > self.width:
                particle["x"] = 0
            if particle["y"] < 0:
                particle["y"] = self.height
            elif particle["y"] > self.height:
                particle["y"] = 0

            # Draw particle with energy-based effects
            color = self.get_color_from_palette(particle["color_index"])
            size = particle["size"]

            # Add glow effect for high energy particles
            if size > particle["base_size"] * 2:
                glow_size = size + 3
                self.create_oval(
                    particle["x"] - glow_size,
                    particle["y"] - glow_size,
                    particle["x"] + glow_size,
                    particle["y"] + glow_size,
                    fill="",
                    outline=color,
                    width=2,
                )

            self.create_oval(
                particle["x"] - size,
                particle["y"] - size,
                particle["x"] + size,
                particle["y"] + size,
                fill=color,
                outline="",
            )

            # Enhanced connections between particles
            for other in self.particles:
                if other != particle:
                    dx = particle["x"] - other["x"]
                    dy = particle["y"] - other["y"]
                    distance = math.sqrt(dx * dx + dy * dy)

                    # More connections when there's audio energy
                    max_distance = 80 + int(self.overall_energy * 60)
                    if distance < max_distance and self.overall_energy > 0.02:
                        alpha = max(0, 1 - distance / max_distance)
                        line_width = 1 + int(self.overall_energy * 3)
                        self.create_line(
                            particle["x"],
                            particle["y"],
                            other["x"],
                            other["y"],
                            fill=self.get_color_from_palette(2),
                            width=line_width,
                        )

    def draw_geometric_patterns(self):
        """Draw geometric patterns that morph with audio"""
        self.draw_background()

        # Enhanced geometric response
        num_shapes = 5
        for i in range(num_shapes):
            # Calculate shape parameters based on different frequency bands
            base_radius = 25 + i * 12

            # Different shapes respond to different frequencies
            if i < 2:  # First shapes respond to bass
                energy_response = self.bass_energy
            elif i < 4:  # Middle shapes respond to mids
                energy_response = self.mid_energy
            else:  # Last shape responds to treble
                energy_response = self.treble_energy

            radius = base_radius + energy_response * 60 * self.energy_boost
            sides = max(3, 6 + int(energy_response * 15))  # More dramatic side changes
            rotation = (self.frame_count * 0.08 * (1 + energy_response)) + (i * 0.4)

            # Shape position with energy-based movement
            offset_x = (i - num_shapes // 2) * 120
            shape_x = (
                self.center_x
                + offset_x
                + math.cos(self.frame_count * 0.05 + i) * energy_response * 30
            )
            shape_y = self.center_y + math.sin(self.frame_count * 0.03 + i) * (
                20 + energy_response * 40
            )

            # Create polygon points
            points = []
            for vertex in range(sides):
                angle = (vertex / sides) * 2 * math.pi + rotation
                px = shape_x + radius * math.cos(angle)
                py = shape_y + radius * math.sin(angle)
                points.extend([px, py])

            if len(points) >= 6:
                # Enhanced colors based on energy
                color_intensity = min(1.0, energy_response * 2)
                color = self.get_color_from_palette(i)
                outline_color = self.get_color_from_palette((i + 1) % 5)

                # Draw filled shape with energy-based transparency effect
                self.create_polygon(
                    points,
                    fill=color,
                    outline=outline_color,
                    width=2 + int(energy_response * 3),
                )

                # Add multiple inner shapes for depth when energy is high
                inner_layers = 1 + int(energy_response * 3)
                for layer in range(inner_layers):
                    inner_points = []
                    inner_scale = 0.8 - (layer * 0.15)
                    inner_radius = radius * inner_scale

                    for vertex in range(sides):
                        angle = (
                            (vertex / sides) * 2 * math.pi + rotation + (layer * 0.2)
                        )
                        px = shape_x + inner_radius * math.cos(angle)
                        py = shape_y + inner_radius * math.sin(angle)
                        inner_points.extend([px, py])

                    if len(inner_points) >= 6:
                        self.create_polygon(
                            inner_points,
                            fill="",
                            outline=self.get_color_from_palette((i + layer + 2) % 5),
                            width=max(1, 2 - layer),
                        )

    def draw_flowing_waveform(self):
        """Draw flowing waveform with trails and effects"""
        self.draw_background()

        with self.data_lock:
            waveform = self.waveform_data

        if len(waveform) == 0:
            return

        # Enhanced flowing layers with frequency separation
        layers = 4  # More layers for richer visual
        for layer in range(layers):
            points = []
            layer_offset = (layer - layers // 2) * 25

            # Different layers respond to different frequencies
            if layer == 0:  # Bass layer
                layer_scale = 1.2 * (1 + self.bass_energy)
                time_offset = self.frame_count * 0.08
            elif layer == 1:  # Mid layer
                layer_scale = 1.0 * (1 + self.mid_energy)
                time_offset = self.frame_count * 0.12
            elif layer == 2:  # Treble layer
                layer_scale = 0.8 * (1 + self.treble_energy)
                time_offset = self.frame_count * 0.15
            else:  # Overall energy layer
                layer_scale = 0.6 * (1 + self.overall_energy)
                time_offset = self.frame_count * 0.20

            for i, sample in enumerate(waveform):
                x = i * (self.width / len(waveform))
                # Enhanced flowing animation with energy response
                wave_amplitude = sample * 100 * layer_scale * self.energy_boost
                flowing_wave = math.sin(x * 0.03 + time_offset) * (
                    10 + self.overall_energy * 20
                )
                y = self.center_y + layer_offset + wave_amplitude + flowing_wave
                points.extend([x, y])

            if len(points) >= 4:
                color = self.get_color_from_palette(layer)
                width = max(1, 5 - layer + int(self.overall_energy * 3))
                self.create_line(points, fill=color, width=width, smooth=True)

        # Enhanced sparkle effects at peaks (more sensitive)
        sparkle_threshold = 0.4 - (
            self.overall_energy * 0.2
        )  # Lower threshold when energy is high
        for i, sample in enumerate(waveform):
            if abs(sample) > sparkle_threshold:
                x = i * (self.width / len(waveform))
                y = self.center_y + sample * 100 * self.energy_boost

                # Enhanced sparkle with energy response
                sparkle_size = 3 + abs(sample) * 8 + self.treble_energy * 10
                sparkle_color = self.get_color_from_palette(4)

                # Main sparkle
                self.create_oval(
                    x - sparkle_size,
                    y - sparkle_size,
                    x + sparkle_size,
                    y + sparkle_size,
                    fill=sparkle_color,
                    outline="",
                )

                # Enhanced sparkle rays with more rays for high energy
                num_rays = 4 + int(self.overall_energy * 8)
                for ray in range(num_rays):
                    angle = (ray / num_rays) * 2 * math.pi
                    ray_length = sparkle_size * (2 + self.overall_energy * 2)
                    end_x = x + ray_length * math.cos(angle)
                    end_y = y + ray_length * math.sin(angle)
                    self.create_line(
                        x,
                        y,
                        end_x,
                        end_y,
                        fill=sparkle_color,
                        width=max(1, 2 + int(self.overall_energy * 2)),
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
            text="Artistic Audio Visualizer (click to change modes)",
            font=("Arial", 12, "bold"),
            bg="#2b2b2b",
            fg="white",
        )
        scope_frame.pack(pady=10, padx=20, fill="x")

        self.oscilloscope = ArtisticAudioVisualizer(scope_frame, width=750, height=150)
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

                        # Get raw audio data for visualization
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

        # Get raw audio data for visualization if not provided
        if raw_audio_data is None and hasattr(
            self.audio_detector, "get_current_audio_data"
        ):
            raw_audio_data = self.audio_detector.get_current_audio_data()

        # Update visualization
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

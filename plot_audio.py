import pyaudio
import numpy as np
import matplotlib.pyplot as plt
import time
from datetime import datetime


def plot_audio_levels():
    # Audio parameters
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 44100
    duration = 30  # 30 seconds

    # Storage for data
    timestamps = []
    rms_levels = []
    peak_levels = []

    # Peak-based detection parameters (matching audio_detector.py)
    peak_threshold = 0.5  # Primary threshold for peak detection
    rms_threshold = 0.003  # Backup threshold for RMS detection

    # Track detections
    peak_detections = []
    rms_detections = []

    audio = pyaudio.PyAudio()

    print(f"Recording audio levels for {duration} seconds...")
    print("Make various sounds: speak, clap, tap, etc.")
    print(f"Peak threshold: {peak_threshold:.3f} (PRIMARY)")
    print(f"RMS threshold: {rms_threshold:.6f} (backup)")
    print("-" * 50)

    try:
        stream = audio.open(
            format=format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=0,  # MacBook Pro Microphone
            frames_per_buffer=chunk,
        )

        start_time = time.time()

        while time.time() - start_time < duration:
            try:
                data = stream.read(chunk, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)

                if len(audio_data) > 0:
                    # Calculate peak level for sharp sounds (primary detection)
                    peak_level = np.max(np.abs(audio_data)) / 32768.0

                    # Calculate RMS for sustained sounds (backup detection)
                    mean_square = np.mean(audio_data**2)
                    if mean_square >= 0 and not np.isnan(mean_square):
                        rms = np.sqrt(mean_square)
                        normalized_rms = rms / 32768.0
                    else:
                        normalized_rms = 0.0

                    current_time = time.time() - start_time
                    timestamps.append(current_time)
                    rms_levels.append(normalized_rms)
                    peak_levels.append(peak_level)

                    # Detection logic: check both methods
                    peak_triggered = peak_level > peak_threshold
                    rms_triggered = normalized_rms > rms_threshold

                    # Store detection points for plotting
                    if peak_triggered:
                        peak_detections.append((current_time, peak_level))
                    if rms_triggered:
                        rms_detections.append((current_time, normalized_rms))

                    # Print detections
                    if peak_triggered or rms_triggered:
                        if peak_triggered:
                            detection_type = "PEAK"
                        else:
                            detection_type = "RMS"

                        print(
                            f"Time {current_time:.1f}s: [{detection_type}] Peak: {peak_level:.3f}, RMS: {normalized_rms:.6f}"
                        )

            except Exception as e:
                print(f"Error reading audio: {e}")

            time.sleep(0.01)  # Small delay

        stream.stop_stream()
        stream.close()

    except Exception as e:
        print(f"Failed to open audio device: {e}")
        return

    audio.terminate()

    # Create enhanced plot focused on peak detection
    plt.figure(figsize=(15, 10))

    # Plot 1: Peak levels with detections (PRIMARY)
    plt.subplot(2, 1, 1)
    plt.plot(
        timestamps, peak_levels, "g-", linewidth=1.0, alpha=0.8, label="Peak Level"
    )
    plt.axhline(
        y=peak_threshold,
        color="r",
        linestyle="--",
        linewidth=2,
        label=f"Peak Threshold ({peak_threshold})",
    )

    # Mark peak detections
    if peak_detections:
        peak_times, peak_vals = zip(*peak_detections)
        plt.scatter(
            peak_times,
            peak_vals,
            color="red",
            s=50,
            alpha=0.9,
            label="Peak Detections",
            zorder=5,
        )

    plt.ylabel("Peak Level (0.0 - 1.0)")
    plt.title("Peak Audio Level Over Time (PRIMARY DETECTION)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Plot 2: RMS levels with detections (BACKUP)
    plt.subplot(2, 1, 2)
    plt.plot(timestamps, rms_levels, "b-", linewidth=1.0, alpha=0.8, label="RMS Level")
    plt.axhline(
        y=rms_threshold,
        color="orange",
        linestyle="--",
        linewidth=2,
        label=f"RMS Threshold ({rms_threshold})",
    )

    # Mark RMS detections
    if rms_detections:
        rms_times, rms_vals = zip(*rms_detections)
        plt.scatter(
            rms_times,
            rms_vals,
            color="orange",
            s=40,
            alpha=0.9,
            label="RMS Detections",
            zorder=5,
        )

    plt.ylabel("RMS Level (0.0 - 0.1)")
    plt.xlabel("Time (seconds)")
    plt.title("RMS Audio Level Over Time (BACKUP DETECTION)")
    plt.ylim(0, 0.1)  # Zoom in for RMS detail
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save the plot
    filename = f"peak_audio_levels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    print(f"\nPlot saved as: {filename}")

    # Show peak-focused statistics
    max_peak = max(peak_levels) if peak_levels else 0
    max_rms = max(rms_levels) if rms_levels else 0
    avg_peak = np.mean(peak_levels) if peak_levels else 0
    avg_rms = np.mean(rms_levels) if rms_levels else 0

    print(f"\nPeak-Based Detection Statistics:")
    print(f"Maximum Peak level: {max_peak:.3f}")
    print(f"Average Peak level: {avg_peak:.3f}")
    print(f"Maximum RMS level: {max_rms:.6f}")
    print(f"Average RMS level: {avg_rms:.6f}")
    print(f"Peak detections: {len(peak_detections)} (PRIMARY)")
    print(f"RMS detections: {len(rms_detections)} (backup)")
    print(f"Total detections: {len(peak_detections) + len(rms_detections)}")

    if max_peak > 0:
        print(f"\nPeak threshold effectiveness:")
        print(
            f"Your loudest sound reached {max_peak:.3f} (threshold: {peak_threshold:.3f})"
        )
        if max_peak > peak_threshold:
            print("✅ Peak threshold should detect your loud sounds!")
        else:
            print("⚠️  You may need to make louder sounds or lower the threshold")

    plt.show()


if __name__ == "__main__":
    plot_audio_levels()

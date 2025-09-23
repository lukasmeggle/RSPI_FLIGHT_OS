import os
import subprocess
from .pipeline_base import PipelineBase

class CameraPipeline(PipelineBase):
    def __init__(self, camera_type, cfg, laptop_ip, log_dir, record_dir):
        """
        Unified camera pipeline for both IR and Pi cameras.
        Args:
            camera_type: "ir" or "pi"
            cfg: Camera configuration dict
            laptop_ip: IP address for streaming
            log_dir: Directory for logs
            record_dir: Directory for recordings
        """
        self.camera_type = camera_type
        self.cfg = cfg
        self.laptop_ip = laptop_ip
        self.log_dir = log_dir
        self.record_dir = record_dir

        self.width = cfg["width"]
        self.height = cfg["height"]
        self.framerate = cfg["framerate"]
        self.bitrate = cfg["bitrate"]
        self.video_format = cfg.get("video_format", "I420")  # Default to I420 if not specified

        self.stream_enabled = cfg.get("stream", False)
        self.record_enabled = cfg.get("record", False)
        self.display_enabled = cfg.get("display", False)

        # Set up for ir camera
        if camera_type == "ir":
            self.name = "ir_camera"
            self.stream_port = 5000
            self.record_filename = "ir_output.mp4"
            # Build source command for ir camera, use v4l2src
            device = cfg["device"]
            self.source_cmd = [
                "v4l2src", f"device={device}",
                "!", f"video/x-raw,format={self.video_format},width={self.width},height={self.height},framerate={self.framerate}",
                "!", "videoconvert"
            ]
            self.pi_process = None

        # Set up for pi camera
        elif camera_type == "pi":
            self.name = "pi_camera"
            self.stream_port = 5001
            self.record_filename = "pi_output.mp4"
            # Build source command for pi camera, use rpicam-vid and use subprocess PIPE in order to not use bash shell
            self.pi_process = subprocess.Popen(
                ["rpicam-vid", "-t", "0", "-o", "-", "--codec", "yuv420"],
                stdout=subprocess.PIPE
            )
            self.source_cmd = [
                "fdsrc",
                "!", f"videoparse width={self.width} height={self.height} framerate={self.framerate} format={self.video_format}",
                "!", "videoconvert"
            ]
        else:
            raise ValueError("camera_type must be 'ir' or 'pi'")

        # Build output branches
        self.stream_branch = self._build_stream_branch(laptop_ip, self.stream_port) if self.stream_enabled else None
        self.record_branch = self._build_record_branch(record_dir, self.record_filename) if self.record_enabled else None
        self.display_branch = self._build_display_branch() if self.display_enabled else None

        # Build full pipeline
        self.cmd = self._build_pipeline(self.source_cmd, self.bitrate,
                                        self.stream_branch, self.record_branch, self.display_branch)

        # Initialize base class
        super().__init__(name=self.name, cmd=self.cmd, log_dir=self.log_dir)

    def _build_stream_branch(self, laptop_ip, port):
        return ["rtph264pay", "!", "udpsink", f"host={laptop_ip}", f"port={port}"]

    def _build_record_branch(self, record_dir, filename):
        filepath = os.path.join(record_dir, filename)
        return ["mp4mux", "!", "filesink", f"location={filepath}", "async=false"]

    def _build_display_branch(self):
        return ["max-size-buffers=1", "leaky=downstream", "!", "kmssink", "sync=false"]

    def _build_pipeline(self, source_cmd, bitrate, stream_branch, record_branch, display_branch):
        """Build unified pipeline for both IR and Pi cameras."""
        branches_encoded = [b for b in [stream_branch, record_branch] if b]
        branches_raw = [display_branch] if display_branch else []

        if not branches_encoded and not branches_raw:
            return []

        # Start with source
        cmd = source_cmd.copy()

        if branches_encoded or branches_raw:
            if len(branches_encoded) + len(branches_raw) > 1:
                cmd += ["!", "tee", "name=t"]

            # Add raw branches
            for b in branches_raw:
                cmd += ["t.", "!", "queue"] + b

            # Add encoded branches
            if len(branches_encoded) == 1:
                cmd += ["t.", "!", "queue", "!", "x264enc", "tune=zerolatency",
                        f"bitrate={bitrate}", "speed-preset=ultrafast", "!"] + branches_encoded[0]
            elif len(branches_encoded) > 1:
                cmd += ["t.", "!", "queue", "!", "x264enc", "tune=zerolatency",
                        f"bitrate={bitrate}", "speed-preset=ultrafast", "!", "tee", "name=encoded_t"]
                for b in branches_encoded:
                    cmd += ["encoded_t.", "!", "queue"] + b

        return cmd

    def start(self):
        """Start pipeline (Pi camera handled with PIPE)."""
        print(f"[INFO] Starting {self.name}, command: {' '.join(self.cmd)}")
        if self.camera_type == "pi" and self.pi_process:
            # Use fdsrc from Pi camera stdout
            self.process = subprocess.Popen(["gst-launch-1.0"] + self.cmd, stdin=self.pi_process.stdout)
        else:
            self.process = subprocess.Popen(["gst-launch-1.0"] + self.cmd)
        print(f"[INFO] {self.name} started.")

    def stop(self):
        if hasattr(self, "process") and self.process:
            self.process.terminate()
            self.process.wait()
        if self.pi_process:
            self.pi_process.terminate()
            self.pi_process.wait()
        print(f"[INFO] {self.name} stopped.")


# Convenience classes
class IRCameraPipeline(CameraPipeline):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        super().__init__("ir", cfg, laptop_ip, log_dir, record_dir)


class PiCameraPipeline(CameraPipeline):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        super().__init__("pi", cfg, laptop_ip, log_dir, record_dir)
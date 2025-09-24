import os
import subprocess
from .pipeline_base import PipelineBase

class CameraPipeline(PipelineBase):
    def __init__(self, camera_type, cfg, laptop_ip, log_dir, record_dir):
        self.camera_type = camera_type
        self.cfg = cfg
        self.laptop_ip = laptop_ip
        self.log_dir = log_dir
        self.record_dir = record_dir

        self.width = cfg["width"]
        self.height = cfg["height"]
        self.framerate = cfg["framerate"]
        self.bitrate = cfg["bitrate"]
        self.video_format = cfg["video_format"]

        self.stream_enabled = cfg.get("stream", False)
        self.record_enabled = cfg.get("record", False)
        self.display_enabled = cfg.get("display", False)

        if camera_type == "ir":
            self.name = "ir_camera"
            self.stream_port = 5000
            self.record_filename = "ir_output.mp4"
            device = cfg["device"]
            self.source_cmd = (
                f"v4l2src device={device} "
                f"! video/x-raw,format={self.video_format},width={self.width},height={self.height},framerate={self.framerate} "
                "! videoconvert "
            )
            self.pi_process = None

        elif camera_type == "pi":
            self.name = "pi_camera"
            self.stream_port = 5001
            self.record_filename = "pi_output.mp4"
            self.source_cmd = (
                f"fdsrc "
                f"! videoparse width={self.width} height={self.height} framerate={self.framerate} format={self.video_format} "
                "! videoconvert "
            )
            self.pi_process = subprocess.Popen(
                ["rpicam-vid", "-t", "0", "-o", "-", "--codec", "yuv420", "--nopreview"],
                stdout=subprocess.PIPE
            )
        else:
            raise ValueError("camera_type must be 'ir' or 'pi'")

        # Branches
        self.stream_branch = self._build_stream_branch(laptop_ip, self.stream_port) if self.stream_enabled else None
        self.record_branch = self._build_record_branch(record_dir, self.record_filename) if self.record_enabled else None
        self.display_branch = self._build_display_branch() if self.display_enabled else None

        # Vollständige Pipeline
        self.cmd = self._build_pipeline(
            self.source_cmd,
            self.bitrate,
            self.stream_branch,
            self.record_branch,
            self.display_branch
        )

        super().__init__(name=self.name, cmd=self.cmd, log_dir=self.log_dir, stdin_processes=self.pi_process)

    def _build_stream_branch(self, laptop_ip, port):
        return f"! rtph264pay ! udpsink host={laptop_ip} port={port}"

    def _build_record_branch(self, record_dir, filename):
        filepath = os.path.join(record_dir, filename)
        return f"! mp4mux ! filesink location={filepath} async=false"

    def _build_display_branch(self):
        return "! glimagesink sync=false"

    def _build_pipeline(self, source_cmd, bitrate, stream_branch, record_branch, display_branch):
        branches_encoded = [b for b in [stream_branch, record_branch] if b]
        branches_raw = [display_branch] if display_branch else []

        pipeline = source_cmd

        if branches_encoded or branches_raw:
            pipeline += " ! tee name=t"

            # raw branches
            for b in branches_raw:
                pipeline += f" t. {b}"

            # encoded branches
            if len(branches_encoded) == 1:
                pipeline += f" t. ! queue ! x264enc tune=zerolatency bitrate={bitrate} speed-preset=ultrafast {branches_encoded[0]}"
            elif len(branches_encoded) > 1:
                pipeline += f" t. ! queue ! x264enc tune=zerolatency bitrate={bitrate} speed-preset=ultrafast ! tee name=encoded_t"
                for b in branches_encoded:
                    pipeline += f" encoded_t. ! queue {b}"

        full_cmd = f"gst-launch-1.0 -e {pipeline}"
        return full_cmd

# Convenience classes
class IRCameraPipeline(CameraPipeline):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        super().__init__("ir", cfg, laptop_ip, log_dir, record_dir)


class PiCameraPipeline(CameraPipeline):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        super().__init__("pi", cfg, laptop_ip, log_dir, record_dir)
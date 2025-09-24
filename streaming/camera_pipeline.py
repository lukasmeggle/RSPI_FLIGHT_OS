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
            self.source_cmd = f"""
                v4l2src device={device} !
                  video/x-raw,format={self.video_format},width={self.width},height={self.height},framerate={self.framerate} !
                  videoconvert
            """
            self.pi_process = None

        elif camera_type == "pi":
            self.name = "pi_camera"
            self.stream_port = 5001
            self.record_filename = "pi_output.mp4"
            self.source_cmd = f"""
                fdsrc !
                  videoparse width={self.width} height={self.height} framerate={self.framerate} format={self.video_format} !
                  videoconvert
            """
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

        # Pipeline zusammenbauen
        self.cmd = self._build_pipeline(
            self.source_cmd,
            self.bitrate,
            self.stream_branch,
            self.record_branch,
            self.display_branch
        )

        # Pipeline einmal schön formatiert ausgeben
        print("\n[INFO] Final assembled GStreamer pipeline:\n")
        print(self.cmd)
        print("\n")

        super().__init__(name=self.name, cmd=self.cmd, log_dir=self.log_dir, stdin_processes=self.pi_process)

    def _build_stream_branch(self, laptop_ip, port):
        return f"""
            ! rtph264pay config-interval=1 pt=96 !
              udpsink host={laptop_ip} port={port}
        """

    def _build_record_branch(self, record_dir, filename):
        filepath = os.path.join(record_dir, filename)
        return f"""
            ! h264parse config-interval=-1 !
              mp4mux fragment-duration=1000 streamable=true !
              filesink location={filepath} async=false
        """

    def _build_display_branch(self):
        return f"""
            ! video/x-raw,format=NV12,width={self.width},height={self.height} !
              queue max-size-buffers=1 leaky=downstream !
              kmssink sync=false
        """

    def _build_pipeline(self, source_cmd, bitrate, stream_branch, record_branch, display_branch):
        branches_encoded = [b for b in [stream_branch, record_branch] if b]
        branches_raw = [display_branch] if display_branch else []

        pipeline = f"""
            {source_cmd} !
              tee name=t
        """

        # raw (unencoded) branch
        for b in branches_raw:
            pipeline += f"""
              t. {b}
            """

        # encoded branches
        if len(branches_encoded) == 1:
            pipeline += f"""
              t. ! queue !
                x264enc tune=zerolatency bitrate={bitrate} speed-preset=ultrafast
                {branches_encoded[0]}
            """
        elif len(branches_encoded) > 1:
            pipeline += f"""
              t. ! queue !
                x264enc tune=zerolatency bitrate={bitrate} speed-preset=ultrafast !
                tee name=encoded_t
            """
            for b in branches_encoded:
                pipeline += f"""
                  encoded_t. ! queue {b}
                """

        full_cmd = f"gst-launch-1.0 -e {pipeline}"
        # Trim leading/trailing spaces on each line, aber Struktur behalten
        return "\n".join(line.rstrip() for line in full_cmd.splitlines() if line.strip())

# Convenience classes
class IRCameraPipeline(CameraPipeline):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        super().__init__("ir", cfg, laptop_ip, log_dir, record_dir)


class PiCameraPipeline(CameraPipeline):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        super().__init__("pi", cfg, laptop_ip, log_dir, record_dir)
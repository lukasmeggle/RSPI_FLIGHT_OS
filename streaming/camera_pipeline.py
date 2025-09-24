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
                f"v4l2src device={device} !"
                f"video/x-raw,format={self.video_format},width={self.width},height={self.height},framerate={self.framerate} !"
            )
            self.pi_process = None

        elif camera_type == "pi":
            self.name = "pi_camera"
            self.stream_port = 5001
            self.record_filename = "pi_output.mp4"
            self.source_cmd = (
                f"fdsrc !"
                f"videoparse width={self.width} height={self.height} framerate={self.framerate} format={self.video_format} !"
                f"videoconvert ! video/x-raw,format=NV12,width=640,height=480 !"
            )
            self.pi_process = subprocess.Popen(
                ["rpicam-vid", "-t", "0", "-o", "-", "--codec", "yuv420", "--nopreview"],
                stdout=subprocess.PIPE
            )
        else:
            raise ValueError("camera_type must be 'ir' or 'pi'")
        
        # Vollständige Pipeline
        self.cmd = self._build_pipeline()

        super().__init__(name=self.name, cmd=self.cmd, log_dir=self.log_dir, stdin_processes=self.pi_process)


    def _build_pipeline(self):

        pipeline_parts = [f"{self.source_cmd} tee name=t"]  # Raw-split

        # Display-Branch (Raw Data)
        if self.display_enabled:
            pipeline_parts.append(
                "t. ! queue "
                "! videoconvert "
                "! autovideosink sync=false"
            )

        # Encoded-Branch
        if self.stream_enabled or self.record_enabled:
            # Encode once and use tee to split
            pipeline_parts.append(
                "t. ! queue "
                f"! x264enc bitrate={self.bitrate} speed-preset=superfast tune=zerolatency "
                "! h264parse "
                "! tee name=enc"
            )

            # Stream from encoded Branch
            if self.stream_enabled:
                pipeline_parts.append(
                    "enc. ! queue "
                    "! rtph264pay config-interval=1 pt=96 "
                    f"! udpsink host={self.laptop_ip} port={self.stream_port}"
                )

            # Record from encoded Branch
            if self.record_enabled:
                outfile = os.path.join(self.record_dir, self.record_filename)
                pipeline_parts.append(
                    "enc. ! queue "
                    f"! mp4mux ! filesink location={outfile}"
                )

        # Fallback, if no output is enabled
        if not (self.stream_enabled or self.record_enabled or self.display_enabled):
            pipeline_parts.append("t. ! queue ! fakesink sync=false")

        # Finale Command-Assembly + debug output
        self.cmd = " ".join(pipeline_parts)
        print(f"[Pipeline {self.name}] CMD:\n{self.cmd}\n")

# Convenience classes
class IRCameraPipeline(CameraPipeline):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        super().__init__("ir", cfg, laptop_ip, log_dir, record_dir)

class PiCameraPipeline(CameraPipeline):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        super().__init__("pi", cfg, laptop_ip, log_dir, record_dir)
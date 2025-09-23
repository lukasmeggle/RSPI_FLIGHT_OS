import os
from .pipeline_base import PipelineBase

class IRCameraPipeline(PipelineBase):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        device = cfg["device"]
        w, h, fr, br = cfg["width"], cfg["height"], cfg["framerate"], cfg["bitrate"]

        src = [
            "gst-launch-1.0",
            "v4l2src", f"device={device}",
            "!", f"video/x-raw,width={w},height={h},framerate={fr}",
            "!", "videoconvert"
        ]

        branches = []
        if cfg["stream"]:
            branches.append([
                "x264enc", "tune=zerolatency", f"bitrate={br}", "speed-preset=ultrafast",
                "!", "rtph264pay",
                "!", "udpsink", f"host={laptop_ip}", "port=5000"
            ])
        if cfg["record"]:
            branches.append([
                "x264enc", f"bitrate={br}", "speed-preset=superfast",
                "!", "mp4mux",
                "!", "filesink", "location=" + os.path.join(record_dir, "ir_output.mp4")
            ])
        if cfg["display"]:
            branches.append(["kmssink", "sync=false"])

        if not branches:
            cmd = []
        elif len(branches) == 1:
            cmd = src + ["!"] + branches[0]
        else:
            # mit tee für mehrere Sinks
            cmd = src + ["!", "tee", "name=t"]
            for i, b in enumerate(branches):
                cmd += [f"t.", "!", "queue"] + b

        super().__init__(name="ir_camera", cmd=cmd, log_dir=log_dir, record_dir=record_dir)


class PiCameraPipeline(PipelineBase):
    def __init__(self, cfg, laptop_ip, log_dir, record_dir):
        w, h, fr, br = cfg["width"], cfg["height"], cfg["framerate"], cfg["bitrate"]

        # Basis-Befehl: rpicam-vid -> fdsrc -> videoparse -> videoconvert
        base_cmd = f"rpicam-vid -t 0 -o - --codec yuv420 | " \
                   f"gst-launch-1.0 fdsrc ! videoparse width={w} height={h} framerate={fr} format=i420 ! videoconvert"

        branches = []

        # Stream
        if cfg["stream"]:
            branches.append(f"x264enc tune=zerolatency bitrate={br} speed-preset=ultrafast ! "
                            f"rtph264pay config-interval=1 pt=96 ! udpsink host={laptop_ip} port=5001")

        # Record
        if cfg["record"]:
            branches.append(f"x264enc bitrate={br} speed-preset=superfast ! mp4mux ! filesink location="
                            f"{os.path.join(record_dir, 'pi_output.mp4')}")

        # Display
        if cfg["display"]:
            branches.append("kmssink sync=false")

        # Do nothing if no branches are specified
        if not branches:
            cmd = None
        elif len(branches) == 1:
            cmd = f"{base_cmd} ! {branches[0]}"
        else:
            # tee für mehrere Sinks
            tee_branches = " ".join([f"t. ! queue ! {b}" for b in branches])
            cmd = f"{base_cmd} ! tee name=t {tee_branches}"

        # Start as bash command
        if cmd:
            cmd_list = ["bash", "-c", cmd]
        else:
            cmd_list = []

        super().__init__(name="pi_camera", cmd=cmd_list, log_dir=log_dir, record_dir=record_dir)
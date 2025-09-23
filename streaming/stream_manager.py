import yaml, time, datetime, os
from .camera_pipeline import IRCameraPipeline, PiCameraPipeline

class StreamManager:
    def __init__(self, config_file):
        with open(config_file) as f:
            self.cfg = yaml.safe_load(f)
        self.log_dir = os.path.join(self.cfg["log_dir"], datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.record_dir = os.path.join(self.cfg["record_dir"], datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.laptop_ip = self.cfg["laptop_ip"]
        self.pipelines = []

        if self.cfg["ir_camera"]["stream"] or self.cfg["ir_camera"]["record"] or self.cfg["ir_camera"]["display"]:
            self.pipelines.append(IRCameraPipeline(self.cfg["ir_camera"], self.laptop_ip, self.log_dir, self.record_dir))

        if self.cfg["pi_camera"]["stream"] or self.cfg["pi_camera"]["record"] or self.cfg["pi_camera"]["display"]:
            self.pipelines.append(PiCameraPipeline(self.cfg["pi_camera"], self.laptop_ip, self.log_dir, self.record_dir))

        # ComposePipeline später ergänzen

    def start_all(self):
        for p in self.pipelines:
            if p.cmd:  # skip wenn keine Sinks
                p.start()
        print("[INFO] All pipelines started.")

    def monitor(self):
        try:
            while True:
                for p in self.pipelines:
                    if not p.is_running():
                        print(f"[ERROR] {p.name} stopped unexpectedly")
                        return
                print("[INFO] Pipelines running...")
                time.sleep(5)
        except KeyboardInterrupt:
            print("[INFO] Ctrl+C detected, stopping pipelines...")
            self.stop_all()

    def stop_all(self):
        for p in self.pipelines:
            p.stop()
import yaml, time, datetime, os
from .camera_pipeline import IRCameraPipeline, PiCameraPipeline

class StreamManager:
    def __init__(self, config_file):

        # Load configuration
        with open(config_file) as f:
            self.cfg = yaml.safe_load(f)
        self.log_dir = os.path.join(self.cfg["log_dir"], datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.record_dir = os.path.join(self.cfg["record_dir"], datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.laptop_ip = self.cfg["laptop_ip"]
        self.pipelines = []

        # Create record directory if recording is enabled
        if self.cfg["ir_camera"]["record"] or self.cfg["pi_camera"]["record"]:
            os.makedirs(self.record_dir, exist_ok=True)

        # Initialize pipelines based on config
        if self.cfg["ir_camera"]["stream"] or self.cfg["ir_camera"]["record"] or self.cfg["ir_camera"]["display"]:
            self.pipelines.append(IRCameraPipeline(self.cfg["ir_camera"], self.laptop_ip, self.log_dir, self.record_dir))
        if self.cfg["pi_camera"]["stream"] or self.cfg["pi_camera"]["record"] or self.cfg["pi_camera"]["display"]:
            self.pipelines.append(PiCameraPipeline(self.cfg["pi_camera"], self.laptop_ip, self.log_dir, self.record_dir))

        # ComposePipeline TBD

    def start_all(self):
        ''' Start all configured pipelines'''
        for p in self.pipelines:
            if p.cmd:  # skip wenn keine Sinks
                p.start()
        print("[INFO] All pipelines started.")

    def stop_all(self):
        ''' Stop all active pipelines'''
        for p in self.pipelines:
            if p and p.is_running():
                p.stop()
        print("[INFO] All pipelines stopped.")

    def monitor(self, interval=5):
        '''Monitor all active pipelines'''
        try:
            while True:
                for obj in self.pipelines:
                    if obj and not obj.is_running():
                        print(f"[ERROR] {obj.name} stopped unexpectedly")
                        self.stop_all()
                        return
                print("[INFO] Pipelines running...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("[INFO] Ctrl+C detected, stopping pipelines...")
            self.stop_all()
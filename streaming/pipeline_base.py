import subprocess, os, signal

class PipelineBase:
    def __init__(self, name, cmd, log_dir):
        self.name = name
        self.cmd = cmd
        self.log_dir = log_dir
        self.process = None
        self.log_file = None


    def start(self):
        log_path = os.path.join(self.log_dir, f"{self.name}.log")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = open(log_path, "w")
        self.process = subprocess.Popen(
            self.cmd,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
        print(f"[INFO] Started {self.name} -> log: {log_path}")

    def is_running(self):
        return self.process and (self.process.poll() is None)

    def stop(self):
        if self.process and self.is_running():
            print(f"[INFO] Stopping {self.name}...")
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait()
        if self.log_file:
            self.log_file.close()
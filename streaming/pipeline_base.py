import subprocess, os, signal

class PipelineBase:
    def __init__(self, name, cmd, log_dir, stdin_processes=None):
        self.name = name
        self.cmd = cmd
        self.log_dir = log_dir
        self.process = None
        self.log_file = None
        self.stdin_processes = stdin_processes


    def start(self):
        log_path = os.path.join(self.log_dir, f"{self.name}.log")
        self.log_file = open(log_path, "w")
        print(f"[INFO] Starting {self.name}, command: \n'''\n{self.cmd}\n'''")
        self.process = subprocess.Popen(
            self.cmd,
            shell=True,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            stdin=self.stdin_processes.stdout if self.stdin_processes else None, # Use output of another process as input if provided
            preexec_fn=os.setsid
        )
        print(f"[INFO] Started {self.name} -> log: {log_path}")

    def is_running(self):
        return self.process and (self.process.poll() is None)

    def stop(self):
        if self.process:
            print(f"[INFO] Stopping {self.name}...")
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait()
            print(f"[INFO] {self.name} process terminated.")
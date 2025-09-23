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
        print(f"[INFO] Starting {self.name}, command: \n'''\n{' '.join(self.cmd)}\n'''")
        self.process = subprocess.Popen(
            self.cmd,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            stdin=self.stdin_processes.stdout if self.stdin_processes else None, # Use output of another process as input if provided
            preexec_fn=os.setsid
        )
        print(f"[INFO] Started {self.name} -> log: {log_path}")

    def is_running(self):
        return self.process and (self.process.poll() is None)

    def stop(self):
        if self.process and self.is_running():
            print(f"[INFO] Stopping {self.name}...")
            self.process.terminate()
            self.process.wait()
            print(f"[INFO] {self.name} process terminated.")
        if self.stdin_processes:
            print(f"[INFO] Terminating {self.name} stdin process...")
            self.stdin_processes.terminate()
            self.stdin_processes.wait()
            print(f"[INFO] {self.name} stdin process terminated.")
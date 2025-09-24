import subprocess, os, signal

class PipelineBase:
    def __init__(self, name, cmd, log_dir, stdin_processes=None):
        """
        Base class for managing subprocess pipelines.

        Args:
            name (str): Name of the process (used for logging).
            cmd (str): Command to execute as a subprocess.
            log_dir (str): Directory where log files will be stored.
            stdin_processes (subprocess.Popen, optional): If provided, the stdout
                of this process will be connected to the stdin of the current process.
        """
        self.name = name
        self.cmd = cmd
        self.log_dir = log_dir
        self.process = None
        self.log_file = None
        self.stdin_processes = stdin_processes

    def start(self):
        """Start the subprocess and configure logging."""
        if self.stdin_processes:
            assert self.stdin_processes.stdout is not None, \
                "stdin_processes must provide a stdout to connect to stdin"
        
        # Setup logging
        log_path = os.path.join(self.log_dir, f"{self.name}.log")
        self.log_file = open(log_path, "w")
        print(f"[INFO] Starting {self.name}, command: \n'''\n{self.cmd}\n'''")

        # Start subprocess (in its own process group)
        self.process = subprocess.Popen(
            self.cmd,
            shell=True,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            stdin=self.stdin_processes.stdout if self.stdin_processes else None,
            preexec_fn=os.setsid
        )
        print(f"[INFO] Started {self.name} -> log: {log_path}")

    def is_running(self):
        main_alive = self.process and (self.process.poll() is None)
        stdin_alive = (self.stdin_processes is None) or (self.stdin_processes.poll() is None)
        return main_alive and stdin_alive
    
    def stop(self):
        """Stop the subprocess and its input pipeline (if any)."""
        if self.process and self.process.poll() is None:
            self._stop_process(self.process, self.name)
            self.process = None

        if self.stdin_processes and self.stdin_processes.poll() is None:
            self._stop_process(self.stdin_processes, f"{self.name} stdin_process")
            self.stdin_processes = None

        # Close log file if open
        if self.log_file and not self.log_file.closed:
            self.log_file.close()
            self.log_file = None

    def _stop_process(self, process, name):
        """
        Try to gracefully stop a subprocess by sending signals in escalating order:
        SIGINT -> SIGTERM -> SIGKILL
        """
        print(f"[INFO] Stopping {name}...")
        try:
            # First attempt: SIGINT for graceful shutdown
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
            process.wait(timeout=5)

        except subprocess.TimeoutExpired:
            print(f"[WARN] {name} did not exit, sending SIGTERM...")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print(f"[ERROR] {name} still alive, forcing SIGKILL...")
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()

        print(f"[INFO] {name} process terminated.")
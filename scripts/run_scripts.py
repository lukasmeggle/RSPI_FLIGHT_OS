#!/usr/bin/env python3
import os, sys

# Add the parent directory to Python path so we can import streaming module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streaming.stream_manager import StreamManager

if __name__ == "__main__":
    cfg_file = sys.argv[1] if len(sys.argv) > 1 else "config/default_config.yaml"
    if not os.path.exists(cfg_file):
        print(f"[ERROR] Config file {cfg_file} not found")
        sys.exit(1)

    mgr = StreamManager(cfg_file)
    mgr.start_all()
    mgr.monitor()
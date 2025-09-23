#!/usr/bin/env python3
import os, sys
from streaming.stream_manager import StreamManager

if __name__ == "__main__":
    cfg_file = sys.argv[1] if len(sys.argv) > 1 else "config/default_config.yaml"
    if not os.path.exists(cfg_file):
        print(f"[ERROR] Config file {cfg_file} not found")
        sys.exit(1)

    mgr = StreamManager(cfg_file)
    mgr.start_all()
    mgr.monitor()
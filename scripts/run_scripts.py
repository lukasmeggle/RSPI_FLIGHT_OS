#!/usr/bin/env python3
import os
import sys
import argparse

# Add the parent directory to Python path so we can import streaming module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streaming.stream_manager import StreamManager

def get_config_path(path):
    """
    Expands user (~), resolves relative paths, and checks if the file exists.
    Returns the absolute path if valid, otherwise exits with an error.
    """
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(abs_path):
        print(f"[ERROR] Config file '{abs_path}' not found.")
        sys.exit(1)
    return abs_path

if __name__ == "__main__":
    # Set up argument parser for command-line options
    parser = argparse.ArgumentParser(description="Run the StreamManager with a given config file.")
    parser.add_argument(
        "config",
        nargs="?",
        default="configs/default_config.yaml",
        help="Path to the configuration YAML file (default: configs/default_config.yaml)"
    )
    args = parser.parse_args()

    # Get and validate the config file path
    cfg_file = get_config_path(args.config)

    # Initialize and start the StreamManager
    mgr = StreamManager(cfg_file)
    mgr.start_all()
    mgr.monitor()
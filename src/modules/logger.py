import logging
import json
import os
from datetime import datetime

class TraceLogger:
    def __init__(self, log_file="trace.log"):
        self.log_file = log_file
        # Clear log file on initiation to ensure it only contains the last execution
        with open(self.log_file, "w") as f:
            f.write(f"--- Pipeline Execution Trace: {datetime.now().isoformat()} ---\n")
        
        self.logger = logging.getLogger("PipelineTrace")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_step(self, agent_name, action, details):
        message = f"[{agent_name}] {action}: {json.dumps(details, indent=2) if isinstance(details, (dict, list)) else details}"
        self.logger.info(message)
        print(message) # Also print to console for visibility

trace_log = TraceLogger()

import argparse
import os
import sys
from src.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser(description="Elearning Multi-agent Pipeline Demo")
    parser.add_argument("--learner", type=str, default="learner_1", help="Learner ID (learner_1, learner_2, learner_3)")
    parser.add_argument("--goal", type=str, default="Linear Regression Basics", help="Learning topic or goal")
    
    args = parser.parse_args()

    config = {
        "profiles_path": "data/demo/learner_profiles.json",
        "logs_dir": "data/demo/logs",
        "topic_graph_path": "data/demo/topic_graph.yaml",
        "resources_path": "data/demo/resources.jsonl",
        "qa_rules_path": "config/qa_rules.yaml",
        "oulad_dir": "data/raw/OULAD",
        "model": "llama3"
    }

    print(f"--- Starting Pipeline for {args.learner} (Goal: {args.goal}) ---")
    
    orchestrator = Orchestrator(config)
    result = orchestrator.run(args.learner, args.goal)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("\n--- Summary ---")
        print(f"Learner: {result['learner']}")
        print(f"Next Step: {result['next_step']}")
        print("Pipeline execution complete. Check 'output.json' for full details and 'trace.log' for the execution trace.")

if __name__ == "__main__":
    main()

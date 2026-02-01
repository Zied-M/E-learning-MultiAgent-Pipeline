import json
import os

class LearnerAgent:
    def __init__(self, profiles_path, logs_dir, logger):
        self.profiles_path = profiles_path
        self.logs_dir = logs_dir
        self.logger = logger
        self.personas = self._load_personas()

    def _load_personas(self):
        if os.path.exists(self.profiles_path):
            with open(self.profiles_path, "r") as f:
                return json.load(f)
        return {}

    def get_context(self, learner_id):
        self.logger.log_step("LearnerAgent", "Fetching Context", {"learner_id": learner_id})
        persona = self.personas.get(learner_id, {})
        logs = []
        log_path = os.path.join(self.logs_dir, f"{learner_id}.jsonl")
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                for line in f:
                    logs.append(json.loads(line))
        
        return {
            "persona": persona,
            "logs": logs
        }

    def add_learned_topic(self, learner_id, topic_name):
        self.logger.log_step("LearnerAgent", "Updating Progress", {"learner_id": learner_id, "topic": topic_name})
        if learner_id in self.personas:
            if "strengths" not in self.personas[learner_id]:
                self.personas[learner_id]["strengths"] = []
            if topic_name not in self.personas[learner_id]["strengths"]:
                self.personas[learner_id]["strengths"].append(topic_name)
            
            # Persist to disk
            with open(self.profiles_path, "w") as f:
                json.dump(self.personas, f, indent=4)
            return True
        return False

    def update_last_topic(self, learner_id, topic_name):
        if learner_id in self.personas:
            self.personas[learner_id]["last_topic"] = topic_name
            with open(self.profiles_path, "w") as f:
                json.dump(self.personas, f, indent=4)

    def set_original_goal(self, learner_id, goal):
        if learner_id in self.personas:
            self.personas[learner_id]["original_goal"] = goal
            with open(self.profiles_path, "w") as f:
                json.dump(self.personas, f, indent=4)

    def save_quiz_answers(self, learner_id, quiz):
        if learner_id in self.personas:
            self.personas[learner_id]["current_quiz"] = quiz
            with open(self.profiles_path, "w") as f:
                json.dump(self.personas, f, indent=4)

    def get_quiz_answers(self, learner_id):
        return self.personas.get(learner_id, {}).get("current_quiz", [])

import yaml
import os

class PathPlanningAgent:
    def __init__(self, topic_graph_path, logger, ollama_client=None):
        self.topic_graph_path = topic_graph_path
        self.logger = logger
        self.ollama = ollama_client
        self.graph = self._load_graph()

    def _load_graph(self):
        if os.path.exists(self.topic_graph_path):
            with open(self.topic_graph_path, "r") as f:
                return yaml.safe_load(f)
        return {"topics": []}

    def plan_path(self, profile, goal_topic):
        self.logger.log_step("PathPlanningAgent", "Planning Path", {"goal": goal_topic})
        
        # Fuzzy matching for goal node
        goal_node = None
        goal_topic_lower = goal_topic.lower()
        
        topics = self.graph.get("topics", [])
        
        # 1. Exact or ID match
        goal_node = next((t for t in topics if t["name"].lower() == goal_topic_lower or t["id"].lower() == goal_topic_lower), None)
        
        # 2. Fuzzy/Partial match
        if not goal_node:
            for t in topics:
                t_name = t["name"].lower()
                if t_name in goal_topic_lower or goal_topic_lower in t_name:
                    goal_node = t
                    break
        
        # 3. LLM-based Intent Mapping (NLU fallback)
        if not goal_node and self.ollama:
            self.logger.log_step("PathPlanningAgent", "NLU Fallback", "Mapping conversational input via LLM")
            topic_list = ", ".join([t["name"] for t in topics])
            prompt = f"""
            Given the user request: "{goal_topic}"
            And the following available topics: {topic_list}
            
            Identify the single most relevant topic from the list. 
            Reply ONLY with the topic name. If no topic is remotely relevant, reply "NONE".
            """
            llm_mapped = self.ollama.generate(prompt).strip().strip('"').strip("'")
            self.logger.log_step("PathPlanningAgent", "LLM Mapping Result", llm_mapped)
            
            goal_node = next((t for t in topics if t["name"].lower() == llm_mapped.lower()), None)

        if not goal_node:
            self.logger.log_step("PathPlanningAgent", "Error", f"No topic match found for: {goal_topic}")
            return []

        path = []
        # Breadth-first search for prerequisites (simplified for demo)
        to_visit = [goal_node]
        visited = set()
        
        while to_visit:
            curr = to_visit.pop(0)
            if curr["id"] not in visited:
                path.insert(0, curr)
                visited.add(curr["id"])
                for prereq_id in curr.get("prerequisites", []):
                    prereq_node = next((t for t in topics if t["id"] == prereq_id), None)
                    if prereq_node:
                        to_visit.append(prereq_node)
        
        # Filter out topics the learner already knows
        strengths = [s.lower() for s in profile.get("strengths", [])]
        filtered_path = []
        for node in path:
            # Check if topic name or ID matches a strength
            if node["name"].lower() not in strengths and node["id"].lower() not in strengths:
                filtered_path.append(node)
        
        # If all nodes in the path are known, filtered_path will be empty.
        # This is correct - it means the learner has mastered the requested path.
        
        return filtered_path

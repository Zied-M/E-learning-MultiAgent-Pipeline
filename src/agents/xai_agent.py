class XAIAgent:
    def __init__(self, logger):
        self.logger = logger

    def package_report(self, shared_state):
        self.logger.log_step("XAIAgent", "Packaging XAI Output", "Finalizing report")
        
        xai_output = {
            "learner_profile": shared_state.get("profile"),
            "path_planned": [t["name"] for t in shared_state.get("path", [])],
            "recommendation_reasoning": {
                rec["title"]: {
                    "reason_text": rec.get("reason_text", "Matched your current proficiency and interests."),
                    "score": rec.get("total_score", 0),
                    "features": rec.get("reasons", {})
                } for rec in shared_state.get("recommendations", [])[:1]
            },
            "qa_summary": shared_state.get("qa_report"),
            "counterfactual": self._generate_insight(shared_state.get("profile")),
            "agent_contributions": {
                "ProfilingAgent": "Calibrated learning depth using OULAD distribution mean.",
                "PathplanningAgent": "Optimized sequence to avoid redundant concepts (e.g. skipping strengths).",
                "RecommendationAgent": "Weighted resource selection based on preference for " + shared_state.get("profile", {}).get("preferences", {}).get("resource_type", "Text")
            }
        }
        
        return xai_output

    def _generate_insight(self, profile):
        if not profile: return "Waiting for learner context..."
        level = profile.get("base_level", "Beginner")
        eng = profile.get("engagement_rate", "High")
        if level == "Advanced" and eng == "Low":
            return "Strategy: Providing high-density research-grade materials to re-engage advanced learner."
        if level == "Beginner" and eng == "High":
            return "Strategy: Leveraging high engagement with step-by-step foundational concepts."
        return f"Strategy: Calibration set to {level} level with {eng} engagement weighting."

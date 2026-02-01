class RecommendationAgent:
    def __init__(self, logger):
        self.logger = logger

    def recommend(self, profile, next_step, candidates):
        self.logger.log_step("RecommendationAgent", "Ranking Candidates", {"next_step": next_step["name"]})
        
        ranked_results = []
        for res in candidates:
            # Transparent scoring logic
            score = 0
            reasons = {}
            
            # Difficulty match
            diff_diff = abs(res["difficulty"] - next_step["difficulty"])
            if diff_diff == 0:
                score += 50
                reasons["difficulty_match"] = 50
            else:
                score += max(0, 50 - (diff_diff * 10))
                reasons["difficulty_match"] = max(0, 50 - (diff_diff * 10))
            
            # Weakness alignment
            is_weakness = any(w.lower() in res["topic"].lower() or w.lower() in res["title"].lower() for w in profile.get("weaknesses", []))
            if is_weakness:
                score += 30
                reasons["weakness_alignment"] = 30
            
            # Preference match
            pref_type = profile.get("preferences", {}).get("resource_type", "")
            if pref_type and pref_type.lower() in res.get("source", "").lower():
                score += 20
                reasons["preference_fit"] = 20
            
            # Descriptive Reason string for UI
            reason_text = f"Difficulty match ({res['difficulty']} vs {next_step['difficulty']})"
            if is_weakness: reason_text += f" + Targets your weakness in {res['topic']}"
            if pref_type and pref_type.lower() in res.get("source", "").lower(): reason_text += f" + Matches your preference for {pref_type}"
                
            ranked_results.append({
                "resource_id": res["resource_id"],
                "title": res["title"],
                "total_score": score,
                "reasons": reasons,
                "reason_text": reason_text,
                "text": res["text"] # Pass along for generator
            })
            
        # Sort by total score
        ranked_results.sort(key=lambda x: x["total_score"], reverse=True)
        return ranked_results

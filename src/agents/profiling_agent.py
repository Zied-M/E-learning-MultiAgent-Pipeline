import pandas as pd
import numpy as np
import os

class ProfilingAgent:
    def __init__(self, oulad_dir, logger):
        self.oulad_dir = oulad_dir
        self.logger = logger
        self.calibration_stats = self._calculate_calibration_stats()

    def _calculate_calibration_stats(self):
        # Calibration using OULAD: Calculate average scores and engagement distributions
        score_stats = {}
        try:
            student_assessment_path = os.path.join(self.oulad_dir, "studentAssessment.csv")
            if os.path.exists(student_assessment_path):
                df = pd.read_csv(student_assessment_path)
                # Filter out null scores and convert to numeric
                df['score'] = pd.to_numeric(df['score'], errors='coerce')
                df = df.dropna(subset=['score'])
                
                score_stats = {
                    "mean_score": float(df['score'].mean()),
                    "p25": float(df['score'].quantile(0.25)),
                    "p50": float(df['score'].quantile(0.50)),
                    "p75": float(df['score'].quantile(0.75))
                }
                self.logger.log_step("ProfilingAgent", "OULAD Calibration Success", score_stats)
        except Exception as e:
            self.logger.log_step("ProfilingAgent", "OULAD Calibration Error", str(e))
        
        return score_stats

    def profile(self, context):
        persona = context.get("persona", {})
        logs = context.get("logs", [])
        
        self.logger.log_step("ProfilingAgent", "Generating Profile", {"learner_name": persona.get("name")})
        
        # Calculate engagement from logs
        num_sessions = len(logs)
        avg_score = 0
        quiz_logs = [l for l in logs if l.get("type") == "quiz"]
        if quiz_logs:
            avg_score = sum(l.get("score", 0) for l in quiz_logs) / len(quiz_logs)
            
        # Calibrate level based on stats
        # For simplicity: if avg_score > p75 -> Advanced, etc. (Mocking logic here)
        calibrated_level = persona.get("level", "Unknown")
        if self.calibration_stats:
            if avg_score > self.calibration_stats.get("p75", 75):
                calibrated_status = "High Performer"
            elif avg_score < self.calibration_stats.get("p25", 40):
                calibrated_status = "Struggling"
            else:
                calibrated_status = "Average"
        else:
            calibrated_status = "Not Calibrated"

        profile = {
            "learner_id": persona.get("learner_id"),
            "name": persona.get("name"),
            "base_level": calibrated_level,
            "performance_status": calibrated_status,
            "avg_quiz_score": avg_score,
            "engagement_rate": "High" if num_sessions > 3 else "Low",
            "strengths": persona.get("strengths", []),
            "weaknesses": persona.get("weaknesses", []),
            "preferences": persona.get("preferences", {})
        }
        
        return profile

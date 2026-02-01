import json

class VerifierAgent:
    def __init__(self, config_path, logger):
        self.config_path = config_path
        self.logger = logger

    def verify(self, generated_content, evidence):
        self.logger.log_step("VerifierAgent", "Verifying Content", "Running hard-rule checks")
        
        passed = True
        reasons = []
        
        # Check 1: Citations
        explanation = str(generated_content.get("explanation", "")) + str(generated_content.get("raw_content", ""))
        if evidence["title"].lower() not in explanation.lower() and "source" not in explanation.lower():
            passed = False
            reasons.append("Missing or invalid citation")
            
        # Check 2: Format compliance
        if "explanation" not in generated_content and "raw_content" not in generated_content:
            passed = False
            reasons.append("Invalid output format")

        # Check 3: Quiz existence
        if "quiz" not in generated_content and "quiz" not in str(generated_content):
            passed = False
            reasons.append("Quiz missing")
            
        report = {
            "passed": passed,
            "reasons": reasons
        }
        
        self.logger.log_step("VerifierAgent", "Verification Report", report)
        return report

class JudgeAgent:
    def __init__(self, ollama_client, logger):
        self.client = ollama_client
        self.logger = logger

    def judge(self, verifier_report, generated_content):
        if verifier_report["passed"]:
            self.logger.log_step("JudgeAgent", "Final Decision", "ACCEPT")
            return "ACCEPT", None
            
        reasons = ", ".join(verifier_report["reasons"])
        self.logger.log_step("JudgeAgent", "Analyzing Failures", reasons)
        
        # Call LLM to generate specific revision instructions
        prompt = f"""
        The following generated educational content failed verification.
        Content: {json.dumps(generated_content)}
        Verification Failures: {reasons}
        
        Generate a concise instruction for the AI agent to fix these specific issues. 
        Format: "Instruction: [Your instruction here]"
        """
        feedback = self.client.generate(prompt).replace("Instruction:", "").strip()
        
        self.logger.log_step("JudgeAgent", "Revision Requested", feedback)
        return "REVISE", feedback

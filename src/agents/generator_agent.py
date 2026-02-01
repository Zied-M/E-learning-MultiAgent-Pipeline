import requests
import json

class OllamaClient:
    def __init__(self, model="llama3", base_url="http://localhost:11434/api/generate"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt, system_prompt=None):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            response = requests.post(self.base_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"Error connecting to Ollama: {str(e)}"

class ContentGeneratorAgent:
    def __init__(self, ollama_client, prompt_template_path, logger):
        self.client = ollama_client
        self.prompt_template_path = prompt_template_path
        self.logger = logger

    def generate_content(self, profile, next_step, top_recommendation):
        self.logger.log_step("ContentGeneratorAgent", "Generating Content", {"topic": next_step["name"]})
        
        system_prompt = f"You are an expert tutor. YOU MUST REPLY ONLY WITH A JSON OBJECT. NO CONVERSATIONAL TEXT. Create a personalized explanation for {profile['name']} at {profile['base_level']} level. Topic: {next_step['name']}."
        prompt = f"""
        Explain {next_step['name']} using this evidence: {top_recommendation['text']}
        
        Requirements:
        1. Clear explanation citing [Source: {top_recommendation['title']}].
        2. Practical example.
        3. 5-question Multiple Choice Quiz (MCQ) with 3 options each.
        
        Format MUST be valid JSON. DO NOT TALK OUTSIDE THE JSON.
        JSON Structure: {{"explanation": "...", "example": "...", "quiz": [{{"question": "...", "options": ["...", "..."], "answer": "FULL TEXT OF THE CORRECT OPTION"}}]}}
        """
        
        raw_output = self.client.generate(prompt, system_prompt)
        
        # Hyper-aggressive JSON extractor
        try:
            start = raw_output.find('{')
            end = raw_output.rfind('}') + 1
            if start != -1 and end != 0:
                json_part = raw_output[start:end]
                
                # Try 1: Standard Parse
                try: 
                    content = json.loads(json_part)
                except:
                    # Try 2: Manual Repair for common LLM issues
                    import re
                    # Fix single-quoted keys and values
                    fixed = re.sub(r"\'(\w+)\'\s*:", r'"\1":', json_part)
                    fixed = re.sub(r":\s*\'(.*?)\'", r': "\1"', fixed)
                    # Fix escaped quotes or trailing commas
                    fixed = fixed.replace(",\n}", "\n}").replace(",}", "}")
                    content = json.loads(fixed)

                if content and "quiz" in content:
                    self.logger.log_step("ContentGeneratorAgent", "Extraction Success", "Grounded Quiz Data Saved")
                    return content
        except:
            pass
            
        self.logger.log_step("ContentGeneratorAgent", "Extraction Warning", "Falling back to smart scraping")
        import re
        
        # 1. Try to extract Explanation and Example via regex
        exp_match = re.search(r'"explanation"\s*:\s*"(.*?)"', raw_output, re.DOTALL)
        ex_match = re.search(r'"example"\s*:\s*"(.*?)"', raw_output, re.DOTALL)
        
        explanation = exp_match.group(1) if exp_match else ""
        example = ex_match.group(1) if ex_match else ""
        
        # 2. Cleanup: If regex found nothing, try to find a large block of text that isn't JSON
        if not explanation:
            # Match any large block of text that doesn't look like JSON keys
            explanation = re.sub(r'\{.*?\}', '', raw_output, flags=re.DOTALL).strip()
            explanation = explanation.replace("```json", "").replace("```", "").strip()

        return {
            "explanation": explanation,
            "example": example,
            "raw_content": explanation if len(explanation) > 10 else raw_output,
            "original_output": raw_output
        }

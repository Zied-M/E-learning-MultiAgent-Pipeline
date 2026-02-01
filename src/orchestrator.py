import json
import os
from src.modules.logger import trace_log
from src.modules.rag import RAGModule
from src.agents.learner_agent import LearnerAgent
from src.agents.profiling_agent import ProfilingAgent
from src.agents.path_agent import PathPlanningAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.agents.generator_agent import ContentGeneratorAgent, OllamaClient
from src.agents.qa_agents import VerifierAgent, JudgeAgent
from src.agents.xai_agent import XAIAgent

class Orchestrator:
    def __init__(self, config):
        self.config = config
        self.logger = trace_log
        
        # Modules
        self.rag = RAGModule(config['resources_path'], self.logger)
        self.ollama = OllamaClient(model=config.get('model', 'llama3'))
        
        # Agents
        self.learner_agent = LearnerAgent(config['profiles_path'], config['logs_dir'], self.logger)
        self.profiling_agent = ProfilingAgent(config['oulad_dir'], self.logger)
        self.path_agent = PathPlanningAgent(config['topic_graph_path'], self.logger, self.ollama)
        self.rec_agent = RecommendationAgent(self.logger)
        self.gen_agent = ContentGeneratorAgent(self.ollama, "", self.logger)
        self.verifier = VerifierAgent(config['qa_rules_path'], self.logger)
        self.judge = JudgeAgent(self.ollama, self.logger)
        self.xai_agent = XAIAgent(self.logger)

        self.shared_state = {}

    def run(self, learner_id, input_text):
        self.logger.log_step("Orchestrator", "Processing Input", {"learner_id": learner_id, "input": input_text})
        
        # 1. Fetch Context
        context = self.learner_agent.get_context(learner_id)
        self.shared_state['context'] = context
        profile = self.profiling_agent.profile(context)
        self.shared_state['profile'] = profile

        # 1b. Hybrid Intent Recognition
        goal_keywords = ['learn', 'teach', 'explain', 'tell me', 'what is', 'goal', 'path', 'next topic']
        input_lower = input_text.lower()
        
        # Deterministic override: Keywords
        if any(kw in input_lower for kw in goal_keywords):
            intent = "GOAL"
        else:
            intent_prompt = f"""
            Identify if the user input is a quiz ANSWER or a learning GOAL/TOPIC.
            
            Input: "{input_text}"
            
            Rules:
            - ANSWER: Select options (A,B,C), index (0,1,2), or direct answers to previous questions.
            - GOAL: Asking to learn a topic, setting a goal, or requesting explanation.
            
            Reply ONLY with 'ANSWER' or 'GOAL'. No explanation.
            """
            intent = self.ollama.generate(intent_prompt).strip().upper()

        # Deterministic override: Topic match
        if any(t['name'].lower() in input_lower for t in self.path_agent.graph.get('topics', [])):
             if not any(str(i) in input_text for i in range(1, 6)): # If no question numbers mentioned
                intent = "GOAL"
             
        self.logger.log_step("Orchestrator", "Intent Result", intent)

        feedback_prefix = ""
        actual_quiz = self.learner_agent.get_quiz_answers(learner_id)
        
        # State-aware override: If no quiz was ever sent, it CANNOT be an answer
        is_answer_mode = "ANSWER" in intent and actual_quiz is not None and len(actual_quiz) > 0
        
        if is_answer_mode:
            self.logger.log_step("Orchestrator", "Reviewing Answer", input_text)
            last_topic = context['persona'].get('last_topic', 'Introduction to Machine Learning')
            
            truth_context = "Correct Mapping for this quiz:\n"
            for i, q in enumerate(actual_quiz):
                # DEEP SCRUB for the truth context
                q_txt = str(q.get('question', '')).replace('"', '').replace('\\', '').split('options')[0].strip()
                a_txt = str(q.get('answer', '')).replace('"', '').replace('\\', '').strip()
                truth_context += f"Q{i+1}: {q_txt}\n   - Correct Answer: {a_txt}\n"

            eval_prompt = f"""
            You are a supportive educational tutor.
            Topic: {last_topic}
            Learner Response: "{input_text}"
            
            {truth_context}

            INSTRUCTION:
            1. Briefly acknowledge the learner's effort.
            2. Reveal the correct answers for any questions they missed or were vague about.
            3. Explain WHY the correct answers are right in a helpful way.
            4. End by telling them they are now ready to move to the next topic.
            
            CRITICAL RULES:
            - SPEAK ONLY IN NATURAL LANGUAGE.
            - NO JSON, NO BRACES {{ }}, NO CODE BLOCKS, NO technical delimiters like ":", "[", "]".
            - NO technical metadata.
            """
            eval_result = self.ollama.generate(eval_prompt).strip()
            # Emergency Clean for feedback
            for char in ["{", "}", '["', '"]', '":']: eval_result = eval_result.replace(char, "")
            
            # PIVOT: Always master the topic after providing feedback
            self.learner_agent.add_learned_topic(learner_id, last_topic)
            feedback_prefix = f"🎓 **Lesson Review for {last_topic}**\n\n{eval_result}\n\n✨ Progressing to your next topic..."
            self.logger.log_step("Orchestrator", "Evaluation Result", "PROGRESSING WITH FEEDBACK")
            
            # RE-FETCH Profile to update strengths
            context = self.learner_agent.get_context(learner_id)
            profile = self.profiling_agent.profile(context)
            self.shared_state['profile'] = profile
            
            # Chain to the ORIGINAL goal
            input_text = context['persona'].get('original_goal', last_topic)

        # 2. Path Planning & Execution (Chained)
        self.logger.log_step("Orchestrator", "Execution Flow", {"mode": "Chaining" if is_answer_mode else "Planning", "input": input_text})
        path = self.path_agent.plan_path(profile, input_text)
        self.shared_state['path'] = path
        
        if not path:
            return {
                "status": "Success",
                "learner": profile['name'],
                "next_step": "Goal Achieved",
                "content": {"explanation": f"Congratulations! You have mastered all topics covered in this learning journey for **{profile.get('original_goal', 'your goal')}**."},
                "feedback": feedback_prefix,
                "xai": self.xai_agent.package_report(self.shared_state),
                "trace_file": "trace.log"
            }

        if not is_answer_mode:
            self.learner_agent.set_original_goal(learner_id, input_text)

        next_step = path[0] 
        self.shared_state['next_step'] = next_step
        self.learner_agent.update_last_topic(learner_id, next_step['name'])
        
        # 4. Recommendation
        candidates = self.rag.retrieve(next_step['id'], next_step['name'])
        recommendations = self.rec_agent.recommend(profile, next_step, candidates)
        self.shared_state['recommendations'] = recommendations
        
        if not recommendations:
            return {"error": "No resources found"}

        top_rec = recommendations[0]
        
        # 5. Content Generation + QA Gate
        revision_count = 0
        max_revisions = 1
        generated = {}
        while revision_count <= max_revisions:
            generated = self.gen_agent.generate_content(profile, next_step, top_rec)
            self.shared_state['generated'] = generated
            qa_report = self.verifier.verify(generated, top_rec)
            self.shared_state['qa_report'] = qa_report
            decision, _ = self.judge.judge(qa_report, generated)
            if decision == "ACCEPT":
                break
            revision_count += 1
            self.logger.log_step("Orchestrator", "Revision Attempt", revision_count)
        
        # PERSIST the quiz for the next turn
        quiz_to_save = generated.get("quiz")
        if not quiz_to_save:
            # Multi-layered hunt: Use original_output if available (un-scrubbed)
            hunt_target = generated.get("original_output") or generated.get("raw_content", "")
            extracted = self._hunt_for_quiz(hunt_target)
            if extracted:
                quiz_to_save = extracted
                generated["quiz"] = extracted # INJECT back so UI can see it
                self.logger.log_step("Orchestrator", "Quiz Recovery", "Successfully recovered quiz metadata and injected into response")

        if quiz_to_save:
            self.learner_agent.save_quiz_answers(learner_id, quiz_to_save)
        else:
            self.logger.log_step("Orchestrator", "Persistence Failure", "No quiz metadata found to ground future evaluation")

        # 6. XAI Report
        xai_report = self.xai_agent.package_report(self.shared_state)
        
        # 7. Final Output
        output = {
            "status": "Success",
            "learner": profile['name'],
            "next_step": next_step['name'],
            "content": generated,
            "feedback": feedback_prefix, 
            "xai": xai_report,
            "trace_file": "trace.log"
        }
        
        with open("output.json", "w") as f:
            json.dump(output, f, indent=4)
            
        return output

    def _hunt_for_quiz(self, text):
        """High-fidelity Quiz Hunter with Multi-Strategy Option Extraction."""
        import re
        quiz = []
        
        def clean_text(t):
            if not t: return ""
            # Strip common JSON debris and artifacts
            debris = ['":', '",', '" :', '",\n', '\\"', '"}', '"{', '{', '}', '[', ']', '\"']
            res = t.strip()
            for d in debris: res = res.replace(d, "")
            return res.strip().replace("\n", " ").strip()

        # Strategy A: Logic Block Splitting (Question -> Options -> Answer)
        text_clean = text.replace("**", "") 
        blocks = re.split(r"(?i)(?:question|q\d+)\s*\d*\s*[:\-]\s*", text_clean)
        
        for block in blocks[1:]:
            if not block.strip(): continue
            
            # Find the Answer marker
            sub_parts = re.split(r"(?i)(?:answer|correct|key)\s*[:\-]\s*", block)
            if len(sub_parts) >= 2:
                q_and_opts = sub_parts[0]
                a_raw = sub_parts[1].split("\n")[0]
                
                # OPTION HUNTER STRATEGY 1: Letter/Number lists (e.g. A) Option)
                options = re.findall(r"(?m)^\s*(?:[A-D]|[1-4])[\.\)]\s*(.*?)$", q_and_opts)
                
                # OPTION HUNTER STRATEGY 2: JSON Bracket lists (e.g. ["Opt1", "Opt2"])
                if not options:
                    json_list_match = re.search(r'\[(.*?)\]', q_and_opts, re.DOTALL)
                    if json_list_match:
                        # Split by comma and clean individual quotes
                        options = [o.strip(' "') for o in json_list_match.group(1).split(',')]

                # Final cleaning
                q_scrubbed = re.split(r"(?i)(?:options|choices|\n\s*[A-D1-4][\.\)]|\[)", q_and_opts)[0]
                
                quiz.append({
                    "question": clean_text(q_scrubbed),
                    "options": [clean_text(o) for o in options if len(o) > 1] if options else ["Option A", "Option B", "Option C"],
                    "answer": clean_text(a_raw)
                })
        
        # Strategy B: JSON Key Match (Fallback)
        if not quiz:
            q_matches = re.findall(r"(?i)\"question\"\s*:\s*\"(.*?)\"", text)
            a_matches = re.findall(r"(?i)\"answer\"\s*:\s*\"(.*?)\"", text)
            for q, a in zip(q_matches, a_matches):
                quiz.append({
                    "question": clean_text(q),
                    "options": ["Option A", "Option B", "Option C"],
                    "answer": clean_text(a)
                })
                
        return quiz[:5] if len(quiz) >= 1 else None

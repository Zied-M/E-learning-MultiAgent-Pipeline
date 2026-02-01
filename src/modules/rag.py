import json
import os

class RAGModule:
    def __init__(self, resources_path, logger):
        self.resources_path = resources_path
        self.logger = logger
        self.corpus = self._load_corpus()

    def _load_corpus(self):
        corpus = []
        if os.path.exists(self.resources_path):
            with open(self.resources_path, "r") as f:
                for line in f:
                    if line.strip():
                        corpus.append(json.loads(line))
        return corpus

    def retrieve(self, topic_id, topic_name, k=2):
        self.logger.log_step("RAG", "Retrieving", {"topic_id": topic_id, "topic_name": topic_name, "k": k})
        results = []
        
        # Normalize search terms
        search_terms = {topic_id.lower(), topic_name.lower()}
        if "machine learning" in topic_name.lower():
            search_terms.add("ml")
            search_terms.add("machine learning")
        
        for res in self.corpus:
            res_topic = res['topic'].lower()
            res_title = res['title'].lower()
            
            match = False
            for term in search_terms:
                if term in res_topic or term in res_title or res_topic in term or res_title in term:
                    match = True
                    break
            
            if match:
                results.append(res)
        
        self.logger.log_step("RAG", "Results Found", {"count": len(results), "resource_ids": [r['resource_id'] for r in results]})
        
        # Add mock similarity scores
        for res in results:
            res['similarity_score'] = 0.95
            
        return results[:k]

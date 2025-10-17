# iroko/evals/context.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from uuid import UUID
import logging

from iroko.evals.schemas import Answer

logger = logging.getLogger('iroko-cris')

@dataclass
class EvaluationContext:
    node_id: str
    node_data: Dict[str, Any]
    methodology_id: str
    user_id: UUID
    answers: Dict[str, Answer] = field(default_factory=dict)
    category_results: Dict[str, Answer] = field(default_factory=dict)
    section_results: Dict[str, Answer] = field(default_factory=dict)
    intermediate_cache: Dict[str, Answer] = field(default_factory=dict)
    
    def get_answer(self, question_id: str) -> Answer:
        """Get answer for a question, checking cache first"""
        return self.answers.get(question_id)
    
    def set_answer(self, question_id: str, value: Answer):
        """Set answer for a question"""
        self.answers[question_id] = value
        logger.debug(f"Set answer for {question_id}: {value}")
    
    def get_cached_value(self, key: str) -> Answer:
        """Get value from intermediate cache"""
        return self.intermediate_cache.get(key)
    
    def set_cached_value(self, key: str, value: Answer):
        """Set value in intermediate cache"""
        self.intermediate_cache[key] = value
    
    def has_all_answers(self, question_ids: list) -> bool:
        """Check if all required questions have answers"""
        return all(qid in self.answers and self.answers[qid] is not None for qid in question_ids)
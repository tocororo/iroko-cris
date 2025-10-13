from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from uuid import UUID
from datetime import datetime

from iroko.auth.schemas import UserResponse

class QuestionType(str, Enum):
    BOOLEAN = "boolean"
    NUMBER = "number"
    SELECT = "select"

class Answer(BaseModel):
    result: Optional[Union[bool, float, str]] = None
    recommendation: Optional[str] = None
    user_id: Optional[UUID] = None

class Question(BaseModel):
    id: str
    type: QuestionType
    desc: str
    min: Optional[float] = None
    max: Optional[float] = None
    selectOptions: Optional[List[Dict[str, str]]] = None
    answer: Optional[Answer] = None
    
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Question):
            return self.id == other.id
        return False
    
class Category(BaseModel):
    title: str
    id: str
    description: Optional[str] = None
    questions: List[str] = []
    answer: Optional[Answer] = None

class Section(BaseModel):
    title: str
    id: str
    description: Optional[str] = None
    categories: List['Category'] = []
    answer: Optional[Answer] = None

class Methodology(BaseModel):
    id: str
    name: str
    version: str
    description: str
    entity: str  # Node type (Source, Organization, Person, etc.)
    sections: List[Section]
    answer: Optional[Answer] = None

    class Config:
        from_attributes = True

# class QuestionResult(BaseModel):
#     id: str
#     result: Optional[Union[bool, float, str]] = None
#     recommendation: Optional[str] = None

# class CategoryResult(Category):
#     questions: List[QuestionResult] = []
#     result: Optional[Union[bool, float, str]] = None
#     recommendation: Optional[str] = None

# class SectionResult(Section):
#     categories: List[CategoryResult] = []

class EvaluationResult(BaseModel):
    methodology: Methodology
    # sections: List[SectionResult]
    node_id: str
    timestamp: datetime
    user_id: Optional[UUID] = None
    is_complete: bool = False
    is_finalized: bool = False
    question_data: Dict[str, Question] = {}


    # final_score: Optional[float] = None
    # overall_recommendation: Optional[str] = None
    
    class Config:
        from_attributes = True


class StoredEvaluation(BaseModel):
    id: UUID
    node_id: str
    user_id: UUID
    user: Optional[UserResponse] = None
    methodology_id: str
    timestamp: datetime
    evaluation_data: EvaluationResult   # JSON representation of EvaluationResult
    is_complete: bool
    
    class Config:
        from_attributes = True

Section.model_rebuild()
Category.model_rebuild()
Methodology.model_rebuild()

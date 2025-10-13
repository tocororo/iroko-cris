# iroko/evals/service.py
import yaml
import os
from typing import Dict, List, Optional
from pathlib import Path
from neo4j import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as SQLAsyncSession
from uuid import UUID

from iroko.auth.models import User

from .schemas import *
from .models import EvaluationRecord
from .rules_registry import rules_registry
from .evaluation_engine import EvaluationEngine
from .context import EvaluationContext
import logging

logger = logging.getLogger('iroko-cris')

class EvaluationService:
    def __init__(self, methodologies_path: str = "methodologies"):
        self.methodologies_path = Path(methodologies_path)
        self._methodologies: Dict[str, Methodology] = {}
        self._questions: Dict[str, Question] = {}
        self.engine = EvaluationEngine(rules_registry)
        
    async def load_methodologies(self):
        """Load all methodology and question YAML files"""
        try:
            # Load questions
            questions_file = self.methodologies_path / "questions.yaml"
            if questions_file.exists():
                with open(questions_file, 'r') as f:
                    questions_data = yaml.safe_load(f)
                    for q_data in questions_data:
                        question = Question(**q_data)
                        self._questions[question.id] = question
            
            # Load methodologies
            for methodology_file in self.methodologies_path.glob("methodology-*.yaml"):
                with open(methodology_file, 'r') as f:
                    methodology_data = yaml.safe_load(f)
                    methodology = Methodology(**methodology_data)
                    self._methodologies[methodology.id] = methodology
            
            logger.info(f"Loaded {len(self._methodologies)} methodologies and {len(self._questions)} questions")
            
        except Exception as e:
            logger.error(f"Error loading methodologies: {e}")
            raise
    
    def __helper_fill_questions(self, methodology_data):
        if 'sections' in methodology_data:
            for section in methodology_data.get('sections'):
                if 'categories' in section:
                    for category in section.get('categories'):
                        if 'questions' in category:
                            for question in category.get('questions'):
                                question = self._questions[question]

    async def create_evaluation_context(self, methodology_id: str, node_id: str, 
                                     user_id: UUID, neo4j_session: AsyncSession) -> EvaluationContext:
        """Create evaluation context with node data and load methodology-specific rules"""
        # Load methodology-specific rules
        await rules_registry.load_methodology_rules(methodology_id)
        
        node_data = await self._get_node_data(neo4j_session, node_id)
        return EvaluationContext(
            node_id=node_id,
            node_data=node_data,
            methodology_id=methodology_id,
            user_id=user_id
        )
    
    
    async def create_evaluation_result(self, methodology_id: str, node_id: str, 
                          neo4j_session: AsyncSession, user_id: UUID) -> EvaluationResult:
        """Evaluate a node using the specified methodology"""
        methodology = self._methodologies.get(methodology_id)
        if not methodology:
            raise ValueError(f"Methodology {methodology_id} not found")
        
        # Create evaluation context
        context = await self.create_evaluation_context(methodology_id, node_id, user_id, neo4j_session)
        
        # Build evaluation result structure
        result = EvaluationResult(
            methodology=methodology,
            node_id=node_id,
            timestamp=datetime.now(),
            user_id=user_id,
            is_complete=True
        )
        # Step 1: Evaluate all questions
        await self._evaluate_questions(context, neo4j_session, result)

        # Step 2: Evaluate categories
        await self._evaluate_categories(context, result)
        
        # Step 3: Evaluate sections  
        await self._evaluate_sections(context, result)
        
        # Step 4: Evaluate methodology
        await self._evaluate_methodology(context, result)
        
        return result
    
    async def complete_evaluation_result(self, neo4j_session: AsyncSession, result: EvaluationResult, user_id: UUID):
        context = await self.create_evaluation_context(
                methodology_id=result.methodology.id, node_id= result.node_id, user_id= user_id, neo4j_session=neo4j_session)
        context.answers = result.question_data
        logger.debug('-==-=-=-=-=-=-==-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=')
        logger.debug('-==-=-=-=-=-=-==-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=')
        logger.debug(context)
        logger.debug('-==-=-=-=-=-=-==-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=')
        logger.debug('-==-=-=-=-=-=-==-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=')
        # Step 2: Evaluate categories
        await self._evaluate_categories(context, result)
        
        # Step 3: Evaluate sections  
        await self._evaluate_sections(context, result)
        
        # Step 4: Evaluate methodology
        await self._evaluate_methodology(context, result)
        
        return result
    
    
    async def _evaluate_questions(self, context: EvaluationContext,
                                neo4j_session: AsyncSession, result: EvaluationResult):
        """Evaluate all questions in the methodology"""
        result.question_data = {}
        
        for section in result.methodology.sections:
            

            # section_result = SectionResult(**section.model_dump())
            
            for category in section.categories:
                # category_result = CategoryResult(**category.model_dump())
                
                # Evaluate questions in this category
                for question_id in category.questions:
                    question = self._questions.get(question_id)

                    logger.debug(question)
                    if not question:
                        logger.warning(f"Question {question_id} not found")
                        continue
                    
                    # question_result = QuestionResult(id=question_id)
                    
                    # Try to evaluate automatically
                    answer = await self.engine.evaluate_question(question_id, context, neo4j_session)
                    question_with_answer = Question(
                        id=question.id,
                        type=question.type,
                        desc=question.desc,
                        min=question.min,
                        max=question.max,
                        selectOptions=question.selectOptions,
                        answer=answer
                    )
                    result.question_data[question_id] = question_with_answer

                    # If couldn't answer automatically, mark as incomplete
                    if answer is None:
                        result.is_complete = False
                    
                    # category_result.questions.append(question_result)
                    context.set_answer(question_id, answer)
                
                # section_result.categories.append(category_result)
            
            # result.sections.append(section_result)
    
    async def _evaluate_categories(self, context: EvaluationContext, result: EvaluationResult):
        """Evaluate all categories in the methodology"""
        for section in result.methodology.sections:
            for category in section.categories:
                # Apply category rules if available
                answer = await self.engine.evaluate_category(
                    category.id, context, category.model_dump()
                )
                # qs = []
                # for q in category.questions:
                #     qs.append(self._questions.get(q))
                # category.questions = qs
                if answer:
                    category.answer = answer
    
    async def _evaluate_sections(self, context: EvaluationContext,
                               result: EvaluationResult):
        """Evaluate all sections in the methodology"""
        for section in result.methodology.sections:
            # Apply section rules if available
            answer = await self.engine.evaluate_section(
                section.id, context, section.model_dump()
            )
            if answer:
                section.result = answer
    
    async def _evaluate_methodology(self, context: EvaluationContext, result: EvaluationResult):
        """Evaluate the complete methodology"""
        answer = await self.engine.evaluate_methodology(
            result.methodology.id, context, result.methodology.model_dump()
        )
        
        if answer:
            result.methodology.answer = answer            
            # Add methodology-level recommendations
            # if answer.get('recommendations'):
            #     result.overall_recommendation += ". " + "; ".join(answer['recommendations'])
    
    async def _get_node_data(self, session: AsyncSession, node_id: str, entity_type: str = None) -> Dict[str, Any]:
        """Get node data from Neo4j"""
        if not entity_type:
            # Try to determine entity type by querying
            query = """
            MATCH (n {id: $node_id}) 
            RETURN labels(n) as labels, n as data
            """
        else:
            query = f"MATCH (n:{entity_type} {{id: $node_id}}) RETURN n as data"
        
        result = await session.run(query, node_id=node_id)
        record = await result.single()
        
        if not record:
            raise ValueError(f"Node {node_id} not found")
        
        node_data = dict(record["data"])
        
        # Convert neo4j types to Python types
        for key, value in node_data.items():
            if hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
                node_data[key] = list(value)
        
        return node_data
    
    async def store_evaluation(self, db_session: SQLAsyncSession,
                             evaluation: EvaluationResult, user_id: UUID) -> EvaluationRecord:
        """Store evaluation result in database"""
        record = EvaluationRecord(
            node_id=evaluation.node_id,
            user_id=user_id,
            methodology_id=evaluation.methodology.id,
            evaluation_data=evaluation.model_dump(mode='json'),
            is_complete=evaluation.is_complete,
            entity_type=evaluation.methodology.entity
        )
        
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)
        
        return StoredEvaluation.model_validate(record)

    async def get_evaluation_history(self, db_session: SQLAsyncSession,
                                    node_id: str, methodology_id: Optional[str] = None) -> List[StoredEvaluation]:
        """Get evaluation history for a node"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        query = (select(EvaluationRecord, User)
        .join(User, EvaluationRecord.user_id == User.id) 
        .filter(EvaluationRecord.node_id == node_id))
        
        if methodology_id:
            query = query.filter(EvaluationRecord.methodology_id == methodology_id)
        
        query = query.order_by(EvaluationRecord.timestamp.desc())
        
        result = await db_session.execute(query)
        records = result.fetchall() 
        
        # Convert to list of StoredEvaluation
        stored_evals = []
        for e,u in records:
            user_data = {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "created_at": u.created_at,
                "updated_at": u.updated_at,
                # "roles": u.roles
                # Map other user fields as needed
            }
            record_dict = {
                "id": e.id,
                "node_id": e.node_id,
                "user_id": e.user_id, # Assuming your StoredEvaluation needs this
                "methodology_id": e.methodology_id,
                "timestamp": e.timestamp,
                "evaluation_data": e.evaluation_data,
                "is_complete": e.is_complete,
                "user": user_data # Include the manually constructed user dict
            }
            logger.debug(record_dict)
            logger.debug('------------------------')
            stored_evals.append(StoredEvaluation.model_validate(record_dict))
        
        return stored_evals

# Update the global instance
eval_service = EvaluationService()
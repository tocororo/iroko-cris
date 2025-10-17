# iroko/evals/evaluation_engine.py
from typing import Dict, Any, List, Optional
from neo4j import AsyncSession
import logging

from iroko.evals.schemas import Answer
from .rules_registry import RulesRegistry
from .context import EvaluationContext

logger = logging.getLogger('iroko-cris')

class EvaluationEngine:
    def __init__(self, rules_registry: RulesRegistry):
        self.rules = rules_registry
    
    async def evaluate_question(self, question_id: str, context: EvaluationContext, 
                              neo4j_session: AsyncSession) -> Answer:
        """Evaluate a single question using registered rules"""
        if question_id in self.rules.question_rules:
            try:
                rule_def = self.rules.question_rules[question_id]
                # Check cache first
                cache_key = f"question_{question_id}"
                cached_result = context.get_cached_value(cache_key)
                if cached_result is not None and rule_def.cacheable:
                    logger.debug(f"Using cached result for {question_id}")
                    return cached_result
                
                # Check dependencies
                if not context.has_all_answers(rule_def.dependencies):
                    missing_deps = [dep for dep in rule_def.dependencies if dep not in context.answers]
                    logger.warning(f"Missing dependencies for {question_id}: {missing_deps}")
                    return None
                
                # Execute rule
                result = await rule_def.func(context, neo4j_session)
                
                # Cache result
                if rule_def.cacheable:
                    context.set_cached_value(cache_key, result)
                
                return result
                
            except Exception as e:
                logger.error(f"Error evaluating question {question_id}: {e}")
                return None
        
        logger.warning(f"No rule found for question: {question_id}")
        return None
    
    async def evaluate_category(self, category_id: str, context: EvaluationContext,
                              neo4j_session: AsyncSession) -> Answer:
        """Evaluate a category using registered rules"""
        if category_id in self.rules.category_rules:
            try:
                rule_def = self.rules.category_rules[category_id]
                
                # Check if we have all required answers
                if not context.has_all_answers(rule_def.dependencies):
                    logger.warning(f"Missing answers for category {category_id}")
                    return None
                
                # Execute category rule
                result = await rule_def.func(context, neo4j_session)
                context.category_results[category_id] = result
                return result
                
            except Exception as e:
                logger.error(f"Error evaluating category {category_id}: {e}")
                return None
        
        logger.warning(f"No rule found for category: {category_id}")
        return None
    
    async def evaluate_section(self, section_id: str, context: EvaluationContext,
                             neo4j_session: AsyncSession)  -> Answer:
        """Evaluate a section using registered rules"""
        if section_id in self.rules.section_rules:
            try:
                rule_def = self.rules.section_rules[section_id]
                
                # Check if we have all required category results
                missing_categories = [cat for cat in rule_def.dependencies if cat not in context.category_results]
                if missing_categories:
                    logger.warning(f"Missing category results for section {section_id}: {missing_categories}")
                    return None
                
                # Execute section rule
                result = await rule_def.func(context, neo4j_session)
                context.section_results[section_id] = result
                return result
                
            except Exception as e:
                logger.error(f"Error evaluating section {section_id}: {e}")
                return None
        
        logger.warning(f"No rule found for section: {section_id}")
        return None
    
    async def evaluate_methodology(self, methodology_id: str, context: EvaluationContext,
                                 neo4j_session: AsyncSession) -> Answer:
        """Evaluate methodology using registered rules"""
        if methodology_id in self.rules.methodology_rules:
            try:
                rule_def = self.rules.methodology_rules[methodology_id]
                
                # Check if we have all required section results
                missing_sections = [sec for sec in rule_def.dependencies if sec not in context.section_results]
                if missing_sections:
                    logger.warning(f"Missing section results for methodology {methodology_id}: {missing_sections}")
                    return None
                
                # Execute methodology rule
                return await rule_def.func(context, neo4j_session)
                
            except Exception as e:
                logger.error(f"Error evaluating methodology {methodology_id}: {e}")
                return None
        
        logger.warning(f"No rule found for methodology: {methodology_id}")
        return None
# iroko/evals/rules_registry.py
from typing import Dict, Callable, Any, List
from dataclasses import dataclass
from neo4j import AsyncSession
import logging
import importlib
import pkgutil
from pathlib import Path

logger = logging.getLogger('iroko-cris')

@dataclass
class RuleDefinition:
    func: Callable
    dependencies: List[str]
    cacheable: bool = True

class RulesRegistry:
    def __init__(self):
        self.question_rules: Dict[str, RuleDefinition] = {}
        self.category_rules: Dict[str, RuleDefinition] = {}
        self.section_rules: Dict[str, RuleDefinition] = {}
        self.methodology_rules: Dict[str, RuleDefinition] = {}
        self._loaded_methodologies: set = set()
    
    def register_question_rule(self, question_id: str, dependencies: List[str] = None):
        def decorator(func):
            self.question_rules[question_id] = RuleDefinition(
                func=func, 
                dependencies=dependencies or []
            )
            logger.debug(f"Registered question rule: {question_id}")
            return func
        return decorator
    
    def register_category_rule(self, category_id: str, dependencies: List[str] = None):
        def decorator(func):
            self.category_rules[category_id] = RuleDefinition(
                func=func, 
                dependencies=dependencies or []
            )
            logger.debug(f"Registered category rule: {category_id}")
            return func
        return decorator
    
    def register_section_rule(self, section_id: str, dependencies: List[str] = None):
        def decorator(func):
            self.section_rules[section_id] = RuleDefinition(
                func=func, 
                dependencies=dependencies or []
            )
            logger.debug(f"Registered section rule: {section_id}")
            return func
        return decorator
    
    def register_methodology_rule(self, methodology_id: str, dependencies: List[str] = None):
        def decorator(func):
            self.methodology_rules[methodology_id] = RuleDefinition(
                func=func, 
                dependencies=dependencies or []
            )
            logger.debug(f"Registered methodology rule: {methodology_id}")
            return func
        return decorator
    
    async def load_methodology_rules(self, methodology_id: str):
        """Dynamically load rules for a specific methodology"""
        if methodology_id in self._loaded_methodologies:
            return
        
        try:
            module_name = f"iroko.evals.rules.{methodology_id}"
            importlib.import_module(module_name)
            self._loaded_methodologies.add(methodology_id)
            logger.info(f"Loaded rules for methodology: {methodology_id}")
        except ImportError as e:
            logger.warning(f"No specific rules found for methodology {methodology_id}: {e}")
        except Exception as e:
            logger.error(f"Error loading rules for methodology {methodology_id}: {e}")

# Global rules registry instance
rules_registry = RulesRegistry()
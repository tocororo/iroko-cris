# iroko/evals/rules_registry.py

import logging
import importlib
import traceback
from typing import Dict, Callable, List
from dataclasses import dataclass

logger = logging.getLogger('iroko-cris.evals')

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
        self._loaded_modules: set = set()  # Track loaded modules by their full path
    
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
    
    async def load_rules_module(self, module_path: str):
        """Dynamically load rules from a specified module path"""
        if module_path in self._loaded_modules:
            logger.debug(f"Rules module already loaded: {module_path}")
            return
        
        try:
            logger.info(f"Loading rules module: {module_path}")
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Force registration by accessing the module (decorators run on import)
            logger.info(f"Successfully loaded rules module: {module_path}")
            
            self._loaded_modules.add(module_path)
            
        except ImportError as e:
            logger.error(f"Failed to import rules module {module_path}: {e}")
            logger.error(f"Import error details: {traceback.format_exc()}")
            raise
        except Exception as e:
            logger.error(f"Error loading rules module {module_path}: {e}")
            logger.error(f"Error details: {traceback.format_exc()}")
            raise
    
    async def load_methodology_rules(self, methodology_id: str, rules_module: str = None):
        """Load rules for a specific methodology"""
        if rules_module:
            # Use the specified rules module
            await self.load_rules_module(rules_module)
        else:
            # Fallback to default naming convention
            default_module = f"iroko.evals.rules.{methodology_id}"
            logger.warning(f"No rules module specified for {methodology_id}, trying default: {default_module}")
            try:
                await self.load_rules_module(default_module)
            except ImportError:
                logger.warning(f"No rules found for methodology {methodology_id} (tried: {default_module})")

# Global rules registry instance
rules_registry = RulesRegistry()
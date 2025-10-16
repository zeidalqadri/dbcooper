
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class GeneratedMigration:
    """Result of AI migration generation"""
    sql: str
    rollback_sql: Optional[str]
    confidence: float  # 0.0 to 1.0
    warnings: List[str]
    suggestions: List[str]
    description: str
    reasoning: Optional[str] = None


class AIProvider(ABC):
    """Base class for AI providers (OpenAI, Claude, etc.)"""

    @abstractmethod
    def generate_migration(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        file_type: str = "sql"
    ) -> GeneratedMigration:
        """
        Generate a migration from natural language prompt.

        Args:
            prompt: Natural language description of the migration
            context: Additional context (current schema, tables, etc.)
            file_type: 'sql' or 'py'

        Returns:
            GeneratedMigration with SQL/Python code and metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is properly configured and available"""
        pass

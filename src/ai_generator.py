
import os
from typing import Optional, Dict, Any, List
from sqlalchemy import inspect, text

from .database import get_engine
from .ai_providers import AIProvider, GeneratedMigration, OpenAIProvider, ClaudeProvider


class AICodeGenerator:
    """
    Main AI code generator that orchestrates different AI providers.

    Supports multiple providers with automatic fallback:
    - OpenAI GPT-4 (primary)
    - Anthropic Claude (fallback)
    - Local models (future)
    """

    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize AI generator.

        Args:
            provider_name: Specific provider to use ('openai', 'claude')
                          If None, will try providers in order
        """
        self.provider_name = provider_name or os.getenv("AI_PROVIDER", "auto")
        self.providers = self._initialize_providers()

    def _initialize_providers(self) -> List[AIProvider]:
        """Initialize available AI providers"""
        providers = []

        if self.provider_name in ("auto", "openai"):
            openai = OpenAIProvider()
            if openai.is_available():
                providers.append(openai)

        if self.provider_name in ("auto", "claude"):
            claude = ClaudeProvider()
            if claude.is_available():
                providers.append(claude)

        return providers

    def is_available(self) -> bool:
        """Check if any AI provider is available"""
        return len(self.providers) > 0

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        names = []
        if any(isinstance(p, OpenAIProvider) for p in self.providers):
            names.append("OpenAI GPT-4")
        if any(isinstance(p, ClaudeProvider) for p in self.providers):
            names.append("Anthropic Claude")
        return names

    def _get_database_context(self) -> Dict[str, Any]:
        """
        Get current database schema as context for AI.

        Returns schema information including:
        - List of tables
        - Column information
        - Constraints
        """
        try:
            engine = get_engine()
            inspector = inspect(engine)

            # Get all table names
            tables = inspector.get_table_names()

            # Get schema info for each table
            schema_info = {}
            for table_name in tables:
                columns = inspector.get_columns(table_name)
                indexes = inspector.get_indexes(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)

                schema_info[table_name] = {
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                            "default": col.get("default")
                        }
                        for col in columns
                    ],
                    "indexes": [idx["name"] for idx in indexes],
                    "foreign_keys": [
                        {
                            "constrained_columns": fk["constrained_columns"],
                            "referred_table": fk["referred_table"],
                            "referred_columns": fk["referred_columns"]
                        }
                        for fk in foreign_keys
                    ]
                }

            return {
                "tables": tables,
                "schema": schema_info
            }

        except Exception as e:
            print(f"Warning: Could not fetch database context: {e}")
            return {"tables": [], "schema": {}}

    def generate_migration(
        self,
        prompt: str,
        file_type: str = "sql",
        include_context: bool = True
    ) -> GeneratedMigration:
        """
        Generate a migration from natural language prompt.

        Args:
            prompt: Natural language description (e.g., "Add email to users")
            file_type: 'sql' or 'py'
            include_context: Whether to include current database schema

        Returns:
            GeneratedMigration with SQL code and metadata

        Raises:
            ValueError: If no AI providers available
        """
        if not self.is_available():
            available = self.get_available_providers()
            if available:
                provider_str = ", ".join(available)
            else:
                provider_str = "None"

            return GeneratedMigration(
                sql="-- AI generation not available\n-- No API keys configured",
                rollback_sql=None,
                confidence=0.0,
                warnings=[
                    "No AI providers configured",
                    "Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable"
                ],
                suggestions=[
                    "Configure OpenAI: export OPENAI_API_KEY=your_key",
                    "Or configure Claude: export ANTHROPIC_API_KEY=your_key",
                    "Or write migration manually"
                ],
                description=f"Failed: {prompt}"
            )

        # Get database context if requested
        context = self._get_database_context() if include_context else None

        # Try providers in order until one succeeds
        last_error = None
        for provider in self.providers:
            try:
                result = provider.generate_migration(prompt, context, file_type)

                # Check if generation was successful
                if result.confidence > 0.0:
                    return result

                last_error = result.warnings[0] if result.warnings else "Unknown error"

            except Exception as e:
                last_error = str(e)
                continue

        # All providers failed
        return GeneratedMigration(
            sql=f"-- All AI providers failed\n-- Last error: {last_error}\n-- Please write migration manually",
            rollback_sql=None,
            confidence=0.0,
            warnings=["All AI providers failed", f"Last error: {last_error}"],
            suggestions=["Check API key configuration", "Check internet connection", "Write migration manually"],
            description=f"Failed: {prompt}"
        )


# Global instance (lazy-initialized)
_generator: Optional[AICodeGenerator] = None


def get_ai_generator() -> AICodeGenerator:
    """Get or create the global AI generator instance"""
    global _generator
    if _generator is None:
        _generator = AICodeGenerator()
    return _generator


def generate_migration_with_ai(
    prompt: str,
    file_type: str = "sql",
    include_context: bool = True
) -> GeneratedMigration:
    """
    Convenience function to generate migration with AI.

    Args:
        prompt: Natural language description
        file_type: 'sql' or 'py'
        include_context: Include database schema context

    Returns:
        GeneratedMigration with SQL and metadata
    """
    generator = get_ai_generator()
    return generator.generate_migration(prompt, file_type, include_context)

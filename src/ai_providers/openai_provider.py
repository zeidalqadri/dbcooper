import json
import os
from typing import Any, Dict, Optional

from openai import OpenAI

from .base import AIProvider, GeneratedMigration


class OpenAIProvider(AIProvider):
    """OpenAI GPT-4 provider for migration generation"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def is_available(self) -> bool:
        """Check if OpenAI is configured"""
        return self.client is not None

    def _build_system_prompt(self) -> str:
        """Build the system prompt for SQL generation"""
        return """You are an expert database migration specialist. Your task is to generate safe, idempotent PostgreSQL migration scripts.

CRITICAL RULES:
1. ALWAYS use IF NOT EXISTS / IF EXISTS patterns for idempotency
2. ALWAYS include appropriate indexes for performance
3. ALWAYS add timestamps (created_at, updated_at) to new tables
4. NEVER drop data without explicit confirmation
5. ALWAYS use proper data types (VARCHAR with limits, TIMESTAMP, etc.)
6. ALWAYS add foreign key constraints with proper CASCADE rules
7. ALWAYS consider performance implications

RESPONSE FORMAT:
Return a JSON object with this structure:
{
    "sql": "-- The migration SQL",
    "rollback_sql": "-- SQL to undo this migration",
    "confidence": 0.95,
    "warnings": ["Array of potential issues"],
    "suggestions": ["Array of additional improvements"],
    "description": "Brief description of what this does",
    "reasoning": "Why you chose this approach"
}

EXAMPLES:

User: "Add email column to users table"
Response:
{
    "sql": "ALTER TABLE users\\nADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE;\\n\\nCREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
    "rollback_sql": "ALTER TABLE users\\nDROP COLUMN IF EXISTS email;",
    "confidence": 0.95,
    "warnings": ["Existing data will have NULL emails initially"],
    "suggestions": ["Consider adding NOT NULL after backfilling data", "Consider email validation at application level"],
    "description": "Add unique email column to users table with index",
    "reasoning": "Used UNIQUE constraint to prevent duplicate emails. Added index for performance on email lookups."
}"""

    def _build_user_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the user prompt with context"""
        parts = [f"Generate a PostgreSQL migration for: {prompt}"]

        if context:
            if "tables" in context:
                parts.append(f"\nExisting tables: {', '.join(context['tables'])}")
            if "current_schema" in context:
                parts.append(f"\nCurrent schema:\n{context['current_schema']}")

        return "\n".join(parts)

    def generate_migration(
        self, prompt: str, context: Optional[Dict[str, Any]] = None, file_type: str = "sql"
    ) -> GeneratedMigration:
        """Generate migration using OpenAI"""

        if not self.is_available():
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")

        if file_type != "sql":
            raise NotImplementedError("Python migrations not yet supported with AI")

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": self._build_user_prompt(prompt, context)},
                ],
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"},
            )

            # Parse response
            result = json.loads(response.choices[0].message.content)

            return GeneratedMigration(
                sql=result.get("sql", ""),
                rollback_sql=result.get("rollback_sql"),
                confidence=result.get("confidence", 0.0),
                warnings=result.get("warnings", []),
                suggestions=result.get("suggestions", []),
                description=result.get("description", prompt),
                reasoning=result.get("reasoning"),
            )

        except Exception as e:
            # Fallback generation on error
            return GeneratedMigration(
                sql=f"-- Error generating migration: {str(e)}\\n-- Please write migration manually",
                rollback_sql=None,
                confidence=0.0,
                warnings=[f"AI generation failed: {str(e)}"],
                suggestions=["Please write migration manually", "Check API key configuration"],
                description=f"Failed: {prompt}",
            )

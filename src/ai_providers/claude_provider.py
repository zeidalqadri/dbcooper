
import os
import json
from typing import Optional, Dict, Any
from anthropic import Anthropic

from .base import AIProvider, GeneratedMigration


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider for migration generation"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None

    def is_available(self) -> bool:
        """Check if Claude is configured"""
        return self.client is not None

    def _build_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the complete prompt for Claude"""
        system_instruction = """You are an expert database migration specialist. Generate safe, idempotent PostgreSQL migrations.

CRITICAL RULES:
- ALWAYS use IF NOT EXISTS / IF EXISTS
- ALWAYS include indexes
- ALWAYS add timestamps to new tables
- NEVER drop data without confirmation
- Use proper data types
- Add foreign key constraints

Return JSON with: sql, rollback_sql, confidence (0-1), warnings (array), suggestions (array), description, reasoning"""

        user_prompt = f"{system_instruction}\n\nGenerate migration for: {prompt}"

        if context:
            if "tables" in context:
                user_prompt += f"\n\nExisting tables: {', '.join(context['tables'])}"

        return user_prompt

    def generate_migration(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        file_type: str = "sql"
    ) -> GeneratedMigration:
        """Generate migration using Claude"""

        if not self.is_available():
            raise ValueError("Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable.")

        if file_type != "sql":
            raise NotImplementedError("Python migrations not yet supported with AI")

        try:
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": self._build_prompt(prompt, context)
                }]
            )

            # Parse response
            content = message.content[0].text

            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            return GeneratedMigration(
                sql=result.get("sql", ""),
                rollback_sql=result.get("rollback_sql"),
                confidence=result.get("confidence", 0.0),
                warnings=result.get("warnings", []),
                suggestions=result.get("suggestions", []),
                description=result.get("description", prompt),
                reasoning=result.get("reasoning")
            )

        except Exception as e:
            return GeneratedMigration(
                sql=f"-- Error generating migration: {str(e)}\n-- Please write migration manually",
                rollback_sql=None,
                confidence=0.0,
                warnings=[f"AI generation failed: {str(e)}"],
                suggestions=["Please write migration manually", "Check API key configuration"],
                description=f"Failed: {prompt}"
            )

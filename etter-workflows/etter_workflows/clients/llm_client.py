"""
LLM client for Etter Workflows.

Provides LLM operations for:
- Job description formatting (markdown conversion)
- Text processing and extraction

This client is designed to:
1. Use the existing ModelManager from draup_world_model (when available)
2. Use direct LLM API calls (for isolated deployment)
"""

import logging
from typing import Any, Dict, Optional
from functools import lru_cache

from etter_workflows.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM client for workflow operations.

    Provides methods for text processing needed by the self-service pipeline.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        use_existing_manager: bool = True,
    ):
        """
        Initialize LLM client.

        Args:
            provider: LLM provider (gemini, claude, openai)
            model: Model name
            api_key: API key
            use_existing_manager: Try to use existing ModelManager
        """
        settings = get_settings()
        self.provider = provider or settings.llm_provider
        self.model = model or settings.llm_model
        self.api_key = api_key or settings.llm_api_key
        self._llm = None
        self._model_manager = None

        # Try to use existing ModelManager from draup_world_model
        if use_existing_manager:
            try:
                from draup_world_model.chatbot_components.model_manager import ModelManager
                self._model_manager = ModelManager()
                self._llm = self._model_manager.get_model_for_analysis(self.model)
                logger.info(f"Using existing ModelManager with model: {self.model}")
            except ImportError:
                logger.info("draup_world_model not available, using standalone LLM client")
            except Exception as e:
                logger.warning(f"Failed to initialize ModelManager: {e}")

    def _get_llm(self):
        """Get or create LLM instance."""
        if self._llm is not None:
            return self._llm

        # Fallback to direct API calls
        raise NotImplementedError(
            "Standalone LLM client not implemented. "
            "Please ensure draup_world_model is available."
        )

    def format_job_description(
        self,
        jd_text: str,
        job_title: str = "",
    ) -> str:
        """
        Format a job description into clean markdown.

        This mirrors the functionality in jd_markdown_converter.py.

        Args:
            jd_text: Raw job description text
            job_title: Optional job title

        Returns:
            Formatted markdown string
        """
        if not jd_text or len(jd_text.strip()) < 10:
            return ""

        try:
            from langchain_core.prompts import ChatPromptTemplate

            prompt_template = ChatPromptTemplate.from_messages([
                ("system",
                 "You are an expert at formatting documents. Reformat the following job description "
                 "into clean markdown format. Use headings for sections like 'Responsibilities', "
                 "'Qualifications', etc. If a job title is present, make it a level 1 heading."),
                ("human",
                 "Please reformat this job description with given {job_title}:\n\n---\n{jd_text}\n---"),
            ])

            llm = self._get_llm()
            prompt_value = prompt_template.invoke({
                "jd_text": jd_text,
                "job_title": job_title,
            })
            response_message = llm.invoke(prompt_value)
            content = response_message.content

            # Clean up markdown formatting
            content_cleaned = content.replace("```markdown\n", "").replace("\n```", "").strip()
            return content_cleaned

        except Exception as e:
            logger.error(f"Error formatting job description: {e}")
            # Return original text if formatting fails
            return jd_text

    def extract_text(
        self,
        prompt: str,
        text: str,
        max_tokens: int = 4096,
    ) -> str:
        """
        Extract or process text using LLM.

        Args:
            prompt: System prompt for the task
            text: Input text to process
            max_tokens: Maximum tokens for response

        Returns:
            Processed text
        """
        try:
            from langchain_core.prompts import ChatPromptTemplate

            prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt),
                ("human", "{text}"),
            ])

            llm = self._get_llm()
            prompt_value = prompt_template.invoke({"text": text})
            response_message = llm.invoke(prompt_value)
            return response_message.content

        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            raise


# Singleton client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get the singleton LLM client instance.

    Returns:
        LLMClient instance
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def reset_llm_client():
    """Reset the singleton client (for testing)."""
    global _llm_client
    _llm_client = None

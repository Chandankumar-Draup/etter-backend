"""
Base generator with LLM integration.

All generators inherit from this. Provides:
- LLM invocation with retry
- JSON parsing from LLM output
- Batch prompt construction
- File I/O for generated data
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from draup_world_model.digital_twin.config import LLMConfig

logger = logging.getLogger(__name__)


class BaseGenerator:
    """Base class for all data generators."""

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.llm_config = llm_config or LLMConfig()
        self._llm = None

    @property
    def llm(self):
        """Lazy-load LLM instance."""
        if self._llm is None:
            self._llm = self._init_llm()
        return self._llm

    def _init_llm(self):
        """Initialize LLM using existing project infrastructure."""
        from draup_world_model.llm_models import get_claude_llm
        return get_claude_llm(
            model_name=self.llm_config.model,
            temperature=self.llm_config.temperature,
            max_tokens=self.llm_config.max_tokens,
        )

    def invoke_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Call LLM with retry logic."""
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(prompt)
                return response.content if hasattr(response, "content") else str(response)
            except Exception as e:
                wait = 2 ** (attempt + 1)
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}. Retrying in {wait}s.")
                time.sleep(wait)
        raise RuntimeError(f"LLM call failed after {max_retries} attempts")

    def parse_json_response(self, text: str) -> Any:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove first line (```json or ```)
            lines = cleaned.split("\n")
            lines = lines[1:]
            # Remove last ``` line
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Try to find JSON array or object within the text
            for start_char, end_char in [("[", "]"), ("{", "}")]:
                start = cleaned.find(start_char)
                end = cleaned.rfind(end_char)
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(cleaned[start:end + 1])
                    except json.JSONDecodeError:
                        continue
            logger.error(f"Failed to parse JSON from response: {text[:500]}...")
            raise ValueError(f"Could not parse JSON from LLM response: {e}")

    def generate_batch(self, prompt: str, max_parse_retries: int = 2) -> List[Dict[str, Any]]:
        """Send a batch prompt and parse the JSON array response.

        Retries on JSON parse failures (typically caused by truncated responses
        when the LLM hits max_tokens). After retries are exhausted, attempts to
        repair truncated JSON by recovering complete items.
        """
        last_error = None
        last_response = ""
        for attempt in range(max_parse_retries + 1):
            response_text = self.invoke_llm(prompt)
            last_response = response_text
            try:
                return self.parse_json_response(response_text)
            except ValueError as e:
                last_error = e
                if attempt < max_parse_retries:
                    logger.warning(
                        f"JSON parse failed (attempt {attempt + 1}/{max_parse_retries + 1}), "
                        f"retrying with fresh LLM call: {e}"
                    )
                    time.sleep(2)

        # All retries exhausted - try to repair truncated JSON
        repaired = self._try_repair_truncated_json(last_response)
        if repaired is not None:
            logger.warning(
                f"Recovered {len(repaired)} items from truncated response "
                f"(original error: {last_error})"
            )
            return repaired

        raise last_error

    @staticmethod
    def _try_repair_truncated_json(text: str) -> Optional[List[Dict[str, Any]]]:
        """Attempt to recover items from a truncated JSON array.

        When the LLM hits max_tokens, the JSON response gets cut off mid-item.
        Strategy: find the last complete JSON object (ending with '}') before
        the truncation point, then close the array.
        """
        cleaned = text.strip()
        # Strip markdown code fences
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        # Find the start of the JSON array
        start = cleaned.find("[")
        if start == -1:
            return None

        content = cleaned[start:]

        # Find the last complete object (ending with '}')
        last_brace = content.rfind("}")
        if last_brace == -1:
            return None

        # Take up to the last complete object, strip trailing comma, close array
        truncated = content[:last_brace + 1].rstrip().rstrip(",") + "\n]"

        try:
            result = json.loads(truncated)
            if isinstance(result, list) and len(result) > 0:
                return result
        except json.JSONDecodeError:
            pass

        return None

    @staticmethod
    def save_json(data: Any, path: Path) -> None:
        """Save data to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {path} ({len(data) if isinstance(data, list) else 1} items)")

    @staticmethod
    def load_json(path: Path) -> Any:
        """Load data from JSON file."""
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def save_per_function(
        items: List[Dict[str, Any]],
        entity_dir: Path,
        function_id_key: str = "function_id",
    ) -> Dict[str, int]:
        """Save items grouped by function_id to per-function files.

        Each function gets its own JSON file inside entity_dir, keeping
        individual files small and enabling per-function resumability.
        """
        entity_dir.mkdir(parents=True, exist_ok=True)
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            func_id = item.get(function_id_key, "unknown")
            grouped.setdefault(func_id, []).append(item)
        stats: Dict[str, int] = {}
        for func_id, func_items in grouped.items():
            path = entity_dir / f"{func_id}.json"
            with open(path, "w") as f:
                json.dump(func_items, f, indent=2)
            stats[func_id] = len(func_items)
            logger.info(f"  Saved {path.name}: {len(func_items)} items")
        return stats

    @staticmethod
    def load_from_dir(entity_dir: Path) -> List[Dict[str, Any]]:
        """Load and merge all JSON files from a directory."""
        items: List[Dict[str, Any]] = []
        if not entity_dir.exists():
            return items
        for path in sorted(entity_dir.glob("*.json")):
            with open(path) as f:
                data = json.load(f)
                if isinstance(data, list):
                    items.extend(data)
                elif isinstance(data, dict):
                    items.append(data)
        logger.info(f"Loaded {len(items)} items from {entity_dir}")
        return items

    @staticmethod
    def make_id(*parts: str) -> str:
        """Create a snake_case ID from parts."""
        combined = "_".join(parts)
        return (
            combined.lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("&", "and")
            .replace("/", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(",", "")
            .replace("__", "_")
            .strip("_")
        )

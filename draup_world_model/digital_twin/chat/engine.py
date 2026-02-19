"""
Chat engine for the Digital Twin graph.

Pipeline:
  1. User question + history → Cypher generation (or direct answer)
  2. Cypher validation (read-only only)
  3. Execute against Neo4j
  4. Stream insights from LLM

Uses the Anthropic SDK directly for simplicity and native streaming.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, Generator, List, Optional

from draup_world_model.digital_twin.automation import normalize_result_rows

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────

DEFAULT_MODEL = os.environ.get("DT_CHAT_MODEL", "claude-sonnet-4-5-20250929")
MAX_RESULT_ROWS = 50
MAX_HISTORY_TURNS = 6  # Last N user/assistant pairs to send to LLM

# ── Prompts ──────────────────────────────────────────────────────────

CYPHER_SYSTEM_PROMPT = """\
You are a Cypher query generator for a Neo4j Digital Twin workforce graph.

Given a user's natural language question, generate a single READ-ONLY Cypher query
to retrieve the relevant data from the graph described below.

{schema}

## Rules

1. Generate ONLY read queries: MATCH ... RETURN.  NEVER use CREATE, MERGE, DELETE, SET, REMOVE, DETACH, DROP, CALL.
2. Always include LIMIT (max 50 rows) unless doing count/sum/avg aggregations that return few rows.
3. Use the EXACT node labels and property names from the schema above.  Labels start with DT, relationships start with DT_.
4. Property values are CASE-SENSITIVE.  Use exact names from the Available Functions/Roles/Technologies lists.
5. For hierarchy traversal, use variable-length paths:  [:DT_CONTAINS*] to go from Function → SubFunction → JobFamilyGroup → JobFamily.
6. When the user asks about a function/role, try to match the closest entity name from the lists above.
7. If the question absolutely cannot be answered from the graph data (e.g. greetings, opinions, external knowledge), respond with exactly:  DIRECT: <your brief answer>
8. If the question is ambiguous, make reasonable assumptions and proceed.
9. automation_score and automation_potential are ALREADY on a 0–100 scale.  Do NOT multiply by 100.  Use round(r.automation_score) AS automation_pct.
10. Output ONLY the Cypher query.  No markdown code blocks, no explanation, no comments.
"""

INSIGHT_SYSTEM_PROMPT = """\
You are a workforce analytics expert analyzing data from a Digital Twin workforce simulation graph.

Given the user's question and query results, provide a clear, insightful analysis.

Rules:
- Answer the question DIRECTLY in the first sentence, then elaborate.
- Use ONLY the data provided — never fabricate or assume numbers not present.
- Use **bold** for key metrics and findings.
- Highlight patterns: outliers, concentrations, spreads (highest vs lowest).
- Note practical implications for workforce planning when relevant.
- If data is empty or insufficient, say so clearly and suggest what to try instead.
- Be concise: 2–4 sentences for simple queries, up to a paragraph for complex analysis.
- Do NOT repeat the raw data in a list — the user can already see the table.

After your analysis, on a NEW line, output the exact marker FOLLOWUPS: followed by a JSON array of 3 concise follow-up questions the user might ask next.
Example ending:
FOLLOWUPS: ["What skills do these roles need?", "How does this compare to other functions?", "Which tasks can be automated?"]
"""

# ── Forbidden Cypher patterns ────────────────────────────────────────

_WRITE_PATTERN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|CALL)\b",
    re.IGNORECASE,
)


def _validate_cypher(query: str) -> Optional[str]:
    """
    Validate that a Cypher query is read-only.
    Returns an error message if invalid, None if OK.
    """
    if _WRITE_PATTERN.search(query):
        return "Query rejected: write operations are not allowed."
    if "MATCH" not in query.upper():
        return "Query rejected: must contain a MATCH clause."
    if "RETURN" not in query.upper():
        return "Query rejected: must contain a RETURN clause."
    return None


def _clean_cypher(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM output."""
    text = raw.strip()
    # Remove ```cypher ... ``` wrapping
    text = re.sub(r"^```(?:cypher)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _rows_to_serializable(rows: List[Dict]) -> List[Dict]:
    """Convert Neo4j result rows to JSON-safe dicts."""
    clean = []
    for row in rows:
        r = {}
        for k, v in row.items():
            if isinstance(v, (int, float, str, bool, type(None))):
                r[k] = v
            elif isinstance(v, list):
                r[k] = [str(x) for x in v]
            else:
                r[k] = str(v)
        clean.append(r)
    return clean


class ChatEngine:
    """
    Agentic chat engine for the Digital Twin graph.

    Usage:
        engine = ChatEngine(neo4j_conn, schema_ctx)
        for event in engine.stream(message, history):
            yield f"data: {json.dumps(event)}\\n\\n"
    """

    def __init__(self, neo4j_conn: Any, schema_context_str: str):
        self._conn = neo4j_conn
        self._schema = schema_context_str
        self._client = None  # Lazy-init Anthropic client

    def _get_client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    # ── Public API ───────────────────────────────────────────────────

    def stream(
        self,
        message: str,
        history: Optional[List[Dict]] = None,
    ) -> Generator[Dict, None, None]:
        """
        Process a user message and yield SSE event dicts.

        Event types:
            status   - Step progress updates
            cypher   - Generated Cypher query
            data     - Query result rows + columns
            insight  - Streamed insight text chunk
            suggest  - Follow-up suggestions
            error    - Error message
            done     - Completion with timing
        """
        t0 = time.time()
        history = history or []

        try:
            # ── Step 1: Generate Cypher ──────────────────────────────
            yield {"type": "status", "step": "thinking", "content": "Understanding your question..."}

            cypher_or_direct = self._generate_cypher(message, history)

            # Check if LLM decided to answer directly (no query needed)
            if cypher_or_direct.startswith("DIRECT:"):
                direct_answer = cypher_or_direct[7:].strip()
                yield {"type": "insight", "content": direct_answer}
                yield {"type": "done", "time_ms": int((time.time() - t0) * 1000)}
                return

            cypher = _clean_cypher(cypher_or_direct)

            # Validate
            err = _validate_cypher(cypher)
            if err:
                yield {"type": "error", "content": err}
                yield {"type": "done", "time_ms": int((time.time() - t0) * 1000)}
                return

            yield {"type": "cypher", "content": cypher}

            # ── Step 2: Execute query ────────────────────────────────
            yield {"type": "status", "step": "querying", "content": "Querying the graph..."}

            rows, exec_error = self._execute_query(cypher)

            if exec_error:
                # Try to fix the query once
                yield {"type": "status", "step": "retrying", "content": "Fixing query and retrying..."}
                cypher = self._fix_cypher(cypher, exec_error, message)
                cypher = _clean_cypher(cypher)
                err = _validate_cypher(cypher)
                if err:
                    yield {"type": "error", "content": f"Query failed: {exec_error}"}
                    yield {"type": "done", "time_ms": int((time.time() - t0) * 1000)}
                    return
                yield {"type": "cypher", "content": cypher}
                rows, exec_error = self._execute_query(cypher)
                if exec_error:
                    yield {"type": "error", "content": f"Query failed after retry: {exec_error}"}
                    yield {"type": "done", "time_ms": int((time.time() - t0) * 1000)}
                    return

            # Serialize results and normalise automation scores
            clean_rows = _rows_to_serializable(rows)
            clean_rows = normalize_result_rows(clean_rows)
            columns = list(clean_rows[0].keys()) if clean_rows else []

            yield {
                "type": "data",
                "content": {
                    "columns": columns,
                    "rows": clean_rows,
                    "count": len(clean_rows),
                },
            }

            # ── Step 3: Stream insights + extract suggestions ────────
            yield {"type": "status", "step": "analyzing", "content": "Analyzing results..."}

            for event in self._stream_insights(message, cypher, clean_rows, history):
                yield event

            yield {"type": "done", "time_ms": int((time.time() - t0) * 1000)}

        except Exception as e:
            logger.exception("Chat engine error")
            yield {"type": "error", "content": f"Unexpected error: {str(e)}"}
            yield {"type": "done", "time_ms": int((time.time() - t0) * 1000)}

    # ── Internal: Cypher generation ──────────────────────────────────

    def _generate_cypher(self, message: str, history: List[Dict]) -> str:
        """Generate a Cypher query from the user message."""
        system = CYPHER_SYSTEM_PROMPT.format(schema=self._schema)

        messages = self._build_cypher_messages(message, history)

        response = self._get_client().messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2048,
            temperature=0.0,
            system=system,
            messages=messages,
        )

        return response.content[0].text.strip()

    def _build_cypher_messages(self, message: str, history: List[Dict]) -> List[Dict]:
        """Build the message list for Cypher generation, including relevant history."""
        messages = []

        # Include recent history for context (follow-ups, refinements)
        recent = history[-(MAX_HISTORY_TURNS * 2):] if history else []
        for turn in recent:
            role = turn.get("role", "user")
            if role == "user":
                messages.append({"role": "user", "content": turn["content"]})
            elif role == "assistant":
                # Summarize the assistant turn for context
                summary_parts = []
                if turn.get("cypher"):
                    summary_parts.append(f"Cypher: {turn['cypher']}")
                if turn.get("data") and turn["data"].get("count"):
                    summary_parts.append(f"Returned {turn['data']['count']} rows")
                if turn.get("insight"):
                    # Truncate insight to first 200 chars for context
                    summary_parts.append(turn["insight"][:200])
                if summary_parts:
                    messages.append({"role": "assistant", "content": "\n".join(summary_parts)})

        messages.append({"role": "user", "content": message})
        return messages

    def _fix_cypher(self, failed_query: str, error: str, original_question: str) -> str:
        """Attempt to fix a failed Cypher query."""
        system = CYPHER_SYSTEM_PROMPT.format(schema=self._schema)

        fix_prompt = (
            f"The following Cypher query failed with this error:\n\n"
            f"Query:\n{failed_query}\n\n"
            f"Error:\n{error}\n\n"
            f"Original question: {original_question}\n\n"
            f"Generate a corrected Cypher query. Output ONLY the query."
        )

        response = self._get_client().messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2048,
            temperature=0.0,
            system=system,
            messages=[{"role": "user", "content": fix_prompt}],
        )

        return response.content[0].text.strip()

    # ── Internal: Query execution ────────────────────────────────────

    def _execute_query(self, cypher: str) -> tuple:
        """Execute a Cypher query. Returns (rows, error_or_none)."""
        try:
            rows = self._conn.execute_read_query(cypher)
            if rows is None:
                rows = []
            return rows, None
        except Exception as e:
            logger.warning("Cypher execution failed: %s", e)
            return [], str(e)

    # ── Internal: Insight streaming ──────────────────────────────────

    # Marker the LLM uses to separate insight text from follow-up suggestions.
    _FOLLOWUP_MARKER = "FOLLOWUPS:"

    def _stream_insights(
        self,
        question: str,
        cypher: str,
        rows: List[Dict],
        history: List[Dict],
    ) -> Generator[Dict, None, None]:
        """
        Stream insight text from the LLM, token by token.

        The LLM is instructed to append FOLLOWUPS: [...] at the end.
        This method buffers the stream to detect the marker, yielding
        insight chunks in real-time and emitting a separate 'suggest'
        event once the suggestions JSON is captured.
        """

        # Build data summary for the prompt
        if not rows:
            data_text = "(No results returned — the query matched zero records.)"
        elif len(rows) <= 20:
            data_text = json.dumps(rows, indent=2, default=str)
        else:
            data_text = json.dumps(rows[:20], indent=2, default=str)
            data_text += f"\n... ({len(rows)} total rows, showing first 20)"

        # Build conversation context
        conv_context = ""
        if history:
            recent = history[-(MAX_HISTORY_TURNS * 2):]
            conv_parts = []
            for turn in recent:
                role = turn.get("role", "user")
                if role == "user":
                    conv_parts.append(f"User: {turn['content']}")
                elif role == "assistant" and turn.get("insight"):
                    conv_parts.append(f"Assistant: {turn['insight'][:300]}")
            if conv_parts:
                conv_context = "Previous conversation:\n" + "\n".join(conv_parts) + "\n\n"

        user_prompt = (
            f"{conv_context}"
            f"User question: {question}\n\n"
            f"Cypher query used:\n{cypher}\n\n"
            f"Query results:\n{data_text}"
        )

        marker = self._FOLLOWUP_MARKER
        marker_len = len(marker)
        full_text = ""
        flushed = 0
        marker_found = False

        try:
            with self._get_client().messages.stream(
                model=DEFAULT_MODEL,
                max_tokens=4096,
                temperature=0.2,
                system=INSIGHT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for token in stream.text_stream:
                    full_text += token

                    if marker_found:
                        continue  # accumulating suggestions tail

                    # Check if marker has appeared in accumulated text
                    idx = full_text.find(marker, max(0, flushed - marker_len))
                    if idx >= 0:
                        # Flush any insight text before the marker
                        remaining = full_text[flushed:idx].rstrip()
                        if remaining:
                            yield {"type": "insight", "content": remaining}
                        marker_found = True
                        continue

                    # Yield text we're certain isn't part of the marker
                    safe_end = len(full_text) - marker_len
                    if safe_end > flushed:
                        yield {"type": "insight", "content": full_text[flushed:safe_end]}
                        flushed = safe_end

        except Exception as e:
            logger.error("Insight streaming failed: %s", e)
            yield {"type": "insight", "content": f"(Could not generate insights: {e})"}
            return

        # Flush remaining text
        if not marker_found:
            if flushed < len(full_text):
                yield {"type": "insight", "content": full_text[flushed:]}
        else:
            # Parse suggestions from text after marker
            suggestions_text = full_text[full_text.find(marker) + marker_len:].strip()
            try:
                suggestions = json.loads(suggestions_text)
                if isinstance(suggestions, list) and len(suggestions) >= 1:
                    yield {"type": "suggest", "content": suggestions[:3]}
            except Exception:
                logger.debug("Could not parse follow-up suggestions: %s", suggestions_text[:100])

"""Utils for task simulator."""

import re
from typing import Dict, Optional
from draup_packages.draup_llm_manager import DraupLLMManager
from constants.auth import ENV, DRAUP_LLM_USER


async def request_llm(
    prompt_name: str, placeholders: Dict, config: Dict
) -> Optional[str]:
    """Request LLM to get the response."""

    try:
        _llm_client = DraupLLMManager(
            env=ENV,
            user=DRAUP_LLM_USER,
            llm_provider=config["provider"],
            process="task_automation_scoring",
        )

        response = await _llm_client.acompletion(
            model=config["model"],
            prompt_name=prompt_name,
            placeholders=placeholders,
            temperature=0.0,
            timeout=60,
        )
    except Exception as e:
        print("Error calling the LLM: ", e)
        return None

    if response.choices[0].message.content is None:
        return None

    return response.choices[0].message.content


def extract_tag_from_text(text: str, tag: str) -> str:
    """Extract content between XML-style tags from text."""
    if not text:
        return ""
    
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    if match:
        cleaned_response = match.group(1).strip()
    else:
        cleaned_response = re.sub(rf"<{tag}>\s*|\s*</{tag}>", "", text.strip())

    return cleaned_response


def extract_tag_from_markdown(text: str, tag: str) -> str:
    """Extract content between markdown tags from text."""
    text = text.strip()
    match = re.search(rf"```{tag}(.*?)```", text, re.DOTALL)
    if match:
        cleaned_response = match.group(1).strip()
    else:
        cleaned_response = re.sub(rf"```{tag}\s*|\s*```", "", text.strip())

    return cleaned_response

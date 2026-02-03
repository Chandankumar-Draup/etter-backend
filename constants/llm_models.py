GEMINI_FLASH_MODEL = "gemini/gemini-3-flash-preview"
GEMINI_PRO_MODEL = "gemini/gemini-3-pro-preview"
GEMINI_2_5_FLASH_MODEL = "gemini/gemini-2.5-flash"
GPT_4_1_MODEL = "gpt-4.1"
GPT_5_1_MODEL = "gpt-5.1"
PERPLEXITY_SONAR_MODEL = "perplexity/sonar"
CLAUDE_SONNET_MODEL = "claude-sonnet-4-5-20250929"

GEMINI_PROVIDER = "gemini"
OPENAI_PROVIDER = "openai"
PERPLEXITY_PROVIDER = "perplexity"
ANTHROPIC_PROVIDER = "anthropic"

TASK_AUTOMATION_SCORING_PROMPT = "task_automation_scoring"
ETTER_TASK_SIMULATION_SCORING_PROMPT = "etter_task_simulation_scoring"

ROLE_ADJACENCY_MODEL_CONFIG = {
    "model": GPT_4_1_MODEL,
    "provider": OPENAI_PROVIDER,
}

ROLE_ADJACENCY_FALLBACK_MODEL_CONFIG = {
    "provider": GEMINI_PROVIDER,
    "model": GEMINI_2_5_FLASH_MODEL,
}

TASK_SIMULATOR_MODEL_CONFIGS = [
    {
        "model": GEMINI_2_5_FLASH_MODEL,
        "provider": GEMINI_PROVIDER,
        "prompt_name": TASK_AUTOMATION_SCORING_PROMPT,
    },
    {
        "model": GPT_5_1_MODEL,
        "provider": OPENAI_PROVIDER,
        "prompt_name": TASK_AUTOMATION_SCORING_PROMPT,
    },
    {
        "model": PERPLEXITY_SONAR_MODEL,
        "provider": PERPLEXITY_PROVIDER,
        "prompt_name": TASK_AUTOMATION_SCORING_PROMPT,
    },
    {
        "model": CLAUDE_SONNET_MODEL,
        "provider": ANTHROPIC_PROVIDER,
        "prompt_name": TASK_AUTOMATION_SCORING_PROMPT,
    },
]

ETTER_SCORING_MODEL_CONFIGS = [
    {
        "model": GPT_5_1_MODEL,
        "provider": OPENAI_PROVIDER,
        "prompt_name": ETTER_TASK_SIMULATION_SCORING_PROMPT,
    },
    {
        "model": CLAUDE_SONNET_MODEL,
        "provider": ANTHROPIC_PROVIDER,
        "prompt_name": ETTER_TASK_SIMULATION_SCORING_PROMPT,
    },
]


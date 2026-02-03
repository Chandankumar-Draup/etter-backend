## Task Simulator API

### Overview

Use this API to generate automation-readiness scores for a set of tasks. The
service merges your provided tasks with contextual tasks fetched from ETTER
sources (when a company or role is supplied) and evaluates them across multiple
LLM providers. Each task receives aggregated statistics plus per-model scores.

## Base URL

```
http://127.0.0.1:7071
```

## Endpoint

```
POST /api/etter/v1/task_simulator_scores
```

### Request body

Send a JSON object with the following fields:

- `tasks` **(Required)**: `List[str]` — Explicit task names to score.
- `company` *(Optional)*: `str` — Company name used to fetch additional tasks
  from ETTER services.
- `role` *(Optional)*: `str` — Role name paired with the company to refine the
  fetched task list.

When `tasks` are empty but `company`/`role` are provided, the service attempts
to build the task list from ETTER sources. If both provided and remote tasks
exist, they are merged (deduplicated) before scoring.

#### Example

```json
{
  "tasks": [
    "Prepare monthly sales summary in Excel",
    "Draft a job description for a Data Analyst"
  ],
  "company": "Walmart Inc.",
  "role": "Data Scientist"
}
```

### Response

Returns a JSON array where each entry summarizes automation scores for a task.

```json
[
  {
    "task": "Prepare monthly sales summary in Excel",
    "mean_scores": 72.5,
    "variances": 18.5,
    "model_task_results": [
      {
        "model": "gpt-5",
        "score": 70
      },
      {
        "model": "gemini/gemini-2.5-pro",
        "score": 75
      },
      {
        "model": "perplexity/sonar",
        "score": 65
      },
      {
        "model": "claude-sonnet-4-5-20250929",
        "score": 80
      }
    ]
  },
  {
    "task": "Draft a job description for a Data Analyst",
    "mean_scores": 61.25,
    "variances": 12.9,
    "model_task_results": [
      {
        "model": "gpt-5",
        "score": 60
      },
      {
        "model": "gemini/gemini-2.5-pro",
        "score": 55
      },
      {
        "model": "perplexity/sonar",
        "score": 70
      },
      {
        "model": "claude-sonnet-4-5-20250929",
        "score": 60
      }
    ]
  }
]
```

Each `model_task_results` entry corresponds to a single LLM evaluation. Scores
range from `0` (no automation potential) to `100` (fully automatable).

### Errors

#### Server Error

```json
{
  "detail": "Error getting task simulator scores: <error details>"
}
```

The API returns HTTP `500` when scoring fails (e.g., downstream ETTER services
are unavailable or LLM evaluation errors occur). Retry the request or check the
server logs for details.


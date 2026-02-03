import pytest
from typing import Any, Dict, List

import ml_models.task_simulator.task_similuator as ts_mod
from ml_models.task_simulator.task_similuator import parse_json_from_llm_response


def _example_tasks() -> List[str]:
    return [
        "Design and implement a FastAPI endpoint to generate sales reports",
    ]


def _mock_llm_results_for_example_task() -> List[Dict[str, Any]]:
    task = _example_tasks()[0]
    return [
        {
            "model": "gpt-4.1-mini",
            "provider": "openai",
            "response": "<json>[...]</json>",
            "task_scores": [{"task": task, "score": 80, "reason": ""}],
        },
        {
            "model": "gemini/gemini-2.0-flash",
            "provider": "gemini",
            "response": "<json>[...]</json>",
            "task_scores": [{"task": task, "score": 85, "reason": ""}],
        },
    ]


@pytest.mark.asyncio
async def test_compute_task_simulator_scores_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    tasks = _example_tasks()
    
    async def mock_get_llm_scores(*args, **kwargs):
        return _mock_llm_results_for_example_task()

    monkeypatch.setattr(ts_mod, "get_llm_scores_for_tasks", mock_get_llm_scores)

    # Act
    results = await ts_mod.compute_task_simulator_scores(tasks)

    # Assert
    assert isinstance(results, list)
    assert len(results) == 1
    task_result = results[0]

    assert task_result["task"] == tasks[0]
    assert task_result["mean_scores"] == pytest.approx(82.5)
    # Sample variance of [80, 85] is 12.5
    assert task_result["variances"] == pytest.approx(12.5)
    assert {r["model"] for r in task_result["model_task_results"]} == {
        "gpt-4.1-mini",
        "gemini/gemini-2.0-flash",
    }


@pytest.mark.asyncio
async def test_compute_task_simulator_scores_single_model(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    task = _example_tasks()[0]
    tasks = [task]
    mock_results = [
        {
            "model": "gpt-4.1-mini",
            "provider": "openai",
            "response": "<json>[...]</json>",
            "task_scores": [{"task": task, "score": 80, "reason": ""}],
        }
    ]
    
    async def mock_get_llm_scores(*args, **kwargs):
        return mock_results
        
    monkeypatch.setattr(ts_mod, "get_llm_scores_for_tasks", mock_get_llm_scores)

    # Act
    results = await ts_mod.compute_task_simulator_scores(tasks)

    # Assert
    assert len(results) == 1
    task_result = results[0]
    assert task_result["mean_scores"] == pytest.approx(80.0)
    # Variance should be 0.0 for a single data point
    assert task_result["variances"] == pytest.approx(0.0)
    assert task_result["model_task_results"] == [{"model": "gpt-4.1-mini", "score": 80, "reason": ""}]


@pytest.mark.asyncio
async def test_compute_task_simulator_scores_no_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    task = _example_tasks()[0]
    tasks = [task]
    mock_results = [
        {"model": "gpt-4.1-mini", "provider": "openai", "response": "<json>[...]</json>", "task_scores": []}
    ]
    
    async def mock_get_llm_scores(*args, **kwargs):
        return mock_results

    monkeypatch.setattr(ts_mod, "get_llm_scores_for_tasks", mock_get_llm_scores)

    # Act
    results = await ts_mod.compute_task_simulator_scores(tasks)

    # Assert
    assert len(results) == 1
    task_result = results[0]
    assert task_result["mean_scores"] == pytest.approx(0.0)
    assert task_result["variances"] == pytest.approx(0.0)
    assert task_result["model_task_results"] == []



def test_llm_output_parsing():
    """Test the parse_json_from_llm_response function."""
    examples = [
        {"input": "<json>{\"key\": \"value\"}</json>", "expected": {'key': 'value'}},
        {"input": "```json{\"key\": \"value\"}```", "expected": {'key': 'value'}},
        {"input": "{\"key\": \"value\"}", "expected": {'key': 'value'}},
        {"input": "{\"key\": \"value\"}", "expected": {'key': 'value'}},
        {"input": "```json{```", "expected": None},
    ]
    for example in examples:
        result = parse_json_from_llm_response(example["input"])
        assert result == example["expected"]

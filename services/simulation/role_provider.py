import re
import json
from os import environ
from typing import List, Dict, Final, Optional, cast
import traceback

import requests
import httpx
from constants.auth import DRAUP_LLM_USER, ENV
from services.simulation.store import InMemoryStore, RedisStore
from draup_packages.draup_llm_manager import DraupLLMManager
from ml_models.simulation import RoleDataProvider, Workload


REDIS_DB: Final[int] = int(environ.get("REDIS_DB", 14))
REDIS_PORT: Final[int] = int(environ.get("REDIS_PORT", 6379))
REDIS_HOST: Final[str] = environ.get("REDIS_RW_HOST", "localhost")
REDIS_PASSWORD: Final[Optional[str]] = environ.get("REDIS_PASSWORD", None)

CACHE_EXPERATION_SECONDS: Final[int] = 30 * 86400


def extract_json_from_text(text: str) -> Dict:
    # Clean the response - remove any markdown formatting
    match = re.search(r"```json(.*?)```", text, re.DOTALL)
    if match:
        cleaned_response = match.group(1).strip()
        # logger.error(f"This is the orignal message: {response_text}")
    else:
        # logger.error(f'Failed to extract out json {response_text}')
        cleaned_response = re.sub(r"```json\s*|\s*```", "", text.strip())

    # print("Parsing LLM response for AI quantification analysis", cleaned_response)

    # Parse JSON
    try:
        result = json.loads(cleaned_response)
    except Exception as e:
        print(f"This is the orignal message: {text}")
        raise Exception(f"Error parsing JSON: {e}")


def extract_tag_from_text(tag: str, text: str) -> Dict:
    # Clean the response - remove any markdown formatting
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    if match:
        cleaned_response = match.group(1).strip()
        # logger.error(f"This is the orignal message: {response_text}")
    else:
        # logger.error(f'Failed to extract out json {response_text}')
        cleaned_response = re.sub(rf"<{tag}>\s*|\s*</{tag}>", "", text.strip())

    # print("Parsing LLM response for AI quantification analysis", cleaned_response)
    result = cleaned_response
    return result


def convert_to_snake_case(input_str):
    # Use regular expression to insert underscores before capital letters
    # and convert the string to lowercase
    snake_str = re.sub(r"(?<!^)(?=[A-Z])", "_", input_str).lower()
    return snake_str


class EtterConsoleDataProvider(RoleDataProvider):
    def __init__(self, llm_provider: str = "openai", model_name: str = "gpt-4.1-mini"):
        self._model_name = model_name
        self._llm_provider = llm_provider
        self._cache = None
        try:
            self._cache = RedisStore(
                host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_DB
            )
        except Exception as e:
            self._cache = InMemoryStore()
            print(f"Error initializing redis: {e}", flush=True)

        self._llm_client = DraupLLMManager(
            env=ENV,
            user=DRAUP_LLM_USER,
            llm_provider=llm_provider,
            process="workload_automation_analysis",
        )

    def _get_workflow_history(self, company_name: str, role_name: str) -> dict:
        url = "https://draup-world.draup.technology/api/workflows"
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://draup-world.draup.technology",
        }

        data = {
            "workflow": "role_assessment_data",
            "step": "get_complete_assessment_data",
            "data": {
                "company": company_name,
                "role": role_name,
                "include_history": False,
            },
        }

        response = requests.post(url, headers=headers, json=data)
        return response.json()

    def _extract_task_analysis_and_impact_score(
        self, workflow_history: dict
    ) -> tuple[list[dict], float]:
        task_analysis_table_json = json.loads(
            workflow_history["current_step"]["data"]["assessment_data"][
                "current_version"
            ]["task_analysis"]["task_analysis_table"]
        )
        workload_analysis_table = task_analysis_table_json["body"]

        ai_impact_score = workflow_history["current_step"]["data"]["assessment_data"][
            "etter_ai_impact_score"
        ]

        if (
            "validated_ai_impact_score"
            in workflow_history["current_step"]["data"]["assessment_data"]
        ):
            ai_impact_score = workflow_history["current_step"]["data"][
                "assessment_data"
            ]["validated_ai_impact_score"]

        return workload_analysis_table, ai_impact_score

    def _validate_workload_table(self, workload_table: dict) -> List[Workload]:
        total_time = 0.0
        assert isinstance(workload_table, list), (
            f"Workload table is not a list: {workload_table}"
        )
        for workload in workload_table:
            assert isinstance(workload, dict), f"Workload is not a dict: {workload}"
            assert "Type" in workload, f"Type not in workload: {workload}"
            assert "Skill" in workload, f"Skill not in workload: {workload}"
            assert "Name" in workload, f"Name not in workload: {workload}"
            assert "Time" in workload, f"Time not in workload: {workload}"
            assert "Reason" in workload, f"Reason not in workload: {workload}"

            total_time += workload["Time"]

        if abs(total_time - 1.0) < 0.01:
            for workload in workload_table:
                workload["Time"] = round(workload["Time"] / total_time, 2)

        workload_table = cast(List[Workload], workload_table)
        return workload_table

    def _generate_auto_and_non_auto_workloads(self, data: Dict) -> List[Workload]:
        res = self._llm_client.completion(
            prompt_name="workload_automation_analysis_no_reasoning",
            placeholders={
                "COMPANY": data["company_name"],
                "ROLE": data["role_name"],
                "WORKLOAD_TABLE": json.dumps(data["workload_table"]),
                "AI_IMPACT_SCORE": str(data["ai_impact_score"]),
            },
        )

        workload_json_str = extract_tag_from_text(
            "json", res["choices"][0]["message"]["content"]
        )
        if workload_json_str is None:
            print(res["choices"][0]["message"]["content"])
            raise Exception("Failed to extract workload data")

        workload_data = json.loads(workload_json_str)
        workload_data = self._validate_workload_table(workload_data)
        return workload_data

    async def _generate_auto_and_non_auto_workloads_async(self, data: Dict) -> List[Workload]:
        res = await self._llm_client.acompletion(
            prompt_name="workload_automation_analysis_no_reasoning",
            placeholders={
                "COMPANY": data["company_name"],
                "ROLE": data["role_name"],
                "WORKLOAD_TABLE": json.dumps(data["workload_table"]),
                "AI_IMPACT_SCORE": str(data["ai_impact_score"]),
            },
        )

        workload_json_str = extract_tag_from_text(
            "json", res["choices"][0]["message"]["content"]
        )
        if workload_json_str is None:
            print(res["choices"][0]["message"]["content"])
            raise Exception("Failed to extract workload data")

        workload_data = json.loads(workload_json_str)
        workload_data = self._validate_workload_table(workload_data)
        return workload_data


    async def _get_workflow_history_async(self, company_name: str, role_name: str) -> dict:
        url = "https://draup-world.draup.technology/api/workflows"
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://draup-world.draup.technology",
        }

        data = {
            "workflow": "role_assessment_data",
            "step": "get_complete_assessment_data",
            "data": {
                "company": company_name,
                "role": role_name,
                "include_history": False,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()


    def get_responsibilities_from_role(
        self, role: str, company: str = ""
    ) -> List[Workload]:
        role_company_id = (
            f"workloads:{convert_to_snake_case(role)}#{convert_to_snake_case(company)}"
        )
        workload_data = self._cache.get(role_company_id)
        if workload_data:
            return json.loads(workload_data)

        try:
            try:
                workflow_history = self._get_workflow_history(company, role)
            except Exception as e:
                raise Exception(
                    f"Error getting workflow history for {company} {role}: {e}"
                )

            try:
                workload_analysis_table, ai_impact_score = (
                    self._extract_task_analysis_and_impact_score(workflow_history)
                )
            except Exception as e:
                print(f"Workflow history: {json.dumps(workflow_history)}")
                raise Exception(
                    f"Error extracting task analysis and impact score for {company} {role}: {e}"
                )
            try:
                workload_data = self._generate_auto_and_non_auto_workloads(
                    data={
                        "workload_table": workload_analysis_table,
                        "ai_impact_score": ai_impact_score,
                        "company_name": company,
                        "role_name": role,
                    }
                )
                self._cache.setex(
                    role_company_id, CACHE_EXPERATION_SECONDS, json.dumps(workload_data)
                )
            except Exception:
                raise Exception(
                    f"Generated a invalid workload table for {company} {role}: {workload_data}"
                )

        except Exception as e:
            print(
                f"While using llm to extract role metrics {role} {company}, Error:",
                e,
                flush=True,
            )
            traceback.print_exc()
            workload_data = [
                {
                    "Name": "Read and write internal documents",
                    "Type": "Non-Auto",
                    "Skill": 0.3,
                    "Time": 0.2,
                    "Reason": "This is a default workload for the role",
                },
                {
                    "Name": "Attend meetings",
                    "Type": "Non-Auto",
                    "Skill": 0.4,
                    "Time": 0.15,
                    "Reason": "This is a default workload for the role",
                },
                {
                    "Name": "Basic data entry",
                    "Type": "Auto",
                    "Skill": 0.2,
                    "Time": 0.3,
                    "Reason": "This is a default workload for the role",
                },
                {
                    "Name": "Email correspondence",
                    "Type": "Non-Auto",
                    "Skill": 0.35,
                    "Time": 0.15,
                    "Reason": "This is a default workload for the role",
                },
                {
                    "Name": "Schedule appointments",
                    "Type": "Auto",
                    "Skill": 0.25,
                    "Time": 0.2,
                    "Reason": "This is a default workload for the role",
                },
            ]

        return workload_data


    async def get_responsibilities_from_role_async(
            self, role: str, company: str = ""
        ) -> List[Workload]:
            role_company_id = (
                f"workloads:{convert_to_snake_case(role)}#{convert_to_snake_case(company)}"
            )
            workload_data = self._cache.get(role_company_id)
            if workload_data:
                return json.loads(workload_data)

            try:
                try:
                    workflow_history = await self._get_workflow_history_async(company, role)
                except Exception as e:
                    raise Exception(
                        f"Error getting workflow history for {company} {role}: {e}"
                    )

                try:
                    workload_analysis_table, ai_impact_score = (
                        self._extract_task_analysis_and_impact_score(workflow_history)
                    )
                except Exception as e:
                    print(f"Workflow history: {json.dumps(workflow_history)}")
                    raise Exception(
                        f"Error extracting task analysis and impact score for {company} {role}: {e}"
                    )
                try:
                    workload_data = await self._generate_auto_and_non_auto_workloads_async(
                        data={
                            "workload_table": workload_analysis_table,
                            "ai_impact_score": ai_impact_score,
                            "company_name": company,
                            "role_name": role,
                        }
                    )
                    self._cache.setex(
                        role_company_id, CACHE_EXPERATION_SECONDS, json.dumps(workload_data)
                    )
                except Exception:
                    raise Exception(
                        f"Generated a invalid workload table for {company} {role}: {workload_data}"
                    )

            except Exception as e:
                print(
                    f"While using llm to extract role metrics {role} {company}, Error:",
                    e,
                    flush=True,
                )
                traceback.print_exc()
                workload_data = [
                    {
                        "Name": "Read and write internal documents",
                        "Type": "Non-Auto",
                        "Skill": 0.3,
                        "Time": 0.2,
                        "Reason": "This is a default workload for the role",
                    },
                    {
                        "Name": "Attend meetings",
                        "Type": "Non-Auto",
                        "Skill": 0.4,
                        "Time": 0.15,
                        "Reason": "This is a default workload for the role",
                    },
                    {
                        "Name": "Basic data entry",
                        "Type": "Auto",
                        "Skill": 0.2,
                        "Time": 0.3,
                        "Reason": "This is a default workload for the role",
                    },
                    {
                        "Name": "Email correspondence",
                        "Type": "Non-Auto",
                        "Skill": 0.35,
                        "Time": 0.15,
                        "Reason": "This is a default workload for the role",
                    },
                    {
                        "Name": "Schedule appointments",
                        "Type": "Auto",
                        "Skill": 0.25,
                        "Time": 0.2,
                        "Reason": "This is a default workload for the role",
                    },
                ]

            return workload_data

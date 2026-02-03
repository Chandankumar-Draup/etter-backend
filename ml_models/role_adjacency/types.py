"""Types for role adjacency analysis."""

from typing import TypedDict, List, Optional


class RoleAdjacencyInput(TypedDict):
    """Input data for role adjacency analysis.

    Attributes:
        role: The job role to analyze.
        company: The company name for context.
        top_k: The number of top roles to return.
        description: The description of the job role.
        candidate_roles: The candidate roles to consider.
    """

    role: str
    company: str
    top_k: int
    description: Optional[str] = None
    candidate_roles: Optional[list[str]] = None


class PredictedRole(TypedDict):
    """Represents a predicted role with confidence score.

    Attributes:
        job_role: The predicted job role name.
        score: Confidence score for the prediction (0.0 to 1.0).
    """

    job_role: str
    score: float


class TitleToRoleResult(TypedDict):
    """Result containing job title and its predicted roles.

    Attributes:
        job_title: The input job title.
        predicted_roles: List of predicted roles with scores.
    """

    job_title: str
    predicted_roles: List[PredictedRole]


class TitleToRoleResponse(TypedDict):
    """API response containing title-to-role mapping results.

    Attributes:
        results: List of title-to-role mapping results.
    """

    results: List[TitleToRoleResult]
    success: bool

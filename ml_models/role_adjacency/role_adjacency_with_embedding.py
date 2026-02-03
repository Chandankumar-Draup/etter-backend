"""Role Adjacency using the Embedding Model."""

from typing import List
from openai import OpenAI
import traceback
import numpy as np

from .utils import (
    get_role_description_from_api,
    get_company_roles_and_job_descriptions,
    artificial_score_scaling,
)
from .types import RoleAdjacencyInput, PredictedRole


embedding_store = {}


def get_embedding_for_role_description(descriptions: str) -> List[float]:
    # TODO: Replace inmemory cache with better cache like redis
    inputs = []
    for description in descriptions:
        if description in embedding_store:
            continue

        inputs.append(description)

    # inputs = [description[:512] for description in descriptions]
    # model = "qwen-lora"
    if len(inputs) == 0:
        return [embedding_store[description] for description in descriptions]

    model = "/Users/avashist/Library/Caches/llama.cpp/Qwen_Qwen3-Embedding-0.6B-GGUF_Qwen3-Embedding-0.6B-Q8_0.gguf"
    # model = "hf.co/Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0"
    client = OpenAI(base_url="http://127.0.0.1:11434/v1/")
    try:
        contacted_inputs = [x[:4000] for x in inputs]
        response = client.embeddings.create(input=contacted_inputs, model=model)
    except Exception as e:
        print(inputs)
        print(traceback.format_exc())
        raise e
    for index, data in enumerate(response.data):
        embedding_store[inputs[index]] = data.embedding
    return [embedding_store[description] for description in descriptions]


def compute_embedding_similarity_scores(
    role_embedding: List[float], job_family_embeddings: List[float]
) -> float:
    """Compute the similarity score between the role embedding and the job family embeddings."""
    role_embedding = np.array(role_embedding).reshape((1, 1024))
    job_family_embeddings = np.array(job_family_embeddings)
    dot_product = np.dot(role_embedding, job_family_embeddings.T).reshape(-1)
    norm_role_embedding = np.linalg.norm(role_embedding)
    norm_job_family_embeddings = np.linalg.norm(job_family_embeddings, axis=1)

    similarity_score = dot_product / (norm_role_embedding * norm_job_family_embeddings)
    score = (similarity_score + 1) / 2
    return score


def get_similar_roles_using_embedding_model(
    data: RoleAdjacencyInput,
) -> List[PredictedRole]:
    """Get similar roles for a given role using the embedding model."""
    # query all the roles in the company and job family
    role_description = get_role_description_from_api(data["role"], data["company"])

    roles = get_company_roles_and_job_descriptions(data["company"])
    roles = list(filter(lambda x: x["role_name"] != data["role"], roles))

    # # get the embedding for the role
    job_family_descriptions = [role_description] + [role["description"] for role in roles]
    embeddings = get_embedding_for_role_description(job_family_descriptions)
    role_embedding = embeddings[0]
    job_family_embeddings = embeddings[1:]

    scores = compute_embedding_similarity_scores(role_embedding, job_family_embeddings)
    similar_roles = []
    for index, role in enumerate(roles):
        similar_roles.append(
            {
                "job_role": role["job_role"],
                "score": scores[index],
                "normalized_score": artificial_score_scaling(scores[index]),
            }
        )
    embedding_store = {}
    return [
        PredictedRole(job_role=role["job_role"], score=role["normalized_score"])
        for role in similar_roles
    ]


# def get_similar_roles_using_embedding_batch(data: RoleAdjacencyInput) -> List[TitleToRoleResult]:
#     """Get similar roles for a given role using the embedding model."""
#     # query all the roles in the company and job family
#     role_embedding = get_embedding_of_role(data["role"], data["company"], data["job_family"])
#     query_similar_roles = get_similar_roles_from_db(role_embedding)


#     similar_roles = []
#     for _, data in enumerate(query_similar_roles):
#         embedding_data = json.loads(data["content"])
#         score = (data["score"] + 1 )/2
#         similar_roles.append({
#             "job_role": embedding_data["job_role"],
#             "score": score,
#             "normalized_score": artificial_score_scaling(score)
#         })
#     embedding_store = {}
#     return similar_roles

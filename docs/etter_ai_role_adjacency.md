## Role Adjacency API

### Overview

Use this API to retrieve roles that are similar to a given role, along with a similarity score for each suggested role.

## Base URL

```
http://127.0.0.1:7071
```

## Endpoint

```
POST /api/etter/role_adjacency/{version}
```

### Path parameters
- `version`: API version to use. Supported values:
  - `v1`: Uses an external title-to-role service based on the provided role title
  - `v2`: Uses an LLM-based approach for similarity
  - `v3`: Reserved for embedding-based similarity (not currently enabled)




### Request body
Send a JSON object with the following fields:

- List
  - job_role (Required): "str"
  - company (Requried): "str"
  - top_k (Optional): int
  - candidate_roles (Optional): List[str]

##### Example
```json
[
  {
    "job_role": "Data Scientist",
    "company": "Walmart Inc.",
    "top_k": "15",
    "candidate_roles": [
      "Principal Data Engineer",
      "(USA) Manager, Advanced Analytics",
      "Manager Yield Analytics",
      "Senior Data Scientist",
      "Senior Director Data Engineering",
      "Group Director Data Architecture",
      "Director Data Engineering",
      "Manager Data Engineering",
      "Data Science Apprentice",
      "Senior Manager Member Access Platform Media Analytics and Innovation Data Scientist",
      "Data Engineer III",
      "Group Director Data Science",
      "Senior Director Data Architecture",
      "Senior Distinguished II Data Architect",
      "Director Yield Analytics",
      "Distinguished Data Engineer",
      "Staff Data Architect",
      "Data Engineer II",
      "Senior Manager Data Modeling",
      "Senior Manager Yield Analytics",
      "Senior Manager Merchandising Business Analytics",
      "Distinguished Data Architect",
      "Senior Distinguished I Data Architect",
      "Director Assortment Analytics",
      "Senior Distinguished I Data Scientist",
      "Manager Merchant Analytics",
      "Senior Data Modeler",
      "Director Data Architecture",
      "Senior Manager Data Science",
      "(USA) Data Engineer III",
      "Associate Fellow I Machine Learning Engineer",
      "Senior Analyst Merchandising Business Analytics",
      "Staff Data Engineer",
      "Director Data Science",
      "Senior Manager Data Engineering",
      "Staff Data Scientist",
      "Data Modeler III",
      "Senior Distinguished I Data Engineer",
      "Staff Data Modeler",
      "Senior Director Data Science",
      "Data Modeler II",
      "Senior Fellow Machine Learning Engineer",
      "Principal Data Scientist",
      "Fellow Machine Learning Engineer",
      "Associate Fellow II Machine Learning Engineer"
    ]
  }
]
```

### Example (cURL)

```bash
curl -X "POST" "http://127.0.0.1:7071/api/etter/role_adjacency/v2" \
        -H 'Content-Type: application/json; charset=utf-8' \
        -d $'[
  {
    "job_role": "Data Scientist",
    "company": "Walmart Inc.",
    "top_k": "15",
    "candidate_roles": [
      "Principal Data Engineer",
      "(USA) Manager, Advanced Analytics",
      "Manager Yield Analytics",
      "Senior Data Scientist",
      "Senior Director Data Engineering",
      "Group Director Data Architecture",
      "Director Data Engineering",
      "Manager Data Engineering",
      "Data Science Apprentice",
      "Senior Manager Member Access Platform Media Analytics and Innovation Data Scientist",
      "Data Engineer III",
      "Group Director Data Science",
      "Senior Director Data Architecture",
      "Senior Distinguished II Data Architect",
      "Director Yield Analytics",
      "Distinguished Data Engineer",
      "Staff Data Architect",
      "Data Engineer II",
      "Senior Manager Data Modeling",
      "Senior Manager Yield Analytics",
      "Senior Manager Merchandising Business Analytics",
      "Distinguished Data Architect",
      "Senior Distinguished I Data Architect",
      "Director Assortment Analytics",
      "Senior Distinguished I Data Scientist",
      "Manager Merchant Analytics",
      "Senior Data Modeler",
      "Director Data Architecture",
      "Senior Manager Data Science",
      "(USA) Data Engineer III",
      "Associate Fellow I Machine Learning Engineer",
      "Senior Analyst Merchandising Business Analytics",
      "Staff Data Engineer",
      "Director Data Science",
      "Senior Manager Data Engineering",
      "Staff Data Scientist",
      "Data Modeler III",
      "Senior Distinguished I Data Engineer",
      "Staff Data Modeler",
      "Senior Director Data Science",
      "Data Modeler II",
      "Senior Fellow Machine Learning Engineer",
      "Principal Data Scientist",
      "Fellow Machine Learning Engineer",
      "Associate Fellow II Machine Learning Engineer"
    ]
  }
]'
```

### Response

```json
[
  {
    "role": "Data Scientist",
    "company": "Walmart Inc.",
    "top_k": 15,
    "candidate_roles": [
      "Principal Data Engineer",
      "(USA) Manager, Advanced Analytics",
      "Manager Yield Analytics",
      "Senior Data Scientist",
      "Senior Director Data Engineering",
      "Group Director Data Architecture",
      "Director Data Engineering",
      "Manager Data Engineering",
      "Data Science Apprentice",
      "Senior Manager Member Access Platform Media Analytics and Innovation Data Scientist",
      "Data Engineer III",
      "Group Director Data Science",
      "Senior Director Data Architecture",
      "Senior Distinguished II Data Architect",
      "Director Yield Analytics",
      "Distinguished Data Engineer",
      "Staff Data Architect",
      "Data Engineer II",
      "Senior Manager Data Modeling",
      "Senior Manager Yield Analytics",
      "Senior Manager Merchandising Business Analytics",
      "Distinguished Data Architect",
      "Senior Distinguished I Data Architect",
      "Director Assortment Analytics",
      "Senior Distinguished I Data Scientist",
      "Manager Merchant Analytics",
      "Senior Data Modeler",
      "Director Data Architecture",
      "Senior Manager Data Science",
      "(USA) Data Engineer III",
      "Associate Fellow I Machine Learning Engineer",
      "Senior Analyst Merchandising Business Analytics",
      "Staff Data Engineer",
      "Director Data Science",
      "Senior Manager Data Engineering",
      "Staff Data Scientist",
      "Data Modeler III",
      "Senior Distinguished I Data Engineer",
      "Staff Data Modeler",
      "Senior Director Data Science",
      "Data Modeler II",
      "Senior Fellow Machine Learning Engineer",
      "Principal Data Scientist",
      "Fellow Machine Learning Engineer",
      "Associate Fellow II Machine Learning Engineer"
    ],
    "similar_roles": [
      {
        "job_role": "Chief Data Scientist",
        "score": 82.81
      },
      {
        "job_role": "Data Science Manager",
        "score": 82.49
      },
      {
        "job_role": "Machine Learning Scientist",
        "score": 80.24
      },
      {
        "job_role": "Data Sciences Consultant",
        "score": 78.19
      },
      {
        "job_role": "Artificial Intelligence Scientist",
        "score": 76.86
      },
      {
        "job_role": "Decision Scientist",
        "score": 75.9
      },
      {
        "job_role": "Data Science Director",
        "score": 75.75
      },
      {
        "job_role": "Applied Data Scientist - Speech",
        "score": 71.06
      },
      {
        "job_role": "NLP Scientist",
        "score": 65.46
      },
      {
        "job_role": "Modeling & Simulation Scientist",
        "score": 63.71
      },
      {
        "job_role": "Computational Biology Scientist",
        "score": 63.56
      },
      {
        "job_role": "Data Engineer",
        "score": 63.39
      },
      {
        "job_role": "Artificial Intelligence Specialist",
        "score": 62.89
      },
      {
        "job_role": "Research Scientist",
        "score": 62.75
      }
    ],
    "message": "success"
  }
]
```

### Errors

#### Complete Error
```json
{
  "status": "failure",
  "data": null,
  "errors": [
    "Invalid version: v9"
  ]
}
```

#### Partial Error
```json
[
  {
    "role": "Data Scientist",
    "company": "Walmart Inc.",
    "top_k": 5,
    "candidate_roles": [
      "Principal Data Engineer",
      "(USA) Manager, Advanced Analytics",
      "Manager Yield Analytics",
      "Senior Data Scientist",
      "Senior Director Data Engineering",
      "Group Director Data Architecture",
      "Director Data Engineering",
      "Manager Data Engineering",
      "Data Science Apprentice",
      "Senior Manager Member Access Platform Media Analytics and Innovation Data Scientist",
      "Data Engineer III",
      "Group Director Data Science",
      "Senior Director Data Architecture",
      "Senior Distinguished II Data Architect",
      "Director Yield Analytics",
      "Distinguished Data Engineer",
      "Staff Data Architect",
      "Data Engineer II",
      "Senior Manager Data Modeling",
      "Senior Manager Yield Analytics",
      "Senior Manager Merchandising Business Analytics",
      "Distinguished Data Architect",
      "Senior Distinguished I Data Architect",
      "Director Assortment Analytics",
      "Senior Distinguished I Data Scientist",
      "Manager Merchant Analytics",
      "Senior Data Modeler",
      "Director Data Architecture",
      "Senior Manager Data Science",
      "(USA) Data Engineer III",
      "Associate Fellow I Machine Learning Engineer",
      "Senior Analyst Merchandising Business Analytics",
      "Staff Data Engineer",
      "Director Data Science",
      "Senior Manager Data Engineering",
      "Staff Data Scientist",
      "Data Modeler III",
      "Senior Distinguished I Data Engineer",
      "Staff Data Modeler",
      "Senior Director Data Science",
      "Data Modeler II",
      "Senior Fellow Machine Learning Engineer",
      "Principal Data Scientist",
      "Fellow Machine Learning Engineer",
      "Associate Fellow II Machine Learning Engineer"
    ],
    "similar_roles": [
      {
        "job_role": "Principal Data Scientist",
        "score": 92.5
      },
      {
        "job_role": "Senior Data Scientist",
        "score": 91.0
      },
      {
        "job_role": "Staff Data Scientist",
        "score": 90.0
      },
      {
        "job_role": "Senior Distinguished I Data Scientist",
        "score": 89.0
      },
      {
        "job_role": "Director Data Science",
        "score": 85.0
      }
    ],
    "message": "success"
  },
  {
    "role": "Does Not Exist",
    "company": "Walmart Inc.",
    "top_k": 15,
    "candidate_roles": null,
    "message": "Failed to get role description for role: Does Not Exist in company: Walmart Inc.: Failed to get role description from api: {\"message\":\"No data found for the given company and roles.\",\"status\":\"error\"}\n",
    "similar_roles": []
  }
]
```


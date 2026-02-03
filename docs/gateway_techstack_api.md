# Gateway TechStack API Documentation

## Overview
This API integrates with the Gateway service to fetch tech stack suggestions and retrieves corresponding MasterTechStack data from the database.

## Base URL
- **Development/QA**: `http://127.0.0.1:7071/api/etter`
- **Production**: `https://your-production-domain.com/api/etter`

## Authentication
All endpoints require JWT authentication via Bearer token in the Authorization header.

---

## API Endpoints

### 1. Get TechStack Suggestions with Master Data

**Endpoint:** `POST /api/etter/techstack/suggest`

**Description:** 
Fetches tech stack product suggestions from the Gateway API based on input text and retrieves matching MasterTechStack records from the database.

**Request Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Payload:**
```json
{
  "input_text": ["google", "aws"],
  "score_limit": 0.8
}
```

**Request Payload Fields:**
- `input_text` (required, array of strings): List of input text strings to search for tech stack products
- `score_limit` (optional, float, default: 0.8): Minimum score threshold for suggestions (range: 0.0 to 1.0)

**Success Response (200 OK):**
```json
{
  "status": "success",
  "suggestions": {
    "google": [
      {
        "product": "Google (unspecified solution)",
        "score": 1.0
      },
      {
        "product": "Google Cloud Identity Platform",
        "score": 0.8
      },
      {
        "product": "Google Compute Engine",
        "score": 0.8
      },
      {
        "product": "Google Scale",
        "score": 0.8
      },
      {
        "product": "Google Pay",
        "score": 0.8
      },
      {
        "product": "Google Ads",
        "score": 0.8
      }
    ],
    "aws": [
      {
        "product": "Amazon Web Services (AWS)",
        "score": 1.0
      },
      {
        "product": "AWS Lambda",
        "score": 0.9
      },
      {
        "product": "AWS EC2",
        "score": 0.85
      }
    ]
  },
  "master_data": [
    {
      "id": 123,
      "product_name": "Google Cloud Identity Platform",
      "description": "Identity and access management platform by Google",
      "product_picture_s3_url": "https://s3.amazonaws.com/bucket/image.png",
      "g2_sub_sub_category_3": "Identity Management"
    },
    {
      "id": 124,
      "product_name": "Google Compute Engine",
      "description": "Infrastructure as a Service platform",
      "product_picture_s3_url": "https://s3.amazonaws.com/bucket/image2.png",
      "g2_sub_sub_category_3": "Cloud Infrastructure"
    },
    {
      "id": 125,
      "product_name": "Amazon Web Services (AWS)",
      "description": "Comprehensive cloud computing platform",
      "product_picture_s3_url": "https://s3.amazonaws.com/bucket/aws.png",
      "g2_sub_sub_category_3": "Cloud Platforms"
    }
  ]
}
```

**Response Fields:**
- `status` (string): Response status ("success" or "failure")
- `suggestions` (object): Dictionary where keys are input text values and values are arrays of product suggestions
  - `product` (string): Product name from Gateway API
  - `score` (float): Relevance score (0.0 to 1.0)
- `master_data` (array): Array of MasterTechStack records matching the suggested products
  - `id` (integer): Primary key from MasterTechStack table
  - `product_name` (string, nullable): Product name
  - `description` (string, nullable): Product description
  - `product_picture_s3_url` (string, nullable): S3 URL for product image
  - `g2_sub_sub_category_3` (string, nullable): G2 category classification

**Error Responses:**

**400 Bad Request** - Gateway API returned an error:
```json
{
  "status": "failure",
  "data": null,
  "errors": ["Gateway API returned error: Invalid input"]
}
```

**401 Unauthorized** - Missing or invalid JWT token:
```json
{
  "status": "failure",
  "data": null,
  "errors": ["Not authenticated"]
}
```

**500 Internal Server Error** - Server error:
```json
{
  "status": "failure",
  "data": null,
  "errors": ["Failed to fetch techstack suggestions: <error_message>"]
}
```

---

## Example Usage

### cURL Example
```bash
curl -X POST "http://127.0.0.1:7071/api/etter/techstack/suggest" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": ["google", "microsoft"],
    "score_limit": 0.8
  }'
```

### Python Example (using requests)
```python
import requests

url = "http://127.0.0.1:7071/api/etter/techstack/suggest"
headers = {
    "Authorization": "Bearer <your_jwt_token>",
    "Content-Type": "application/json"
}
payload = {
    "input_text": ["google", "microsoft"],
    "score_limit": 0.8
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### JavaScript Example (using fetch)
```javascript
const url = 'http://127.0.0.1:7071/api/etter/techstack/suggest';
const payload = {
  input_text: ['google', 'microsoft'],
  score_limit: 0.8
};

fetch(url, {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <your_jwt_token>',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
})
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

---

## Environment Configuration

The API automatically selects the Gateway URL based on the environment:

- **Production**: `https://gateway.draup.technology/api`
- **QA/Development**: `https://gateway-qa.draup.technology/api`

**Required Environment Variable:**
- `GATEWAY_TOKEN`: Authentication token for Gateway API

---

---

## TechStack Taxonomy APIs

These APIs manage tech stack taxonomy records for companies. All endpoints are under `/api/extraction/tech_stack_taxonomy/`.

### 1. Get TechStack Taxonomy by Company

**Endpoint:** `GET /api/extraction/tech_stack_taxonomy/company/{company_id}`

**Description:** 
Retrieves paginated list of tech stack taxonomy records for a specific company with optional filtering.

**Request Parameters:**
- `company_id` (path, required): Company ID
- `page` (query, optional, default: 1): Page number
- `page_size` (query, optional, default: 300): Items per page
- `status` (query, optional): Filter by status (pending, approved, rejected, review)
- `tech_stack_name` (query, optional): Filter by tech stack name (partial match)

**Request Example:**
```bash
GET /api/extraction/tech_stack_taxonomy/company/123?page=1&page_size=50&status=pending&tech_stack_name=google
```

**Success Response (200 OK):**
```json
{
  "data": [
    {
      "id": 1,
      "company_id": 123,
      "tech_stack_name": "Google Cloud Platform",
      "description": "Cloud computing platform",
      "image_link": "https://example.com/image.png",
      "category": "Cloud Infrastructure",
      "tech_stack_product_name": "Google Cloud Platform",
      "status": "pending",
      "approver_username": null,
      "user_username": "john.doe",
      "modified_by_username": "john.doe",
      "modified_on": "2024-01-15T10:30:00",
      "created_on": "2024-01-15T10:00:00"
    }
  ],
  "total_count": 1,
  "pending_count": 1,
  "page": 1,
  "page_size": 50,
  "total_pages": 1,
  "has_next": false,
  "has_prev": false
}
```

---

### 2. Bulk Upsert TechStack Taxonomy

**Endpoint:** `POST /api/extraction/tech_stack_taxonomy/bulk_upsert`

**Description:** 
Creates or updates multiple tech stack taxonomy records in a single request.

**Request Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Payload:**
```json
{
  "items": [
    {
      "id": null,
      "tech_stack_name": "AWS Lambda",
      "description": "Serverless compute service",
      "image_link": "https://example.com/aws-lambda.png",
      "category": "Cloud Computing",
      "tech_stack_id": 456,
      "status": "pending",
      "user_username": "john.doe",
      "approver_username": null,
      "modified_by_username": "john.doe"
    },
    {
      "id": 1,
      "tech_stack_name": "Google Cloud Platform",
      "description": "Updated description",
      "category": "Cloud Infrastructure",
      "status": "pending"
    }
  ],
  "force_update": false,
  "force_upload": false
}
```

**Request Payload Fields:**
- `items` (required, array): List of tech stack taxonomy items
  - `id` (optional): Record ID for updates (omit for new records)
  - `tech_stack_name` (required): Name of the tech stack
  - `description` (optional): Description
  - `image_link` (optional): URL to product image
  - `category` (optional): Category name (will lookup/create in master table)
  - `tech_stack_id` (optional): Reference to MasterTechStack.id
  - `status` (optional, default: "pending"): Status (pending, approved, rejected, review)
  - `user_username` (optional): Username of the user who created the record
  - `approver_username` (optional): Username of the approver
  - `modified_by_username` (optional): Username of the modifier
- `force_update` (optional, default: false): Create master table entries if they don't exist
- `force_upload` (optional, default: false): Same as force_update

**Success Response (200 OK):**
```json
{
  "status": "success",
  "data": [
    {
      "id": 2,
      "company_id": 123,
      "tech_stack_name": "AWS Lambda",
      "description": "Serverless compute service",
      "image_link": "https://example.com/aws-lambda.png",
      "category": "Cloud Computing",
      "tech_stack_product_name": "AWS Lambda",
      "status": "pending",
      "approver_username": null,
      "user_username": "john.doe",
      "modified_by_username": "john.doe",
      "modified_on": "2024-01-15T11:00:00",
      "created_on": "2024-01-15T11:00:00"
    },
    {
      "id": 1,
      "company_id": 123,
      "tech_stack_name": "Google Cloud Platform",
      "description": "Updated description",
      "category": "Cloud Infrastructure",
      "status": "pending",
      "modified_by_username": "john.doe",
      "modified_on": "2024-01-15T11:00:00",
      "created_on": "2024-01-15T10:00:00"
    }
  ],
  "total_count": 2,
  "created_count": 1,
  "updated_count": 1,
  "errors": []
}
```

---

### 3. Bulk Approve TechStack Taxonomy

**Endpoint:** `POST /api/extraction/tech_stack_taxonomy/bulk_approve`

**Description:** 
Bulk update the status of multiple tech stack taxonomy records.

**Request Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Payload:**
```json
{
  "ids": [1, 2, 3],
  "status": "approved"
}
```

**Request Payload Fields:**
- `ids` (required, array of integers): List of tech stack taxonomy record IDs
- `status` (optional, default: "approved"): Status to set (pending, approved, rejected, review)

**Success Response (200 OK):**
```json
{
  "status": "success",
  "approved_count": 3,
  "errors": [],
  "message": "Approved 3 tech stack taxonomy record(s)"
}
```

**Partial Success Response:**
```json
{
  "status": "partial_success",
  "approved_count": 2,
  "errors": ["tech stack taxonomy records not found: 3"],
  "message": "Approved 2 tech stack taxonomy record(s)"
}
```

---

### 4. Delete TechStack Taxonomy

**Endpoint:** `DELETE /api/extraction/tech_stack_taxonomy/{tech_stack_taxonomy_id}`

**Description:** 
Permanently deletes a tech stack taxonomy record by ID.

**Request Headers:**
```
Authorization: Bearer <your_jwt_token>
```

**Request Example:**
```bash
DELETE /api/extraction/tech_stack_taxonomy/1
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "tech stack taxonomy record 1 deleted successfully",
  "deleted_id": 1
}
```

**Error Response (404 Not Found):**
```json
{
  "status": "failure",
  "data": null,
  "errors": ["tech stack taxonomy record with ID 1 not found"]
}
```

---

## Notes

### Gateway TechStack Suggest API:
1. The API performs a case-insensitive partial match search on `product_name` in the MasterTechStack table
2. Multiple input texts can be provided, and suggestions will be grouped by input text
3. The `master_data` array contains all matching records from the database, which may include duplicates if multiple suggested products match the same database record
4. The score_limit parameter filters suggestions at the Gateway API level before database lookup
5. If no matching MasterTechStack records are found, the `master_data` array will be empty

### TechStack Taxonomy APIs:
1. All taxonomy endpoints require authentication via JWT token
2. The `category` field in bulk upsert will lookup/create entries in the `MasterTechStackCategory` table
3. The `tech_stack_id` field can reference `MasterTechStack.id` to link taxonomy records to master products
4. Status values: `pending`, `approved`, `rejected`, `review`
5. When `force_update` or `force_upload` is true, missing master table entries (like categories) will be automatically created
6. Username fields (`user_username`, `approver_username`, `modified_by_username`) are resolved to user IDs internally
7. Records are uniquely identified by `company_id` + `tech_stack_name` combination

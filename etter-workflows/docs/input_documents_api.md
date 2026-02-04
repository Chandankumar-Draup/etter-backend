# INPUT API Reference

Quick reference for three read-focused APIs: document listing/retrieval, role taxonomy, and document extraction data.

All endpoints sit under the base path `/api`. Authentication is required on every endpoint — pass a valid Bearer token in the `Authorization` header.

---

## 1. Documents — List & Retrieve

### 1a. List documents

Returns a paginated list of documents for the authenticated user's tenant. Filter by company instance and/or role.

```
GET /api/documents/
Authorization: Bearer <token>
```

#### Query parameters

| Parameter              | Type    | Required | Default | Description                                                                 |
|------------------------|---------|----------|---------|-----------------------------------------------------------------------------|
| `roles`                | string  | No       | —       | Comma-separated role names. Only documents whose `roles` array contains **all** listed values are returned. |
| `company_instance_name`| string  | No       | —       | Filter to a specific company instance.                                      |
| `status`               | string  | No       | —       | Document status: `planned`, `uploaded`, `ready`, `deleted`, `quarantine`, `aborted`. |
| `limit`                | integer | No       | 100     | Max documents to return (1–1000).                                           |
| `offset`               | integer | No       | 0       | Number of documents to skip (for pagination).                              |

#### Response — `200 OK`

```json
{
  "status": "success",
  "data": {
    "documents": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "tenant_id": "company-tenant-id",
        "roles": ["Engineer", "Manager"],
        "status": "ready",
        "original_filename": "job_description.pdf",
        "declared_size_bytes": 45678,
        "observed_size_bytes": 45678,
        "declared_content_type": "application/pdf",
        "observed_content_type": "application/pdf",
        "created_by": "user-uuid",
        "created_at": "2025-01-15T10:30:00Z",
        "completed_at": "2025-01-15T10:31:00Z",
        "custom_metadata": null,
        "legal_hold": false,
        "upload_mode": "ROLE_BASED",
        "folder_path": null
      }
    ],
    "count": 1,
    "limit": 100,
    "offset": 0
  }
}
```

---

### 1b. Get a single document by ID

Returns metadata for one document. Pass `generate_download_url=true` to get a presigned S3 URL (valid for 5 minutes).

```
GET /api/documents/{document_id}?generate_download_url=true
Authorization: Bearer <token>
```

#### Path parameters

| Parameter     | Type | Required | Description                          |
|---------------|------|----------|--------------------------------------|
| `document_id` | UUID | Yes      | The document ID to retrieve.         |

#### Query parameters

| Parameter              | Type    | Required | Default | Description                                                  |
|------------------------|---------|----------|---------|--------------------------------------------------------------|
| `generate_download_url`| boolean | No       | `false` | When `true`, includes a presigned download URL in the response. |

#### Response — `200 OK`

```json
{
  "document": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "company-tenant-id",
    "roles": ["Engineer"],
    "status": "ready",
    "original_filename": "job_description.pdf",
    "declared_size_bytes": 45678,
    "observed_size_bytes": 45678,
    "declared_content_type": "application/pdf",
    "observed_content_type": "application/pdf",
    "created_by": "user-uuid",
    "created_at": "2025-01-15T10:30:00Z",
    "completed_at": "2025-01-15T10:31:00Z",
    "custom_metadata": null,
    "legal_hold": false,
    "upload_mode": "ROLE_BASED",
    "folder_path": null
  },
  "download": {
    "url": "https://s3.amazonaws.com/bucket/...presigned...",
    "expires_in": 300
  }
}
```

`download` is `null` when `generate_download_url` is `false`.

---

## 2. Role Taxonomy — List

Returns a paginated list of role taxonomy records for a company. All text filters (`job_family`, `occupation`, `job_title`) are case-insensitive partial matches.

```
GET /api/taxonomy/roles?company_id=<id>
Authorization: Bearer <token>
```

#### Query parameters

| Parameter        | Type    | Required | Default | Description                                                                 |
|------------------|---------|----------|---------|-----------------------------------------------------------------------------|
| `company_id`     | integer | **Yes**  | —       | Company ID to retrieve taxonomy for. Must match the authenticated user's company. |
| `approval_status`| string  | No       | —       | Filter by status: `pending`, `approved`, `rejected`.                        |
| `job_family`     | string  | No       | —       | Partial match on job family (e.g. `"Eng"` matches `"Engineering"`).        |
| `occupation`     | string  | No       | —       | Partial match on occupation.                                                |
| `job_title`      | string  | No       | —       | Partial match on job title.                                                 |
| `source`         | string  | No       | —       | Exact match on source (e.g. `"User"`, `"Draup"`).                          |
| `page`           | integer | No       | 1       | Page number.                                                                |
| `page_size`      | integer | No       | 50      | Items per page (max 200).                                                   |

#### Response — `200 OK`

Results are ordered by `job_family` ascending, then `created_on` descending.

```json
{
  "status": "success",
  "data": [
    {
      "id": 1234,
      "job_id": "JOB-001",
      "job_role": "Software Engineer",
      "job_title": "Senior Software Engineer",
      "occupation": "Technology",
      "job_family": "Engineering",
      "job_level": "Senior",
      "job_track": "IC",
      "management_level": null,
      "pay_grade": "L4",
      "draup_role": "Software Engineer",
      "skills": ["Python", "AWS", "System Design"],
      "approval_status": "approved",
      "source": "User",
      "created_on": "2025-01-10T08:00:00Z",
      "modified_on": "2025-01-12T09:30:00Z"
    }
  ],
  "total_count": 42,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

---
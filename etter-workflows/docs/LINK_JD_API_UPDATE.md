# API Update: link-job-description Endpoint

## Endpoint
```
POST /api/automated_workflows/link-job-description
```

## Current Issue
The endpoint currently expects `jd_content` (inline text), but the workflow now also sends `jd_uri` (S3 presigned URL) for documents from the QA API.

## Updated Request Payload

```json
{
  "company_role_id": "c242defe4f32a6574a1abbddafe16a6a",
  "jd_content": null,
  "jd_uri": "https://draup-etter.s3.amazonaws.com/qa/79004/documents/Pharmacist_JD.pdf?X-Amz-Algorithm=...",
  "jd_title": "Pharmacist",
  "jd_metadata": {
    "document_id": "0c95f236-d557-43d5-9b0b-30be3c55c762",
    "download_url": "https://draup-etter.s3.amazonaws.com/...",
    "status": "ready",
    "roles": ["Pharmacist"],
    "content_type": "application/pdf",
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-20T14:45:00Z",
    "expires_at": "2026-02-05T00:00:00Z"
  },
  "format_with_llm": true,
  "source": "self_service_pipeline"
}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_role_id` | string | Yes | CompanyRole ID to link JD to |
| `jd_content` | string | No* | Inline JD text content |
| `jd_uri` | string | No* | S3 presigned URL to download JD |
| `jd_title` | string | No | Title/name for the JD |
| `jd_metadata` | object | No | Document metadata from QA API |
| `format_with_llm` | boolean | No | Format JD with LLM (default: true) |
| `source` | string | No | Source identifier |

*Either `jd_content` OR `jd_uri` must be provided.

## Logic to Implement

```python
def link_job_description(request):
    jd_content = request.get("jd_content")
    jd_uri = request.get("jd_uri")

    # If no inline content but URI provided, download it
    if not jd_content and jd_uri:
        jd_content = download_and_extract(jd_uri)

    if not jd_content:
        return {"status": "error", "message": "No JD content available"}

    # Continue with existing logic...
```

## download_and_extract Function

```python
import requests
import io

def download_and_extract(url: str) -> str:
    """Download document from URL and extract text content."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")

    # Handle PDF
    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        import PyPDF2
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text_parts = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        return "\n\n".join(text_parts)

    # Handle text
    return response.text
```

## Expected Response

```json
{
  "status": "success",
  "jd_linked": true,
  "jd_content_length": 2500,
  "formatted": true,
  "company_role_id": "c242defe4f32a6574a1abbddafe16a6a"
}
```

## Error Response (400)

```json
{
  "status": "error",
  "message": "Either jd_content or jd_uri must be provided"
}
```

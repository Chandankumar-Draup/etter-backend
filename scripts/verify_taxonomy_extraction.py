"""
Taxonomy Extraction - Full Flow Script

This script handles the complete taxonomy extraction flow:
1. Upload Excel/CSV file to S3
2. Get document_id from upload response
3. Call taxonomy extraction endpoint
4. Display results

Fill in the constants below before running.
"""

import os
import json
import requests
from typing import Dict, Any, Optional

# =============================================================================
# CONFIGURATION - Fill these in
# =============================================================================

# API base URL (etter-backend)
BASE_URL = "http://localhost:7071"

# Authentication token (Bearer token from login)
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MzYzOCwiZXhwIjoxNzcwOTY2NTE4LCJqdGkiOiJmMDJkMTExNC0xYzg0LTRhOTgtODkyZS1iOWFjYjE0ODAwZjYifQ.InD_F_1TDxBizbnWSTz6mtRCCIkDbUF6sHYkW61I0mU"

# Company ID for upsert/conflict detection
COMPANY_ID = '79008'

# =============================================================================
# OPTION 1: Provide file path for full flow (upload + extract)
# =============================================================================
FILE_PATH = "/Users/eashvrudhula/Downloads/Draup_Leonardo_Platform Customization + Mapping_13Jan2026.xlsx"

# =============================================================================
# OPTION 2: Provide existing document_id (skip upload)
# =============================================================================
EXISTING_DOCUMENT_ID = None  # Set to UUID string to skip upload

# =============================================================================
# EXTRACTION SETTINGS
# =============================================================================
TAXONOMY_TYPE = "role"  # "role", "skill", or "tech_stack"
PREVIEW_ONLY = True     # Set to False to actually upsert data
SHEET_NAME = None       # Optional: sheet name for Excel files


# =============================================================================
# FILE UPLOAD
# =============================================================================

def upload_file(file_path: str) -> Optional[str]:
    """
    Upload a file to S3 and return the document_id.
    
    Uses the combined upload endpoint for simplicity.
    
    Args:
        file_path: Path to the file to upload
        
    Returns:
        document_id (UUID string) if successful, None otherwise
    """
    url = f"{BASE_URL}/api/uploads/upload"
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    
    # Check file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None
    
    filename = os.path.basename(file_path)
    
    print(f"\n{'='*60}")
    print(f"STEP 1: Uploading file")
    print(f"{'='*60}")
    print(f"File: {filename}")
    print(f"Path: {file_path}")
    print(f"Size: {os.path.getsize(file_path):,} bytes")
    
    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': (filename, f, 'application/octet-stream')
            }
            data = {
                'role': 'taxonomy_extraction'  # Role for document categorization
            }
            
            response = requests.post(
                url, 
                headers=headers, 
                files=files, 
                data=data,
                timeout=60
            )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            document_id = result.get("document_id")
            print(f"✓ Upload successful!")
            print(f"  Document ID: {document_id}")
            print(f"  Status: {result.get('status')}")
            return document_id
        else:
            print(f"✗ Upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Exception during upload: {e}")
        return None


# =============================================================================
# TAXONOMY EXTRACTION
# =============================================================================

def extract_taxonomy(
    document_id: str,
    taxonomy_type: str = "role",
    preview_only: bool = True,
    sheet_name: Optional[str] = None,
    user_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Call the taxonomy extraction endpoint.
    
    Args:
        document_id: UUID of the uploaded Excel/CSV file
        taxonomy_type: 'role', 'skill', or 'tech_stack'
        preview_only: If True, returns mapping without upserting
        sheet_name: Sheet name for Excel files (optional)
        user_mapping: Override LLM mapping for specific columns
    
    Returns:
        API response as dict
    """
    url = f"{BASE_URL}/extraction/taxonomy/extract"
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "document_id": document_id,
        "taxonomy_type": taxonomy_type,
        "preview_only": preview_only,
        "company_id": COMPANY_ID
    }
    
    if sheet_name:
        payload["sheet_name"] = sheet_name
    
    if user_mapping:
        payload["user_mapping"] = user_mapping
    
    print(f"\n{'='*60}")
    print(f"STEP 2: Extracting taxonomy")
    print(f"{'='*60}")
    print(f"Document ID: {document_id}")
    print(f"Taxonomy Type: {taxonomy_type}")
    print(f"Preview Only: {preview_only}")
    if sheet_name:
        print(f"Sheet Name: {sheet_name}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print_extraction_result(result)
            return result
        else:
            print(f"✗ Extraction failed: {response.text}")
            return {"error": response.text, "status_code": response.status_code}
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out")
        return {"error": "timeout"}
    except Exception as e:
        print(f"✗ Exception: {e}")
        return {"error": str(e)}


def print_extraction_result(result: Dict[str, Any]):
    """Pretty print the extraction result."""
    print(f"\n{'='*60}")
    print(f"EXTRACTION RESULTS")
    print(f"{'='*60}")
    
    status = result.get('status')
    if status == "success":
        print(f"✓ Status: {status}")
    else:
        print(f"✗ Status: {status}")
        if result.get('error'):
            print(f"  Error: {result.get('error')}")
        return
    
    print(f"Taxonomy Type: {result.get('taxonomy_type')}")
    print(f"Execution Time: {result.get('execution_time', 0):.2f}s")
    
    # Mapping results
    mapping = result.get("mapping", {})
    print(f"\n--- Column Mappings ---")
    column_mappings = mapping.get("column_mappings", {})
    if column_mappings:
        for col, field in column_mappings.items():
            print(f"  • {col} → {field}")
    else:
        print("  (no mappings found)")
    
    unmapped = mapping.get("unmapped_columns", [])
    if unmapped:
        print(f"\n  Unmapped Columns: {', '.join(unmapped)}")
    
    missing = mapping.get("required_fields_missing", [])
    if missing:
        print(f"\n  ⚠ Missing Required Fields: {', '.join(missing)}")
    
    confidence = mapping.get('confidence', 0)
    print(f"\n  Confidence: {confidence:.2%}")
    
    warnings = mapping.get("warnings", [])
    if warnings:
        print(f"\n  Warnings:")
        for w in warnings:
            print(f"    ⚠ {w}")
    
    # Validation results
    validation = result.get("validation")
    if validation:
        print(f"\n--- Validation ---")
        print(f"  Total Rows: {validation.get('total_rows')}")
        print(f"  Valid Rows: {validation.get('valid_rows')}")
        
        dupes = validation.get("duplicates_in_document", [])
        if dupes:
            print(f"  ⚠ Duplicates Found: {len(dupes)}")
            for d in dupes[:3]:  # Show first 3
                print(f"    - Row {d.get('row_number')}: {d.get('duplicate_key')}")
        
        conflicts = validation.get("conflicts_with_database", [])
        if conflicts:
            print(f"  ⚠ DB Conflicts: {len(conflicts)}")
        
        errors = validation.get("validation_errors", [])
        if errors:
            print(f"  ✗ Validation Errors: {len(errors)}")
            for e in errors[:3]:  # Show first 3
                print(f"    - Row {e.get('row_number')}: {e.get('error')}")
    
    # Transformed data preview
    transformed = result.get("transformed_data")
    if transformed:
        print(f"\n--- Transformed Data Preview ---")
        print(f"  Total Records: {len(transformed)}")
        if transformed:
            print(f"  Fields: {list(transformed[0].keys())}")
            print(f"\n  First 3 records:")
            for i, rec in enumerate(transformed[:3], 1):
                # Show first few fields
                preview = {k: v for k, v in list(rec.items())[:4]}
                print(f"    {i}. {preview}")
    
    # Upsert results
    upsert = result.get("upsert_result")
    if upsert:
        print(f"\n--- Upsert Result ---")
        print(f"  Status: {upsert.get('status')}")
        print(f"  Created: {upsert.get('created_count', 0)}")
        print(f"  Updated: {upsert.get('updated_count', 0)}")
        if upsert.get('errors'):
            print(f"  Errors: {len(upsert.get('errors'))}")


# =============================================================================
# FULL FLOW
# =============================================================================

def run_full_flow(
    file_path: Optional[str] = None,
    document_id: Optional[str] = None,
    taxonomy_type: str = "role",
    preview_only: bool = True,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the complete taxonomy extraction flow.
    
    Either provide file_path (will upload) or document_id (skip upload).
    
    Args:
        file_path: Path to Excel/CSV file (optional if document_id provided)
        document_id: Existing document_id (optional if file_path provided)
        taxonomy_type: 'role', 'skill', or 'tech_stack'
        preview_only: If True, only preview without upserting
        sheet_name: Sheet name for Excel files (optional)
    
    Returns:
        Extraction result
    """
    print("\n" + "="*70)
    print("TAXONOMY EXTRACTION - FULL FLOW")
    print("="*70)
    print(f"Base URL: {BASE_URL}")
    print(f"Company ID: {COMPANY_ID}")
    print(f"Taxonomy Type: {taxonomy_type}")
    print(f"Preview Only: {preview_only}")
    
    # Step 1: Get document_id (upload if needed)
    if document_id:
        print(f"\nUsing existing document_id: {document_id}")
    elif file_path:
        document_id = upload_file(file_path)
        if not document_id:
            return {"error": "Upload failed"}
    else:
        print("\n✗ Error: Must provide either file_path or document_id")
        return {"error": "No file_path or document_id provided"}
    
    # Step 2: Extract taxonomy
    result = extract_taxonomy(
        document_id=document_id,
        taxonomy_type=taxonomy_type,
        preview_only=preview_only,
        sheet_name=sheet_name
    )
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Document ID: {document_id}")
    print(f"Status: {result.get('status', 'error')}")
    
    if result.get('mapping'):
        confidence = result['mapping'].get('confidence', 0)
        num_mappings = len(result['mapping'].get('column_mappings', {}))
        print(f"Mappings: {num_mappings} columns mapped (confidence: {confidence:.2%})")
    
    if result.get('validation'):
        valid = result['validation'].get('valid_rows', 0)
        total = result['validation'].get('total_rows', 0)
        print(f"Rows: {valid}/{total} valid")
    
    return result


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Determine which mode to use
    if EXISTING_DOCUMENT_ID:
        # Use existing document
        result = run_full_flow(
            document_id=EXISTING_DOCUMENT_ID,
            taxonomy_type=TAXONOMY_TYPE,
            preview_only=PREVIEW_ONLY,
            sheet_name=SHEET_NAME
        )
    elif FILE_PATH and os.path.exists(FILE_PATH):
        # Upload and extract
        result = run_full_flow(
            file_path=FILE_PATH,
            taxonomy_type=TAXONOMY_TYPE,
            preview_only=PREVIEW_ONLY,
            sheet_name=SHEET_NAME
        )
    else:
        print("\n" + "="*70)
        print("CONFIGURATION REQUIRED")
        print("="*70)
        print("\nPlease configure one of the following:")
        print("\n1. FILE_PATH - Path to Excel/CSV file for upload + extraction")
        print(f"   Current: {FILE_PATH}")
        print("\n2. EXISTING_DOCUMENT_ID - UUID of already uploaded document")
        print(f"   Current: {EXISTING_DOCUMENT_ID}")
        print("\nAlso set:")
        print(f"   AUTH_TOKEN: {AUTH_TOKEN[:20]}..." if len(AUTH_TOKEN) > 20 else f"   AUTH_TOKEN: {AUTH_TOKEN}")
        print(f"   COMPANY_ID: {COMPANY_ID}")
        print(f"   TAXONOMY_TYPE: {TAXONOMY_TYPE}")

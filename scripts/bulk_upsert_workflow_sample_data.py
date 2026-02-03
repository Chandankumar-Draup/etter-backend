#!/usr/bin/env python3
import requests
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

QA_URL = "https://qa-etter.draup.technology/api/etter/workflow_builder_sample_data/bulk_upsert"
PROD_URL = "https://etter.draup.com/api/etter/workflow_builder_sample_data/bulk_upsert"

def read_json_file(file_path: Path) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_items_from_json(data: Dict[str, Any]) -> tuple:
    items = []
    company_name = data.get("company_name", "")
    function_areas = data.get("function_areas", [])
    
    for function_area in function_areas:
        high_level_func = function_area.get("high_level_func")
        sub_level_func = function_area.get("sub_level_func")
        
        if not high_level_func or not sub_level_func:
            continue
        
        item = {
            "high_level_func": high_level_func,
            "sub_level_func": sub_level_func,
            "is_global": True,
            "data": data
        }
        items.append(item)
    
    return company_name, items

def make_api_call(url: str, payload: Dict[str, Any], headers: Dict[str, str], file_name: str) -> tuple:
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        status_code = response.status_code
        
        try:
            response_data = response.json()
        except:
            response_data = {"text": response.text}
        
        return status_code, response_data, None
    except requests.exceptions.RequestException as e:
        return None, None, str(e)

def process_folder(folder_path: str, environment: str, auth_token: str):
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist")
        sys.exit(1)
    
    if not folder.is_dir():
        print(f"Error: '{folder_path}' is not a directory")
        sys.exit(1)
    
    json_files = list(folder.glob("*.json"))
    
    if not json_files:
        print(f"Warning: No JSON files found in '{folder_path}'")
        return
    
    url = QA_URL if environment.lower() == "qa" else PROD_URL
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    print(f"Processing {len(json_files)} JSON file(s) from '{folder_path}'")
    print(f"Environment: {environment.upper()}")
    print(f"API URL: {url}")
    print("-" * 80)
    
    success_count = 0
    failure_count = 0
    
    for json_file in json_files:
        print(f"\nProcessing: {json_file.name}")
        
        try:
            data = read_json_file(json_file)
            company_name, items = extract_items_from_json(data)
            
            if not items:
                print(f"  ⚠️  Skipped: No valid function_areas found in {json_file.name}")
                failure_count += 1
                continue
            
            if not company_name:
                print(f"  ⚠️  Warning: No company_name found, using empty string")
            
            payload = {
                "company_name": company_name,
                "items": items
            }
            
            print(f"  Company: {company_name}")
            print(f"  Items: {len(items)}")
            
            status_code, response_data, error = make_api_call(url, payload, headers, json_file.name)
            
            if error:
                print(f"  ❌ Error: {error}")
                failure_count += 1
            elif status_code and 200 <= status_code < 300:
                print(f"  ✅ Success: Status {status_code}")
                if response_data:
                    status = response_data.get("status", "unknown")
                    print(f"     Response status: {status}")
                success_count += 1
            else:
                print(f"  ❌ Failed: Status {status_code}")
                if response_data:
                    errors = response_data.get("errors", [])
                    if errors:
                        print(f"     Errors: {errors}")
                    else:
                        print(f"     Response: {response_data}")
                failure_count += 1
        
        except json.JSONDecodeError as e:
            print(f"  ❌ Error: Invalid JSON in {json_file.name}: {str(e)}")
            failure_count += 1
        except Exception as e:
            print(f"  ❌ Error processing {json_file.name}: {str(e)}")
            failure_count += 1
    
    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Total files: {len(json_files)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failure_count}")
    print("=" * 80)

def main():
    DEFAULT_FOLDER = "..."
    
    if len(sys.argv) < 3:
        print("Usage: python bulk_upsert_workflow_sample_data.py <environment> <auth_token> [folder_path]")
        print("  environment: 'qa' or 'prod'")
        print("  auth_token: Bearer token for authentication")
        print("  folder_path: (Optional) Path to folder containing JSON files")
        print(f"              Default: {DEFAULT_FOLDER}")
        print("\nExample:")
        print("  python bulk_upsert_workflow_sample_data.py qa <token>")
        print("\nWith custom folder:")
        print("  python bulk_upsert_workflow_sample_data.py qa <token> /path/to/folder")
        sys.exit(1)
    
    environment = sys.argv[1]
    auth_token = sys.argv[2]
    folder_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_FOLDER
    
    if environment.lower() not in ["qa", "prod"]:
        print("Error: Environment must be 'qa' or 'prod'")
        sys.exit(1)
    
    process_folder(folder_path, environment, auth_token)

if __name__ == "__main__":
    main()


# cd /Users/prsairahul/etter-be && python3 scripts/bulk_upsert_workflow_sample_data.py qa "<token>"
# cd /Users/prsairahul/etter-be && python3 scripts/bulk_upsert_workflow_sample_data.py prod "<token>"
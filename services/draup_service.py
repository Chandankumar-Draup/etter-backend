"""
Draup Platform Service

Utility functions for interacting with Draup platform APIs.
"""

import os
import logging
from typing import Optional, Dict, List

import httpx
from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


async def get_company_id_by_name(company_name: str, token: str = None) -> Optional[int]:
    """
    Get Draup company/account ID by company name using universe search API.
    
    Uses DRAUP_PLATFORM_TOKEN environment variable for authentication.
    Always hits production platform URL.
    
    Args:
        company_name: Company name to search for
        token: Deprecated, not used (kept for backward compatibility)
        
    Returns:
        Company ID as integer, or None if not found
        
    Example:
        >>> company_id = await get_company_id_by_name("NVIDIA")
        >>> print(company_id)  # 236748
    """
    # Get Draup platform token from environment
    platform_token = os.environ.get('DRAUP_PLATFORM_TOKEN')
    if not platform_token:
        logger.error("DRAUP_PLATFORM_TOKEN environment variable not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Draup platform token not configured"
        )
    
    # Always use production URL
    url = "https://platform.draup.com/datasub/universe/search/"
    headers = {
        "Authorization": f"Bearer {platform_token}",
        "Content-Type": "application/json",
        "product-id": "4",
        "accept": "application/json"
    }
    payload = {
        "type": "universe",
        "search_key": company_name
    }
    
    logger.info(f"Searching for company '{company_name}' at {url}")
    logger.debug(f"Request payload: {payload}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            # Log response details before raising for debugging
            logger.debug(f"Response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            items = data.get("data", [])
            
            if items and len(items) > 0:
                account_id = items[0].get("id")
                if account_id is not None:
                    logger.info(f"Found account ID for '{company_name}': {account_id}")
                    return int(account_id)
            
            logger.warning(f"No account ID found for company: {company_name}")
            return None
            
    except httpx.TimeoutException:
        logger.error(f"Timeout searching for company: {company_name}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code} error for '{company_name}'")
        logger.error(f"Response body: {e.response.text}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"HTTP error searching for company '{company_name}': {str(e)}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error parsing account ID response for '{company_name}': {str(e)}")
        return None


async def search_companies(query: str, limit: int = 10, token: Optional[str] = None) -> List[Dict]:
    """
    Search for companies in Draup universe and return multiple matches.
    
    Args:
        query: Search query (company name or partial name)
        limit: Maximum number of results to return (default: 10)
        token: Optional bearer token. If not provided, uses DRAUP_PLATFORM_TOKEN env var
        
    Returns:
        List of company dictionaries with 'id' and 'name' fields
        
    Example:
        >>> companies = await search_companies("nvidia", limit=5)
        >>> for company in companies:
        ...     print(f"{company['name']}: {company['id']}")
    """
    auth_token = token or os.environ.get('DRAUP_PLATFORM_TOKEN')
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Draup platform token not configured"
        )
    
    url = "https://platform.draup.com/datasub/universe/search/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    payload = {
        "type": "universe",
        "search_key": query
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("data", [])
            
            # Extract and format results
            results = []
            for item in items[:limit]:
                company_id = item.get("id")
                company_name = item.get("name") or item.get("company_name")
                
                if company_id and company_name:
                    results.append({
                        "id": int(company_id),
                        "name": company_name,
                        "raw_data": item  # Include full data for additional fields if needed
                    })
            
            logger.info(f"Found {len(results)} companies matching '{query}'")
            return results
            
    except httpx.TimeoutException:
        logger.error(f"Timeout searching for companies with query: {query}")
        return []
    except httpx.HTTPError as e:
        logger.error(f"HTTP error searching companies with query '{query}': {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error searching companies: {str(e)}")
        return []


async def get_tech_stack_raw(company_id: int, token: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch raw tech stack data from Draup platform for a given company ID.
    
    Args:
        company_id: Draup company/account ID
        token: Optional bearer token. If not provided, uses DRAUP_PLATFORM_TOKEN env var
        
    Returns:
        Raw response dictionary from Draup API, or None if error occurs
    """
    auth_token = token or os.environ.get('DRAUP_PLATFORM_TOKEN')
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Draup platform token not configured"
        )
    
    url = f"https://platform.draup.com/service/accounts/api/tech_stack/{company_id}/tech_stack_products/"
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {auth_token}",
        "product-id": "4",
        "Content-Type": "application/json"
    }
    payload = {"response_data": {}}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
            
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching tech stack for company {company_id}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching tech stack for company {company_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error fetching tech stack: {str(e)}")
        return None


async def fetch_tech_stack_from_draup_api(company_id: int, user_token: str) -> Dict:
    """
    Fetch tech stack data from Draup platform API using user's token.
    
    This function handles the API call to Draup platform and validates the response.
    All Draup API calls should go through this service for validation.
    
    Args:
        company_id: Draup company/account ID
        user_token: User's bearer token for Draup API authentication
        
    Returns:
        Raw response dictionary from Draup API
        
    Raises:
        HTTPException: If API call fails or token is invalid
    """
    from constants.auth import URL_MAPPING
    
    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User token is required"
        )
    
    draup_url = f"{URL_MAPPING.get('prod')}/service/accounts/api/tech_stack/{company_id}/tech_stack_products/"
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {user_token}",
        "product-id": "4",
        "Content-Type": "application/json"
    }
    
    payload = {"response_data": {}}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                draup_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching tech stack from Draup for company {company_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to Draup platform timed out"
        )
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching tech stack from Draup for company {company_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch from Draup platform: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tech stack from Draup for company {company_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tech stack products: {str(e)}"
        )

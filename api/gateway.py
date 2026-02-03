import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from settings.database import get_db
from services.gateway_service import gateway_service
from schemas.gateway_schemas import (
    TechStackSuggestionRequest,
    TechStackWithMasterDataResponse,
    MasterTechStackItem,
    ProductSuggestion
)
from services.auth import verify_token

logger = logging.getLogger(__name__)

gateway_router = APIRouter(prefix="/etter", tags=["Gateway"])


@gateway_router.post(
    "/techstack/suggest",
    response_model=TechStackWithMasterDataResponse,
    status_code=status.HTTP_200_OK
)
def get_techstack_suggestions_with_master_data(
    request: TechStackSuggestionRequest,
    db: Session = Depends(get_db),
    user=Depends(verify_token)
):
    try:
        gateway_response = gateway_service.get_techstack_suggestions(
            input_text=request.input_text,
            score_limit=request.score_limit
        )
        
        if gateway_response.get("status") != "success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gateway API returned error: {gateway_response.get('errors')}"
            )
        
        results = gateway_response.get("results", {})
        
        all_products = []
        for input_key, suggestions in results.items():
            for suggestion in suggestions:
                product = suggestion.get("product")
                if product:
                    all_products.append(product)
        
        master_data = gateway_service.fetch_master_techstack_data(
            db=db,
            products=all_products
        )
        
        formatted_suggestions = {}
        for input_key, suggestions in results.items():
            formatted_suggestions[input_key] = [
                ProductSuggestion(
                    product=suggestion.get("product"),
                    score=suggestion.get("score")
                )
                for suggestion in suggestions
            ]
        
        return TechStackWithMasterDataResponse(
            status="success",
            suggestions=formatted_suggestions,
            master_data=[MasterTechStackItem(**item) for item in master_data]
        )
    
    except Exception as e:
        logger.error(f"Error fetching techstack suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch techstack suggestions: {str(e)}"
        )

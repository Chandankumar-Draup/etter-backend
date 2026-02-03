from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class TechStackSuggestionRequest(BaseModel):
    input_text: List[str] = Field(..., description="List of input text strings to search for")
    score_limit: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum score threshold for suggestions")


class ProductSuggestion(BaseModel):
    product: str
    score: float


class TechStackSuggestionResponse(BaseModel):
    status: str
    errors: Optional[str] = None
    results: Dict[str, List[ProductSuggestion]]


class MasterTechStackItem(BaseModel):
    id: int
    product_name: Optional[str] = None
    description: Optional[str] = None
    product_picture_s3_url: Optional[str] = None
    g2_sub_sub_category_3: Optional[str] = None

    class Config:
        from_attributes = True


class TechStackWithMasterDataResponse(BaseModel):
    status: str
    suggestions: Dict[str, List[ProductSuggestion]]
    master_data: List[MasterTechStackItem]

from typing import List, Any, Optional
from math import ceil
from sqlalchemy.orm import Query
from pydantic import BaseModel

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 50
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    def validate(self):
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 1000:
            raise ValueError("Page size must be between 1 and 1000")

class PaginatedResult(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

def paginate(
    query: Query,
    page: int = 1,
    page_size: int = 50
) -> PaginatedResult:
    params = PaginationParams(page=page, page_size=page_size)
    params.validate()
    try:
        total = query.count()
    except Exception as e:
        print(e)
    items = query.offset(params.offset).limit(page_size).all()
    
    total_pages = ceil(total / page_size) if total > 0 else 0
    
    return PaginatedResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

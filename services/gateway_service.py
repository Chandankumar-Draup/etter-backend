import logging
import os
from typing import List, Dict, Optional
import requests
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models.extraction import MasterTechStack
from constants.auth import ENV
logger = logging.getLogger(__name__)


class GatewayService:
    def __init__(self):
        self.environment = ENV
        if self.environment == 'prod':
            self.base_url = "https://gateway.draup.technology/api"
        else:
            self.base_url = "https://gateway-qa.draup.technology/api"
        
        self.token = os.environ.get('GATEWAY_TOKEN')
        if not self.token:
            logger.warning("GATEWAY_TOKEN environment variable not set")

    def get_techstack_suggestions(
        self,
        input_text: List[str],
        score_limit: float = 0.8
    ) -> Dict:
        if not self.token:
            raise ValueError("GATEWAY_TOKEN environment variable is not set")
        
        endpoint = f"{self.base_url}/iris1/v1.0/techstack/suggest"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.token}'
        }
        
        payload = {
            "input_text": input_text,
            "score_limit": score_limit
        }
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Gateway API request failed: {str(e)}")
            raise

    def fetch_master_techstack_data(
        self,
        db: Session,
        products: List[str]
    ) -> List[Dict]:
        if not products:
            return []
        
        try:
            from sqlalchemy.orm import joinedload
            
            conditions = []
            for product in products:
                conditions.append(
                    MasterTechStack.product_name.ilike(f"%{product}%")
                )
            
            techstack_records = db.query(MasterTechStack).options(
                joinedload(MasterTechStack.g2_category)
            ).filter(
                or_(*conditions)
            ).all()
            
            results = []
            for record in techstack_records:
                results.append({
                    "id": record.id,
                    "product_name": record.product_name,
                    "description": record.description,
                    "product_picture_s3_url": record.product_picture_s3_url,
                    "g2_sub_sub_category_3": record.g2_sub_sub_category_3
                })
            
            return results
        except Exception as e:
            logger.error(f"Error fetching master techstack data: {str(e)}", exc_info=True)
            raise


gateway_service = GatewayService()

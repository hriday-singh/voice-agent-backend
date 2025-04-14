from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Any, Optional
from app.utils.auth import get_token_data, verify_admin
from app.database.db import get_db
from app.models.models import (
    get_all_llm_providers, get_llm_provider, create_llm_provider, 
    update_llm_provider, delete_llm_provider, get_all_llm_models,
    get_llm_model, create_llm_model, update_llm_model, delete_llm_model,
    Session, LLMProvider, LLMModel
)
from app.schemas.agent import (
    LLMProviderCreate, LLMProviderUpdate, LLMProviderResponse,
    LLMModelCreate, LLMModelUpdate, LLMModelResponse
)
import logging
from sqlmodel import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/llm", tags=["Admin LLM Management"])
security = HTTPBearer()

# Helper function to check admin authorization
def check_admin_authorization(token_data: Dict):
    """Check if user is admin"""
    if token_data.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    return True

# LLM Provider endpoints
@router.get("/providers", response_model=List[LLMProviderResponse])
async def get_providers(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Get all LLM providers"""
    try:
        with get_db() as session:
            providers = get_all_llm_providers(session)
            return providers
    except Exception as e:
        logger.error(f"Error getting LLM providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve LLM providers: {str(e)}"
        )

@router.get("/providers/{provider_id}", response_model=LLMProviderResponse)
async def get_provider(
    provider_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Get a specific LLM provider"""
    with get_db() as session:
        provider = get_llm_provider(session, provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LLM provider with ID {provider_id} not found"
            )
        return provider

@router.post("/providers", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_provider(
    provider: LLMProviderCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Create a new LLM provider"""
    try:
        with get_db() as session:
            # Check if provider with this name already exists
            existing = session.exec(select(LLMProvider).where(LLMProvider.name == provider.name)).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Provider with name '{provider.name}' already exists"
                )
            
            # Remove enabled field if it exists in the data
            provider_data = provider.model_dump()
            if "enabled" in provider_data:
                del provider_data["enabled"]
                
            provider_id = create_llm_provider(session, provider_data)
            
            return {
                "id": provider_id,
                "message": f"LLM provider '{provider.name}' created successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating LLM provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create LLM provider: {str(e)}"
        )

@router.put("/providers/{provider_id}", response_model=Dict[str, Any])
async def update_provider(
    provider_id: int,
    provider: LLMProviderUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Update an existing LLM provider"""
    try:
        with get_db() as session:
            # Check if provider exists
            existing = get_llm_provider(session, provider_id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"LLM provider with ID {provider_id} not found"
                )
                
            # Check for name uniqueness if name is being updated
            if provider.name and provider.name != existing.name:
                name_exists = session.exec(
                    select(LLMProvider).where(LLMProvider.name == provider.name)
                ).first()
                if name_exists:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Provider with name '{provider.name}' already exists"
                    )
            
            # Update only provided fields and remove enabled field
            update_data = {k: v for k, v in provider.model_dump().items() if v is not None}
            if "enabled" in update_data:
                del update_data["enabled"]
            
            success = update_llm_provider(session, provider_id, update_data)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update LLM provider"
                )
                
            return {"message": f"LLM provider updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating LLM provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update LLM provider: {str(e)}"
        )

@router.delete("/providers/{provider_id}", response_model=Dict[str, Any])
async def delete_provider(
    provider_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Delete an LLM provider"""
    try:
        with get_db() as session:
            # Check if provider exists
            existing = get_llm_provider(session, provider_id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"LLM provider with ID {provider_id} not found"
                )
                
            # Get all models for this provider
            models = session.exec(select(LLMModel).where(LLMModel.provider_id == provider_id)).all()
            
            # Delete the provider (this will also delete all associated models)
            success = delete_llm_provider(session, provider_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete LLM provider"
                )
                
            return {
                "message": f"LLM provider '{existing.name}' and {len(models)} associated models deleted successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting LLM provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete LLM provider: {str(e)}"
        )

# LLM Model endpoints
@router.get("/models", response_model=List[Dict[str, Any]])
async def get_models(
    provider_id: Optional[int] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Get all LLM models, optionally filtered by provider"""
    try:
        with get_db() as session:
            models = get_all_llm_models(session, provider_id)
            
            # Enhance response with provider information
            result = []
            for model in models:
                model_dict = {
                    "id": model.id,
                    "name": model.name,
                    "display_name": model.display_name,
                    "default_temperature": model.default_temperature,
                    "provider_id": model.provider_id,
                }
                
                # Add provider name if provider is available
                if hasattr(model, 'provider') and model.provider:
                    model_dict["provider_name"] = model.provider.name
                
                result.append(model_dict)
            
            return result
    except Exception as e:
        logger.error(f"Error getting LLM models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve LLM models: {str(e)}"
        )

@router.get("/models/{model_id}", response_model=Dict[str, Any])
async def get_model(
    model_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Get a specific LLM model"""
    with get_db() as session:
        model = get_llm_model(session, model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LLM model with ID {model_id} not found"
            )
        
        # Create enhanced response with provider information
        result = {
            "id": model.id,
            "name": model.name,
            "display_name": model.display_name,
            "default_temperature": model.default_temperature,
            "provider_id": model.provider_id,
        }
        
        # Add provider name if provider is available
        if hasattr(model, 'provider') and model.provider:
            result["provider_name"] = model.provider.name
        
        return result

@router.post("/models", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_model(
    model: LLMModelCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Create a new LLM model"""
    try:
        with get_db() as session:
            # Check if provider exists
            provider = get_llm_provider(session, model.provider_id)
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"LLM provider with ID {model.provider_id} not found"
                )
                
            # Check if model with this name already exists for this provider
            existing = session.exec(
                select(LLMModel).where(
                    (LLMModel.provider_id == model.provider_id) & 
                    (LLMModel.name == model.name)
                )
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Model '{model.name}' already exists for this provider"
                )
            
            model_id = create_llm_model(session, model.model_dump())
            
            return {
                "id": model_id,
                "message": f"LLM model '{model.name}' created successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating LLM model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create LLM model: {str(e)}"
        )

@router.put("/models/{model_id}", response_model=Dict[str, Any])
async def update_model(
    model_id: int,
    model: LLMModelUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Update an existing LLM model"""
    try:
        with get_db() as session:
            # Check if model exists
            existing = get_llm_model(session, model_id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"LLM model with ID {model_id} not found"
                )
                
            # Check for name uniqueness if name is being updated
            if model.name and model.name != existing.name:
                name_exists = session.exec(
                    select(LLMModel).where(
                        (LLMModel.provider_id == existing.provider_id) & 
                        (LLMModel.name == model.name)
                    )
                ).first()
                if name_exists:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Model with name '{model.name}' already exists for this provider"
                    )
            
            # Update only provided fields
            update_data = {k: v for k, v in model.model_dump().items() if v is not None}
            success = update_llm_model(session, model_id, update_data)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update LLM model"
                )
                
            return {"message": f"LLM model updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating LLM model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update LLM model: {str(e)}"
        )

@router.delete("/models/{model_id}", response_model=Dict[str, Any])
async def delete_model(
    model_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Delete an LLM model"""
    try:
        with get_db() as session:
            # Check if model exists
            existing = get_llm_model(session, model_id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"LLM model with ID {model_id} not found"
                )
                
            # Delete the model
            success = delete_llm_model(session, model_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete LLM model"
                )
                
            return {"message": f"LLM model '{existing.name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting LLM model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete LLM model: {str(e)}"
        ) 
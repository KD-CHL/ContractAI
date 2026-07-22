"""FastAPI routes and transport schemas for ContractGuard."""

from fastapi import APIRouter

from contract_guard.api.auth_routes import router as auth_router
from contract_guard.api.operations_routes import router as operations_router
from contract_guard.api.routes import router as review_router
from contract_guard.api.workspace_routes import router as workspace_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(workspace_router)
router.include_router(operations_router)
router.include_router(review_router)

__all__ = ["router"]

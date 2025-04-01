from fastapi import APIRouter, Depends, HTTPException
from app.utils.auth import get_token_data
from . import realestate_agent, hospital_agent

# Disabled voice agent router
# router = APIRouter(
#     prefix="/voice-agents",
#     tags=["Voice Agents"],
#     dependencies=[Depends(get_token_data)]  # Apply JWT auth to all routes in this router
# )

# # Mount the voice agent streams with authentication
# realestate_agent.stream.mount(router, path="/realestate")
# hospital_agent.stream.mount(router, path="/hospital") 
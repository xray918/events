"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import auth, events, registrations, staff, host, checkin, notify, upload

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(registrations.router, prefix="/registrations", tags=["registrations"])
api_router.include_router(staff.router, prefix="/staff", tags=["staff"])
api_router.include_router(host.router, prefix="/host", tags=["host"])
api_router.include_router(checkin.router, prefix="/checkin", tags=["checkin"])
api_router.include_router(notify.router, prefix="/notify", tags=["notify"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])

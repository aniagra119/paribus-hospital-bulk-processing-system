"""
FastAPI Dependency Injection providers.

These functions are used with FastAPI's `Depends()` to inject
service instances into route handlers, keeping the routes clean
and making unit testing trivial (just override the dependency).
"""

from fastapi import Request

from app.services.hospital_client import HospitalClient


def get_hospital_client(request: Request) -> HospitalClient:
    """
    Inject a HospitalClient backed by the shared httpx.AsyncClient
    created during app lifespan.
    """
    return HospitalClient(client=request.app.state.http_client)

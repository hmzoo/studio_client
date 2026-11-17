"""Fabrique de la passerelle de génération."""
from __future__ import annotations

from ..config import settings
from .fake_gateway import FakeGenerationGatewayClient
from .http_gateway import HttpGenerationGatewayClient
from .interface import GenerationGatewayClient


def get_gateway() -> GenerationGatewayClient:
    if settings.generation_gateway_mode == "http":
        return HttpGenerationGatewayClient()
    if settings.generation_gateway_mode == "fake":
        return FakeGenerationGatewayClient()
    raise ValueError(f"GENERATION_GATEWAY_MODE inconnu : {settings.generation_gateway_mode}")

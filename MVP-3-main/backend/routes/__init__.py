"""
Routes package for Servex Holdings backend.
Exports all route modules for easy import in main.py.
"""
from routes import (
    auth_routes,
    client_routes,
    shipment_routes,
    trip_routes,
    invoice_routes,
    finance_routes,
    fleet_routes,
    warehouse_routes,
    team_routes,
)

__all__ = [
    "auth_routes",
    "client_routes",
    "shipment_routes",
    "trip_routes",
    "invoice_routes",
    "finance_routes",
    "fleet_routes",
    "warehouse_routes",
    "team_routes",
]

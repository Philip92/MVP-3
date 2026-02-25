"""
Database connection module for Servex Holdings backend.
Manages MongoDB connection using motor async driver.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, DB_NAME

# MongoDB client and database instances
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections (for reference and type hints)
users_collection = db['users']
clients_collection = db['clients']
client_rates_collection = db['client_rates']
shipments_collection = db['shipments']
shipment_pieces_collection = db['shipment_pieces']
trips_collection = db['trips']
invoices_collection = db['invoices']
invoice_line_items_collection = db['invoice_line_items']
invoice_adjustments_collection = db['invoice_adjustments']
payments_collection = db['payments']
expenses_collection = db['expenses']
vehicles_collection = db['vehicles']
drivers_collection = db['drivers']
warehouses_collection = db['warehouses']
audit_logs_collection = db['audit_logs']
notifications_collection = db['notifications']
settings_collection = db['settings']

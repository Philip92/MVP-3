#!/usr/bin/env python3
"""
SESSION E Migration: Add Extended Client Management Fields

Adds 7 new fields to existing clients:
1. position - Key contact's job title/position
2. place_of_business - Physical business location address
3. relationship_nature - Type of business relationship
4. owner - Account owner/manager assigned to this client
5. frequency - Shipping frequency (daily, weekly, monthly, quarterly)
6. estimated_value - Estimated annual shipping value
7. total_spent - Running total of all invoiced amounts (auto-calculated)
"""

import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MONGO_URL, DB_NAME

async def migrate():
    """Add extended fields to all existing clients"""
    print("Starting SESSION E migration: Adding extended client fields...")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Define default values for new fields
    default_fields = {
        "position": "",  # Empty string by default
        "place_of_business": "",  # Will be populated from address if available
        "relationship_nature": "regular",  # Options: regular, vip, bulk, retail
        "owner": "",  # Empty until assigned
        "frequency": "monthly",  # Options: daily, weekly, bi-weekly, monthly, quarterly, yearly, sporadic
        "estimated_value": 0.0,  # Float, in base currency
        "total_spent": 0.0,  # Will be calculated from invoices
        "extended_fields_added_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Update all clients without these fields
    result = await db.clients.update_many(
        {"position": {"$exists": False}},  # Only update clients without new fields
        {"$set": default_fields}
    )
    
    print(f"✓ Updated {result.modified_count} clients with extended fields")
    
    # Calculate total_spent for each client from invoices
    print("Calculating total_spent from invoices...")
    clients = await db.clients.find({}).to_list(1000)
    
    updated_count = 0
    for client_doc in clients:
        client_id = client_doc.get('id')
        
        # Sum all paid amounts from invoices for this client
        invoices = await db.invoices.find({
            "client_id": client_id,
            "status": {"$in": ["paid", "partial"]}
        }).to_list(5000)
        
        total_spent = sum(
            inv.get("paid_amount", 0) 
            for inv in invoices
        )
        
        # Update client with calculated total
        await db.clients.update_one(
            {"id": client_id},
            {"$set": {"total_spent": round(total_spent, 2)}}
        )
        updated_count += 1
    
    print(f"✓ Calculated total_spent for {updated_count} clients")
    
    # Copy address to place_of_business if empty
    await db.clients.update_many(
        {"place_of_business": "", "address": {"$exists": True, "$ne": ""}},
        [{"$set": {"place_of_business": "$address"}}]
    )
    
    print("✓ Copied address to place_of_business where applicable")
    
    client.close()
    print("\n" + "="*50)
    print("SESSION E Migration Complete!")
    print("="*50)
    print("\nNew fields added to clients:")
    print("  • position")
    print("  • place_of_business")
    print("  • relationship_nature")
    print("  • owner")
    print("  • frequency")
    print("  • estimated_value")
    print("  • total_spent (auto-calculated)")
    print("\nNext steps:")
    print("1. Update frontend Client.jsx to include new fields in form")
    print("2. Update client table to show new columns")
    print("3. Implement CSV import/export with new fields")

if __name__ == "__main__":
    asyncio.run(migrate())

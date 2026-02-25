#!/usr/bin/env python3
"""
Comprehensive database seeding script for SERVEX ERP.
Creates realistic test data: clients, trips, shipments, invoices, and payments.
"""

import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Database connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Constants
ZAR_RATE = 36.0  # Default rate per kg
KES_RATE = 6.67  # Exchange rate

# Sample data
SOUTH_AFRICAN_NAMES = [
    "Thabo Mokoena", "Sipho Ndlovu", "Johan van der Merwe", "Pieter du Plessis",
    "Nomvula Khumalo", "Zanele Dlamini", "Jan Botha", "Maria van Wyk",
    "Bongani Mthembu", "Lindiwe Zulu", "André Fourie", "Hendrik Venter",
    "Precious Mahlangu", "Themba Sithole", "Elmarie Coetzee", "Francois Nel",
    "Ntombi Nkosi", "Sbusiso Zwane", "Christo Joubert", "Lerato Molefe"
]

KENYAN_NAMES = [
    "James Mwangi", "Mary Wanjiku", "Peter Ochieng", "Grace Akinyi",
    "David Kamau", "Faith Njeri", "John Otieno", "Anne Wambui",
    "Samuel Kipchoge", "Esther Chebet", "Michael Korir", "Ruth Kemunto"
]

COMPANY_NAMES = [
    "Shoprite Holdings", "Pick n Pay", "Checkers Fresh", "Woolworths SA",
    "Makro Wholesale", "Game Stores", "Builders Warehouse", "Massmart",
    "Dis-Chem Pharmacies", "Clicks Group", "Spar Group", "Food Lover's Market",
    "Metro Cash & Carry", "Cambridge Foods", "KitKat Cash & Carry",
    "OK Furniture", "Lewis Group", "JD Group", "Pep Stores", "Ackermans",
    "Truworths", "Foschini", "Edgars", "Jet Stores", "Total Energies"
]

ITEM_DESCRIPTIONS = [
    "Electronics - TV Samsung 55\"", "Household Appliances - Microwave",
    "Furniture - Office Chair", "Auto Parts - Brake Pads Set",
    "Clothing Bulk - Winter Collection", "Food Products - Canned Goods",
    "Building Materials - Cement Bags", "Medical Supplies - PPE Kit",
    "Industrial Equipment - Pump Motor", "Agricultural Supplies - Seeds",
    "Textiles - Cotton Fabric Rolls", "Cosmetics - Beauty Products",
    "Stationery - Office Supplies Box", "Tools - Power Drill Set",
    "Sporting Goods - Gym Equipment", "Toys - Children's Games",
    "Kitchenware - Cookware Set", "Garden Supplies - Fertilizer",
    "Cleaning Products - Detergent Bulk", "Pet Supplies - Dog Food"
]

ROUTES = [
    ["Johannesburg", "Beitbridge", "Harare"],
    ["Johannesburg", "Musina", "Harare", "Lusaka"],
    ["Durban", "Johannesburg", "Harare"],
    ["Cape Town", "Johannesburg", "Harare"],
    ["Johannesburg", "Maputo"],
    ["Pretoria", "Polokwane", "Beitbridge", "Harare"],
    ["Johannesburg", "Nairobi"],
    ["Durban", "Beitbridge", "Harare", "Lusaka"]
]


def gen_id():
    return str(uuid.uuid4())


def gen_phone():
    return f"+27{random.randint(60, 89)}{random.randint(1000000, 9999999)}"


def gen_email(name):
    clean = name.lower().replace(" ", ".").replace("'", "")
    domains = ["gmail.com", "outlook.com", "yahoo.com", "icloud.com", "business.co.za"]
    return f"{clean}@{random.choice(domains)}"


def gen_date_past(days_back_min=1, days_back_max=90):
    days = random.randint(days_back_min, days_back_max)
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def gen_date_future(days_ahead_min=1, days_ahead_max=30):
    days = random.randint(days_ahead_min, days_ahead_max)
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


async def get_tenant_and_user():
    """Get existing tenant and user, or create default ones."""
    tenant = await db.tenants.find_one({}, {"_id": 0})
    user = await db.users.find_one({}, {"_id": 0})
    
    if not tenant:
        tenant = {
            "id": gen_id(),
            "subdomain": "servex",
            "company_name": "Servex Holdings",
            "default_currency": "ZAR",
            "default_rate_type": "per_kg",
            "default_rate_value": ZAR_RATE,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.tenants.insert_one(tenant)
        print("Created default tenant")
    
    if not user:
        user = {
            "id": gen_id(),
            "tenant_id": tenant["id"],
            "name": "Admin User",
            "email": "admin@servex.co.za",
            "role": "owner",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user)
        print("Created default admin user")
    
    return tenant, user


async def create_warehouses(tenant_id):
    """Create warehouses if they don't exist."""
    existing = await db.warehouses.count_documents({"tenant_id": tenant_id})
    if existing > 0:
        warehouses = await db.warehouses.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(10)
        return warehouses
    
    warehouses = [
        {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "name": "Johannesburg Main",
            "code": "JHB",
            "address": "123 Industrial Road, Sandton, Johannesburg",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "name": "Nairobi Hub",
            "code": "NBO",
            "address": "45 Mombasa Road, Industrial Area, Nairobi",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.warehouses.insert_many(warehouses)
    print(f"Created {len(warehouses)} warehouses")
    return warehouses


async def create_clients(tenant_id, count=50):
    """Create client records."""
    # Check existing count
    existing = await db.clients.count_documents({"tenant_id": tenant_id})
    if existing >= count:
        print(f"Skipping client creation - {existing} clients already exist")
        return await db.clients.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(count)
    
    # Generate new clients
    clients = []
    all_names = SOUTH_AFRICAN_NAMES + KENYAN_NAMES
    
    for i in range(count):
        name = random.choice(all_names) if i < len(all_names) else f"Client {i+1}"
        company = random.choice(COMPANY_NAMES) if random.random() > 0.3 else None
        rate = random.choice([32.0, 34.0, 36.0, 38.0, 40.0, 42.0])
        
        client = {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "name": name,
            "company_name": company,
            "phone": gen_phone(),
            "email": gen_email(name),
            "whatsapp": gen_phone(),
            "physical_address": f"{random.randint(1, 500)} {random.choice(['Main', 'Oak', 'Church', 'Long'])} Street, Johannesburg",
            "billing_address": None,
            "vat_number": f"VAT{random.randint(1000000, 9999999)}" if random.random() > 0.5 else None,
            "default_currency": "ZAR",
            "default_rate_type": "per_kg",
            "default_rate_value": rate,
            "credit_limit": random.choice([0, 5000, 10000, 20000, 50000]),
            "payment_terms_days": random.choice([7, 14, 30]),
            "status": "active",
            "created_at": gen_date_past(30, 180)
        }
        clients.append(client)
    
    await db.clients.insert_many(clients)
    print(f"Created {len(clients)} clients")
    return clients


async def create_trips(tenant_id, user_id, count=8):
    """Create trip records with various statuses."""
    existing = await db.trips.count_documents({"tenant_id": tenant_id})
    if existing >= count:
        print(f"Skipping trip creation - {existing} trips already exist")
        return await db.trips.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(count)
    
    trips = []
    statuses = ["planning", "loading", "in_transit", "delivered", "closed"]
    
    for i in range(count):
        trip_num = f"SH-{2025}-{str(i+1).zfill(3)}"
        route = random.choice(ROUTES)
        status = statuses[min(i, len(statuses) - 1)] if i < 5 else random.choice(statuses)
        
        # Older trips are more likely to be closed/delivered
        if i < 3:
            status = random.choice(["delivered", "closed"])
            created = gen_date_past(30, 90)
        elif i < 5:
            status = random.choice(["in_transit", "delivered"])
            created = gen_date_past(7, 30)
        else:
            status = random.choice(["planning", "loading"])
            created = gen_date_past(1, 7)
        
        trip = {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "trip_number": trip_num,
            "route": route,
            "departure_date": gen_date_future(1, 14) if status == "planning" else gen_date_past(1, 30),
            "status": status,
            "capacity_kg": random.choice([5000, 8000, 10000, 12000, 15000]),
            "capacity_cbm": random.choice([20, 30, 40, 50]),
            "vehicle_id": None,
            "driver_id": None,
            "notes": f"Regular shipment to {route[-1]}",
            "created_by": user_id,
            "created_at": created
        }
        trips.append(trip)
    
    await db.trips.insert_many(trips)
    print(f"Created {len(trips)} trips")
    return trips


async def create_shipments_and_invoices(tenant_id, user_id, clients, trips, warehouses):
    """Create shipments and invoices for trips."""
    # Check existing
    existing_shipments = await db.shipments.count_documents({"tenant_id": tenant_id})
    if existing_shipments > 100:
        print(f"Skipping shipment creation - {existing_shipments} shipments already exist")
        return
    
    total_shipments = 0
    total_invoices = 0
    total_line_items = 0
    
    for trip in trips:
        # Number of clients per trip (reduced for ~100 parcels total)
        num_clients = random.randint(5, 10)
        trip_clients = random.sample(clients, min(num_clients, len(clients)))
        
        for client in trip_clients:
            # Parcels per client for this trip (reduced to reach ~100 total)
            num_parcels = random.randint(1, 3)
            
            # Create invoice first
            invoice_id = gen_id()
            invoice_num = f"INV-2025-{str(total_invoices + 1).zfill(3)}"
            
            # Determine invoice status based on trip status
            if trip["status"] in ["closed", "delivered"]:
                inv_status = random.choices(
                    ["paid", "sent", "overdue"],
                    weights=[0.6, 0.25, 0.15]
                )[0]
            elif trip["status"] == "in_transit":
                inv_status = random.choices(
                    ["paid", "sent", "draft"],
                    weights=[0.3, 0.5, 0.2]
                )[0]
            else:
                inv_status = "draft"
            
            line_items = []
            invoice_total = 0
            
            for p_idx in range(num_parcels):
                # Create shipment
                weight = round(random.uniform(5, 150), 1)
                length = random.randint(20, 100)
                width = random.randint(20, 80)
                height = random.randint(10, 60)
                cbm = (length * width * height) / 1000000
                
                # Determine shipment status based on trip
                if trip["status"] == "closed":
                    ship_status = "delivered"
                elif trip["status"] == "delivered":
                    ship_status = random.choice(["delivered", "arrived"])
                elif trip["status"] == "in_transit":
                    ship_status = "in_transit"
                elif trip["status"] == "loading":
                    ship_status = random.choice(["staged", "loaded"])
                else:
                    ship_status = "warehouse"
                
                warehouse = random.choice(warehouses)
                shipment = {
                    "id": gen_id(),
                    "tenant_id": tenant_id,
                    "client_id": client["id"],
                    "trip_id": trip["id"],
                    "invoice_id": invoice_id if inv_status != "draft" else None,
                    "description": random.choice(ITEM_DESCRIPTIONS),
                    "destination": trip["route"][-1],
                    "total_pieces": 1,
                    "total_weight": weight,
                    "total_cbm": round(cbm, 4),
                    "quantity": 1,
                    "status": ship_status,
                    "warehouse_id": warehouse["id"],
                    "recipient": f"Recipient for {client['name']}",
                    "recipient_phone": gen_phone(),
                    "sender": client["name"],
                    "length_cm": length,
                    "width_cm": width,
                    "height_cm": height,
                    "parcel_sequence": p_idx + 1 if num_parcels > 1 else None,
                    "total_in_sequence": num_parcels if num_parcels > 1 else None,
                    "created_by": user_id,
                    "created_at": trip["created_at"]
                }
                await db.shipments.insert_one(shipment)
                total_shipments += 1
                
                # Create line item
                rate = client.get("default_rate_value", ZAR_RATE)
                amount = round(weight * rate, 2)
                invoice_total += amount
                
                line_item = {
                    "id": gen_id(),
                    "invoice_id": invoice_id,
                    "shipment_id": shipment["id"],
                    "description": shipment["description"],
                    "quantity": 1,
                    "unit": "kg",
                    "weight_kg": weight,
                    "actual_weight": weight,
                    "rate": rate,
                    "amount": amount,
                    "length_cm": length,
                    "width_cm": width,
                    "height_cm": height
                }
                line_items.append(line_item)
                total_line_items += 1
            
            # Insert line items
            if line_items:
                await db.invoice_line_items.insert_many(line_items)
            
            # Create invoice
            paid_amount = 0
            if inv_status == "paid":
                paid_amount = invoice_total
            elif inv_status == "partial":
                paid_amount = round(invoice_total * random.uniform(0.3, 0.7), 2)
            
            # Set due date
            if inv_status == "overdue":
                due_date = (datetime.now(timezone.utc) - timedelta(days=random.randint(5, 45))).strftime("%Y-%m-%d")
            else:
                due_date = (datetime.now(timezone.utc) + timedelta(days=random.randint(7, 30))).strftime("%Y-%m-%d")
            
            invoice = {
                "id": invoice_id,
                "tenant_id": tenant_id,
                "invoice_number": invoice_num,
                "client_id": client["id"],
                "trip_id": trip["id"],
                "subtotal": invoice_total,
                "adjustments": 0,
                "total": invoice_total,
                "paid_amount": paid_amount,
                "currency": "ZAR",
                "status": inv_status,
                "due_date": due_date,
                "issue_date": trip["created_at"][:10],
                "payment_terms": "net_30",
                "comment": "",
                "client_name_snapshot": client["name"],
                "client_phone_snapshot": client.get("phone"),
                "client_email_snapshot": client.get("email"),
                "created_at": trip["created_at"]
            }
            await db.invoices.insert_one(invoice)
            total_invoices += 1
            
            # Create payment record if paid
            if paid_amount > 0:
                payment = {
                    "id": gen_id(),
                    "tenant_id": tenant_id,
                    "client_id": client["id"],
                    "invoice_id": invoice_id,
                    "amount": paid_amount,
                    "payment_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d"),
                    "payment_method": random.choice(["bank_transfer", "cash", "mobile_money"]),
                    "reference": f"PAY-{random.randint(10000, 99999)}",
                    "notes": "Payment received",
                    "created_by": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.payments.insert_one(payment)
    
    print(f"Created {total_shipments} shipments, {total_invoices} invoices, {total_line_items} line items")


async def create_additional_warehouse_parcels(tenant_id, user_id, clients, warehouses, count=50):
    """Create parcels that are in warehouse but not yet assigned to trips."""
    existing = await db.shipments.count_documents({
        "tenant_id": tenant_id,
        "status": "warehouse",
        "trip_id": None
    })
    
    if existing >= count:
        print(f"Skipping warehouse parcel creation - {existing} unassigned parcels exist")
        return
    
    shipments = []
    for i in range(count):
        client = random.choice(clients)
        warehouse = random.choice(warehouses)
        weight = round(random.uniform(5, 100), 1)
        
        shipment = {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "client_id": client["id"],
            "trip_id": None,
            "invoice_id": None,
            "description": random.choice(ITEM_DESCRIPTIONS),
            "destination": random.choice(["Harare", "Lusaka", "Nairobi", "Maputo"]),
            "total_pieces": 1,
            "total_weight": weight,
            "total_cbm": None,
            "quantity": 1,
            "status": "warehouse",
            "warehouse_id": warehouse["id"],
            "recipient": f"Recipient {i+1}",
            "recipient_phone": gen_phone(),
            "sender": client["name"],
            "created_by": user_id,
            "created_at": gen_date_past(1, 14)
        }
        shipments.append(shipment)
    
    await db.shipments.insert_many(shipments)
    print(f"Created {len(shipments)} warehouse parcels (unassigned)")


async def print_summary(tenant_id):
    """Print summary of seeded data."""
    print("\n" + "="*50)
    print("DATABASE SEED SUMMARY")
    print("="*50)
    
    counts = {
        "Clients": await db.clients.count_documents({"tenant_id": tenant_id}),
        "Trips": await db.trips.count_documents({"tenant_id": tenant_id}),
        "Shipments": await db.shipments.count_documents({"tenant_id": tenant_id}),
        "Invoices": await db.invoices.count_documents({"tenant_id": tenant_id}),
        "Line Items": await db.invoice_line_items.count_documents({}),
        "Payments": await db.payments.count_documents({"tenant_id": tenant_id}),
        "Warehouses": await db.warehouses.count_documents({"tenant_id": tenant_id})
    }
    
    for name, count in counts.items():
        print(f"  {name}: {count}")
    
    # Status breakdown
    print("\nShipment Status Breakdown:")
    for status in ["warehouse", "staged", "loaded", "in_transit", "arrived", "delivered"]:
        count = await db.shipments.count_documents({"tenant_id": tenant_id, "status": status})
        print(f"  - {status}: {count}")
    
    print("\nInvoice Status Breakdown:")
    for status in ["draft", "sent", "paid", "overdue"]:
        count = await db.invoices.count_documents({"tenant_id": tenant_id, "status": status})
        print(f"  - {status}: {count}")
    
    # Financial summary
    invoices = await db.invoices.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(5000)
    total_invoiced = sum(inv.get("total", 0) for inv in invoices)
    total_paid = sum(inv.get("paid_amount", 0) for inv in invoices)
    total_outstanding = total_invoiced - total_paid
    
    print(f"\nFinancial Summary:")
    print(f"  Total Invoiced: R {total_invoiced:,.2f}")
    print(f"  Total Collected: R {total_paid:,.2f}")
    print(f"  Outstanding: R {total_outstanding:,.2f}")
    
    print("\n" + "="*50)
    print("Seed complete! Ready for verification.")
    print("="*50)


async def main():
    """Main seeding function."""
    print("Starting database seed...")
    print(f"Database: {DB_NAME}")
    
    # Get or create tenant and user
    tenant, user = await get_tenant_and_user()
    tenant_id = tenant["id"]
    user_id = user["id"]
    
    # Create warehouses
    warehouses = await create_warehouses(tenant_id)
    
    # Create clients
    clients = await create_clients(tenant_id, count=50)
    
    # Create trips
    trips = await create_trips(tenant_id, user_id, count=8)
    
    # Create shipments and invoices for trips
    await create_shipments_and_invoices(tenant_id, user_id, clients, trips, warehouses)
    
    # Create additional warehouse parcels (reduced to reach ~100 total)
    await create_additional_warehouse_parcels(tenant_id, user_id, clients, warehouses, count=20)
    
    # Print summary
    await print_summary(tenant_id)


if __name__ == "__main__":
    asyncio.run(main())

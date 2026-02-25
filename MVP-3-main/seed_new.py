#!/usr/bin/env python3
"""
Comprehensive database seeding script for SERVEX ERP.
Creates 50 clients and 400 shipments between Johannesburg and Nairobi warehouses.
"""

import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Database connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "servex_db")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Constants
ZAR_RATE = 36.0
KES_RATE = 6.67

# Client names
SOUTH_AFRICAN_NAMES = [
    "Thabo Mokoena", "Sipho Ndlovu", "Johan van der Merwe", "Pieter du Plessis",
    "Nomvula Khumalo", "Zanele Dlamini", "Jan Botha", "Maria van Wyk",
    "Bongani Mthembu", "Lindiwe Zulu", "Andre Fourie", "Hendrik Venter",
    "Precious Mahlangu", "Themba Sithole", "Elmarie Coetzee", "Francois Nel",
    "Ntombi Nkosi", "Sbusiso Zwane", "Christo Joubert", "Lerato Molefe",
    "Werner Steyn", "Cynthia Mabaso", "Gerrit Potgieter", "Dineo Motaung",
    "Charl Engelbrecht"
]

KENYAN_NAMES = [
    "James Mwangi", "Mary Wanjiku", "Peter Ochieng", "Grace Akinyi",
    "David Kamau", "Faith Njeri", "John Otieno", "Anne Wambui",
    "Samuel Kipchoge", "Esther Chebet", "Michael Korir", "Ruth Kemunto",
    "Daniel Mutua", "Sarah Nyambura", "Patrick Wafula", "Lucy Muthoni",
    "George Kiprono", "Alice Adhiambo", "Thomas Kiptoo", "Betty Nyokabi",
    "Robert Omondi", "Janet Wangari", "William Barasa", "Catherine Cherotich",
    "Joseph Ndirangu"
]

COMPANY_NAMES = [
    "Shoprite Holdings", "Pick n Pay", "Checkers Fresh", "Woolworths SA",
    "Makro Wholesale", "Game Stores", "Builders Warehouse", "Massmart",
    "Dis-Chem Pharmacies", "Clicks Group", "Spar Group", "Food Lovers Market",
    "Metro Cash & Carry", "Cambridge Foods", "KitKat Cash & Carry",
    "OK Furniture", "Lewis Group", "JD Group", "Pep Stores", "Ackermans",
    "Truworths", "Foschini", "Edgars", "Jet Stores", "Total Energies",
    "Safaricom Ltd", "KCB Group", "Equity Bank", "Tusker Breweries", "East African Breweries",
    "Bamburi Cement", "Kenya Airways", "Nation Media", "Bidco Africa", "Tuskys Supermarket",
    "Naivas Supermarket", "Carrefour Kenya", "Bidvest SA", "Tiger Brands", "Pioneer Foods",
    "Sappi Limited", "Naspers", "Investec", "Discovery Ltd", "Old Mutual",
    "Sanlam", "FirstRand", "Nedbank", "Standard Bank", "Absa Group"
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
    "Cleaning Products - Detergent Bulk", "Pet Supplies - Dog Food",
    "Wine - Stellenbosch Selection", "Coffee - Premium Kenyan Beans",
    "Tea - Rooibos Premium", "Electronics - Laptop Dell",
    "Machinery - Conveyor Belt Parts", "Pharmaceuticals - OTC Medicine",
    "Solar Panels - 300W Monocrystalline", "Batteries - Lithium Ion Pack",
    "Tyres - Continental 205/55R16", "Engine Oil - 5W-30 Bulk",
    "Fabric - Ankara Prints", "Shoes - Leather Formal", 
    "Hardware - Plumbing Fittings", "Paint - Dulux Interior 20L",
    "Glass - Tempered Sheets", "Steel - Reinforcement Bars",
    "Plastic - PVC Pipes", "Paper - A4 Copier Box",
    "Electrical - Cable 2.5mm Roll", "Food - Maize Meal 50kg"
]


def gen_id():
    return str(uuid.uuid4())


def gen_phone_sa():
    return f"+27{random.randint(60, 89)}{random.randint(1000000, 9999999)}"


def gen_phone_ke():
    return f"+254{random.randint(700, 799)}{random.randint(100000, 999999)}"


def gen_email(name):
    clean = name.lower().replace(" ", ".").replace("'", "")
    domains = ["gmail.com", "outlook.com", "yahoo.com", "business.co.za", "company.co.ke"]
    return f"{clean}@{random.choice(domains)}"


def gen_date_past(days_back_min=1, days_back_max=90):
    days = random.randint(days_back_min, days_back_max)
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def gen_date_future(days_ahead_min=1, days_ahead_max=30):
    days = random.randint(days_ahead_min, days_ahead_max)
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


async def clear_data():
    """Clear all existing data."""
    collections = ["clients", "trips", "shipments", "invoices", "invoice_line_items", 
                    "payments", "warehouses", "notifications", "audit_logs", "whatsapp_templates"]
    for coll_name in collections:
        count = await db[coll_name].count_documents({})
        if count > 0:
            await db[coll_name].delete_many({})
            print(f"  Cleared {count} records from {coll_name}")


async def get_tenant_and_user():
    """Get existing tenant and user."""
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
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user = {
            "id": gen_id(),
            "tenant_id": tenant["id"],
            "name": "Admin User",
            "email": "admin@servex.com",
            "password_hash": pwd_context.hash("Servex2026!"),
            "role": "owner",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user)
        print("Created default admin user")
    
    return tenant, user


async def create_warehouses(tenant_id, user_id):
    """Create Johannesburg and Nairobi warehouses."""
    warehouses = [
        {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "name": "Johannesburg Warehouse",
            "code": "JHB",
            "location": "Johannesburg, South Africa",
            "address": "123 Industrial Road, Sandton, Johannesburg",
            "contact_person": "Johan van der Merwe",
            "phone": "+27115551234",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user_id
        },
        {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "name": "Nairobi Warehouse",
            "code": "NBO",
            "location": "Nairobi, Kenya",
            "address": "45 Mombasa Road, Industrial Area, Nairobi",
            "contact_person": "James Mwangi",
            "phone": "+254701234567",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user_id
        }
    ]
    
    await db.warehouses.insert_many(warehouses)
    print(f"Created {len(warehouses)} warehouses: Johannesburg, Nairobi")
    return warehouses


async def create_clients(tenant_id, count=50):
    """Create 50 client records."""
    all_names = SOUTH_AFRICAN_NAMES + KENYAN_NAMES
    random.shuffle(all_names)
    
    clients = []
    for i in range(count):
        name = all_names[i] if i < len(all_names) else f"Client {i+1}"
        is_kenyan = i >= 25 or "Mwangi" in name or "Wanjiku" in name or "Ochieng" in name
        company = COMPANY_NAMES[i] if i < len(COMPANY_NAMES) else None
        rate = random.choice([32.0, 34.0, 36.0, 38.0, 40.0, 42.0, 44.0])
        
        client = {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "name": name,
            "company_name": company,
            "phone": gen_phone_ke() if is_kenyan else gen_phone_sa(),
            "email": gen_email(name),
            "whatsapp": gen_phone_ke() if is_kenyan else gen_phone_sa(),
            "physical_address": f"{random.randint(1, 500)} {random.choice(['Main', 'Oak', 'Church', 'Long', 'Kenyatta', 'Moi'])} {'Avenue' if is_kenyan else 'Street'}, {'Nairobi' if is_kenyan else 'Johannesburg'}",
            "billing_address": None,
            "vat_number": f"VAT{random.randint(1000000, 9999999)}" if random.random() > 0.4 else None,
            "default_currency": "KES" if is_kenyan and random.random() > 0.5 else "ZAR",
            "default_rate_type": "per_kg",
            "default_rate_value": rate,
            "credit_limit": random.choice([0, 5000, 10000, 20000, 50000, 100000]),
            "payment_terms_days": random.choice([7, 14, 30, 60]),
            "status": "active",
            "created_at": gen_date_past(30, 180)
        }
        clients.append(client)
    
    await db.clients.insert_many(clients)
    print(f"Created {len(clients)} clients")
    return clients


async def create_trips(tenant_id, user_id):
    """Create trips between Johannesburg and Nairobi."""
    trips = []
    
    # Mix of JHB -> NBO and NBO -> JHB trips
    trip_configs = [
        # Older completed trips
        {"route": ["Johannesburg", "Nairobi"], "status": "closed", "age": (60, 90)},
        {"route": ["Nairobi", "Johannesburg"], "status": "closed", "age": (50, 80)},
        {"route": ["Johannesburg", "Nairobi"], "status": "closed", "age": (40, 70)},
        {"route": ["Nairobi", "Johannesburg"], "status": "delivered", "age": (30, 50)},
        # Recent delivered trips
        {"route": ["Johannesburg", "Nairobi"], "status": "delivered", "age": (15, 30)},
        {"route": ["Nairobi", "Johannesburg"], "status": "delivered", "age": (10, 25)},
        # In transit
        {"route": ["Johannesburg", "Nairobi"], "status": "in_transit", "age": (3, 10)},
        {"route": ["Nairobi", "Johannesburg"], "status": "in_transit", "age": (2, 8)},
        # Loading
        {"route": ["Johannesburg", "Nairobi"], "status": "loading", "age": (1, 5)},
        {"route": ["Nairobi", "Johannesburg"], "status": "loading", "age": (1, 4)},
        # Planning
        {"route": ["Johannesburg", "Nairobi"], "status": "planning", "age": (0, 3)},
        {"route": ["Nairobi", "Johannesburg"], "status": "planning", "age": (0, 2)},
    ]
    
    for i, config in enumerate(trip_configs):
        trip_num = f"SH-2025-{str(i+1).zfill(3)}"
        created = gen_date_past(config["age"][0], config["age"][1])
        
        trip = {
            "id": gen_id(),
            "tenant_id": tenant_id,
            "trip_number": trip_num,
            "route": config["route"],
            "departure_date": gen_date_future(1, 14) if config["status"] == "planning" else gen_date_past(1, 30),
            "status": config["status"],
            "capacity_kg": random.choice([8000, 10000, 12000, 15000, 20000]),
            "capacity_cbm": random.choice([30, 40, 50, 60]),
            "vehicle_id": None,
            "driver_id": None,
            "notes": f"Shipment from {config['route'][0]} to {config['route'][-1]}",
            "created_by": user_id,
            "created_at": created
        }
        trips.append(trip)
    
    await db.trips.insert_many(trips)
    print(f"Created {len(trips)} trips")
    return trips


async def create_shipments_and_invoices(tenant_id, user_id, clients, trips, warehouses):
    """Create 400 shipments distributed across trips + some unassigned warehouse parcels."""
    
    jhb_warehouse = next(w for w in warehouses if "Johannesburg" in w["name"])
    nbo_warehouse = next(w for w in warehouses if "Nairobi" in w["name"])
    
    total_shipments = 0
    total_invoices = 0
    total_line_items = 0
    total_payments = 0
    
    # Target: ~350 shipments on trips, ~50 unassigned in warehouses
    target_per_trip = {
        "closed": 40,      # Older completed trips have more parcels
        "delivered": 35,
        "in_transit": 30,
        "loading": 25,
        "planning": 15,
    }
    
    for trip in trips:
        parcels_for_trip = target_per_trip.get(trip["status"], 20)
        # Add some randomness
        parcels_for_trip = max(10, parcels_for_trip + random.randint(-5, 5))
        
        # Pick origin warehouse based on route
        origin = trip["route"][0]
        origin_warehouse = jhb_warehouse if "Johannesburg" in origin else nbo_warehouse
        
        # Select random clients for this trip
        num_clients = random.randint(5, 12)
        trip_clients = random.sample(clients, min(num_clients, len(clients)))
        
        # Distribute parcels among clients
        parcels_distributed = 0
        client_index = 0
        
        while parcels_distributed < parcels_for_trip:
            client = trip_clients[client_index % len(trip_clients)]
            client_index += 1
            
            # 1-5 parcels per client per trip
            num_parcels = min(random.randint(1, 5), parcels_for_trip - parcels_distributed)
            
            # Create invoice
            invoice_id = gen_id()
            invoice_num = f"INV-2025-{str(total_invoices + 1).zfill(4)}"
            
            # Determine invoice status based on trip status
            if trip["status"] in ["closed"]:
                inv_status = random.choices(
                    ["paid", "sent", "overdue"],
                    weights=[0.7, 0.15, 0.15]
                )[0]
            elif trip["status"] == "delivered":
                inv_status = random.choices(
                    ["paid", "sent", "overdue", "partial"],
                    weights=[0.4, 0.3, 0.15, 0.15]
                )[0]
            elif trip["status"] == "in_transit":
                inv_status = random.choices(
                    ["sent", "draft", "paid"],
                    weights=[0.5, 0.3, 0.2]
                )[0]
            elif trip["status"] == "loading":
                inv_status = random.choices(
                    ["draft", "sent"],
                    weights=[0.7, 0.3]
                )[0]
            else:
                inv_status = "draft"
            
            line_items = []
            invoice_total = 0
            
            for p_idx in range(num_parcels):
                weight = round(random.uniform(3, 200), 1)
                length = random.randint(10, 120)
                width = random.randint(10, 100)
                height = random.randint(5, 80)
                cbm = round((length * width * height) / 1000000, 4)
                vol_weight = round((length * width * height) / 5000, 2)
                
                # Shipment status based on trip
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
                
                shipment = {
                    "id": gen_id(),
                    "tenant_id": tenant_id,
                    "client_id": client["id"],
                    "trip_id": trip["id"],
                    "invoice_id": invoice_id if inv_status != "draft" else None,
                    "description": random.choice(ITEM_DESCRIPTIONS),
                    "destination": trip["route"][-1],
                    "total_pieces": random.randint(1, 5),
                    "total_weight": weight,
                    "total_cbm": cbm,
                    "quantity": 1,
                    "status": ship_status,
                    "warehouse_id": origin_warehouse["id"],
                    "recipient": f"Recipient for {client['name']}",
                    "recipient_phone": gen_phone_ke() if "Nairobi" in trip["route"][-1] else gen_phone_sa(),
                    "sender": client["name"],
                    "length_cm": length,
                    "width_cm": width,
                    "height_cm": height,
                    "volumetric_weight": vol_weight,
                    "parcel_sequence": p_idx + 1 if num_parcels > 1 else None,
                    "total_in_sequence": num_parcels if num_parcels > 1 else None,
                    "created_by": user_id,
                    "created_at": trip["created_at"],
                    "updated_at": trip["created_at"]
                }
                await db.shipments.insert_one(shipment)
                total_shipments += 1
                parcels_distributed += 1
                
                # Create line item
                rate = client.get("default_rate_value", ZAR_RATE)
                chargeable = max(weight, vol_weight)
                amount = round(chargeable * rate, 2)
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
                    "shipping_weight": chargeable,
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
                paid_amount = round(invoice_total * random.uniform(0.2, 0.7), 2)
            
            if inv_status == "overdue":
                due_date = (datetime.now(timezone.utc) - timedelta(days=random.randint(5, 60))).strftime("%Y-%m-%d")
            else:
                due_date = (datetime.now(timezone.utc) + timedelta(days=random.randint(7, 45))).strftime("%Y-%m-%d")
            
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
                "payment_terms": random.choice(["net_7", "net_14", "net_30"]),
                "comment": "",
                "client_name_snapshot": client["name"],
                "client_phone_snapshot": client.get("phone"),
                "client_email_snapshot": client.get("email"),
                "created_at": trip["created_at"]
            }
            await db.invoices.insert_one(invoice)
            total_invoices += 1
            
            # Create payment record if paid/partial
            if paid_amount > 0:
                payment = {
                    "id": gen_id(),
                    "tenant_id": tenant_id,
                    "client_id": client["id"],
                    "invoice_id": invoice_id,
                    "amount": paid_amount,
                    "payment_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                    "payment_method": random.choice(["bank_transfer", "cash", "mobile_money", "eft"]),
                    "reference": f"PAY-{random.randint(10000, 99999)}",
                    "notes": "Payment received",
                    "created_by": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.payments.insert_one(payment)
                total_payments += 1
    
    print(f"Created {total_shipments} trip shipments, {total_invoices} invoices, {total_line_items} line items, {total_payments} payments")
    
    # Now create unassigned warehouse parcels to reach 400 total
    remaining = max(0, 400 - total_shipments)
    if remaining > 0:
        unassigned = []
        for i in range(remaining):
            client = random.choice(clients)
            # Alternate between warehouses
            warehouse = jhb_warehouse if i % 2 == 0 else nbo_warehouse
            dest = "Nairobi" if "Johannesburg" in warehouse["name"] else "Johannesburg"
            weight = round(random.uniform(3, 150), 1)
            length = random.randint(10, 100)
            width = random.randint(10, 80)
            height = random.randint(5, 60)
            
            shipment = {
                "id": gen_id(),
                "tenant_id": tenant_id,
                "client_id": client["id"],
                "trip_id": None,
                "invoice_id": None,
                "description": random.choice(ITEM_DESCRIPTIONS),
                "destination": dest,
                "total_pieces": random.randint(1, 3),
                "total_weight": weight,
                "total_cbm": round((length * width * height) / 1000000, 4),
                "quantity": 1,
                "status": "warehouse",
                "warehouse_id": warehouse["id"],
                "recipient": f"Recipient {i+1}",
                "recipient_phone": gen_phone_ke() if dest == "Johannesburg" else gen_phone_sa(),
                "sender": client["name"],
                "length_cm": length,
                "width_cm": width,
                "height_cm": height,
                "created_by": user_id,
                "created_at": gen_date_past(1, 14),
                "updated_at": gen_date_past(1, 14)
            }
            unassigned.append(shipment)
        
        await db.shipments.insert_many(unassigned)
        print(f"Created {len(unassigned)} unassigned warehouse parcels")
        total_shipments += len(unassigned)
    
    print(f"\nTotal shipments created: {total_shipments}")


async def print_summary(tenant_id):
    """Print summary of seeded data."""
    print("\n" + "=" * 60)
    print("DATABASE SEED SUMMARY")
    print("=" * 60)
    
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
    
    print("\nShipment Status Breakdown:")
    for status in ["warehouse", "staged", "loaded", "in_transit", "arrived", "delivered", "collected"]:
        count = await db.shipments.count_documents({"tenant_id": tenant_id, "status": status})
        if count > 0:
            print(f"  - {status}: {count}")
    
    print("\nInvoice Status Breakdown:")
    for status in ["draft", "sent", "paid", "overdue", "partial"]:
        count = await db.invoices.count_documents({"tenant_id": tenant_id, "status": status})
        if count > 0:
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
    
    # Warehouse breakdown
    print("\nWarehouse Breakdown:")
    warehouses = await db.warehouses.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(10)
    for wh in warehouses:
        count = await db.shipments.count_documents({"tenant_id": tenant_id, "warehouse_id": wh["id"]})
        print(f"  - {wh['name']}: {count} parcels")
    
    print("\n" + "=" * 60)
    print("Seed complete! Ready for testing.")
    print("=" * 60)


async def main():
    """Main seeding function."""
    print("Starting database seed...")
    print(f"Database: {DB_NAME}")
    print(f"MongoDB: {MONGO_URL}")
    
    # Clear existing data
    print("\nClearing existing data...")
    await clear_data()
    
    # Get or create tenant and user
    tenant, user = await get_tenant_and_user()
    tenant_id = tenant["id"]
    user_id = user["id"]
    
    # Create warehouses
    print("\nCreating warehouses...")
    warehouses = await create_warehouses(tenant_id, user_id)
    
    # Create clients (50)
    print("\nCreating 50 clients...")
    clients = await create_clients(tenant_id, count=50)
    
    # Create trips (12 trips - JHB <-> NBO)
    print("\nCreating trips...")
    trips = await create_trips(tenant_id, user_id)
    
    # Create 400 shipments with invoices
    print("\nCreating 400 shipments with invoices...")
    await create_shipments_and_invoices(tenant_id, user_id, clients, trips, warehouses)
    
    # Print summary
    await print_summary(tenant_id)


if __name__ == "__main__":
    asyncio.run(main())

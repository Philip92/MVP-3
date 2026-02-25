"""
D-07 Comprehensive Seed Script for Servex Holdings
Seeds: 200+ clients, 5 trips, 500+ shipments, 60+ invoices
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import random
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

def now():
    return datetime.now(timezone.utc).isoformat()

def past(days=0, hours=0):
    return (datetime.now(timezone.utc) - timedelta(days=days, hours=hours)).isoformat()

FIRST_NAMES = ["James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda","David","Barbara",
               "William","Susan","Richard","Jessica","Joseph","Sarah","Thomas","Karen","Charles","Lisa",
               "Christopher","Nancy","Daniel","Betty","Matthew","Margaret","Anthony","Sandra","Mark","Ashley",
               "Donald","Dorothy","Steven","Kimberly","Paul","Emily","Andrew","Donna","Joshua","Michelle",
               "Kenneth","Carol","Kevin","Amanda","Brian","Melissa","George","Deborah","Timothy","Stephanie",
               "Ronald","Rebecca","Edward","Sharon","Jason","Laura","Jeffrey","Cynthia","Ryan","Kathleen",
               "Jacob","Amy","Gary","Angela","Nicholas","Shirley","Eric","Anna","Jonathan","Brenda",
               "Stephen","Pamela","Larry","Emma","Justin","Nicole","Scott","Helen","Brandon","Samantha",
               "Benjamin","Katherine","Samuel","Christine","Raymond","Debra","Gregory","Rachel","Frank","Carolyn",
               "Patrick","Janet","Alexander","Maria","Jack","Heather","Dennis","Diane","Jerry","Julie"]

LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
              "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
              "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson",
              "Walker","Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores",
              "Green","Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter","Roberts",
              "Banda","Phiri","Mwanza","Chirwa","Nkhata","Gondwe","Tembo","Chisale","Mbewe","Mvula",
              "Moyo","Dube","Ncube","Ndlovu","Sibanda","Nkosi","Dlamini","Zwane","Maseko","Ngwenya",
              "Osei","Mensah","Asante","Boateng","Darko","Owusu","Acheampong","Antwi","Adjei","Addo"]

COMPANIES = ["Tech Solutions Ltd","Fresh Imports","Global Trade Co","East Africa Goods","Safari Exports",
             "Nairobi Supplies","Lagos Freight","Cape Town Traders","Durban Logistics","Accra Merchants",
             "Kampala Distributors","Harare Wholesale","Lusaka Trading","Dar Es Salaam Imports","Cairo Exports",
             "West Africa Holdings","Pan African Trade","Sahara Logistics","Indian Ocean Freight","Southern Cross Ltd",
             "Highveld Supplies","Lowveld Traders","Bushveld Merchants","Bushwillow Exports","Acacia Imports",
             "Baobab Distributors","Marula Trading Co","Msasa Holdings","Umkhondo Freight","Ubuntu Logistics",
             "Nile Basin Exports","Great Rift Imports","Kilimanjaro Cargo","Serengeti Goods","Victoria Falls Trading",
             "Atlas Freight","Horizon Logistics","Pinnacle Exports","Summit Traders","Apex Imports", "None"]

DESCRIPTIONS = [
    "Electronics - Phones", "Clothing - Ladies Wear", "Shoes - Sports", "Food Supplements",
    "Auto Parts", "Cosmetics", "Books - Educational", "Textiles - Cotton", "Jewellery",
    "Medical Supplies", "Computer Accessories", "Kitchenware", "Furniture Parts", "Toys",
    "Sporting Goods", "Tools & Hardware", "Stationery", "Baby Products", "Pet Supplies",
    "Bedding & Linen", "Electrical Items", "Plumbing Fittings", "Gents Clothing", "Handbags",
    "Traditional Fabric", "Industrial Parts", "Packaging Materials", "Hair Products",
    "Food Items - Dry Goods", "Cleaning Products", "Farm Equipment Parts", "Bicycle Parts",
    "Plastic Containers", "Glass Items", "Rubber Products", "Paper Products", "Perfumes",
    "Bags & Luggage", "School Supplies", "Office Furniture", "Salon Equipment",
    "Photography Equipment", "Musical Instruments", "Artwork", "Crafts",
    "Welding Equipment", "Electrical Wire", "Steel Pipes", "Aluminium Sheets", "Cement Bags"
]

DESTINATIONS = ["Nairobi", "Mombasa", "Kisumu", "Kampala", "Dar Es Salaam", "Lusaka", "Harare", "Blantyre", "Lilongwe"]
WAREHOUSE_ROUTES = [
    ["Johannesburg", "Beitbridge", "Harare", "Lusaka"],
    ["Johannesburg", "Beitbridge", "Bulawayo"],
    ["Johannesburg", "Musina", "Harare", "Nairobi"],
    ["Johannesburg", "Beitbridge", "Blantyre"],
    ["Johannesburg", "Durban", "Maputo"]
]

async def get_or_create_tenant():
    tenant = await db.tenants.find_one({})
    if tenant:
        return tenant.get("id"), tenant.get("admin_user_id")
    return None, None

async def seed():
    tenant_id, admin_id = await get_or_create_tenant()
    if not tenant_id:
        print("No tenant found. Please ensure the app is set up first.")
        return

    print(f"Using tenant: {tenant_id}")

    # --- SEED 200+ CLIENTS ---
    existing_clients = await db.clients.count_documents({"tenant_id": tenant_id})
    clients_created = []

    if existing_clients < 200:
        print(f"Seeding clients (existing: {existing_clients})...")
        for i in range(200 - existing_clients):
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            company = random.choice(COMPANIES)
            phone = f"+27{random.randint(600000000, 799999999)}"
            whatsapp = phone if random.random() > 0.3 else ""
            currencies = ["ZAR", "KES"]
            cid = str(uuid.uuid4())
            doc = {
                "id": cid,
                "tenant_id": tenant_id,
                "name": f"{fn} {ln}",
                "company_name": company if company != "None" else None,
                "phone": phone,
                "whatsapp": whatsapp,
                "email": f"{fn.lower()}.{ln.lower()}{i}@example.com" if random.random() > 0.2 else None,
                "physical_address": f"{random.randint(1,999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm', 'Maple'])} Street",
                "billing_address": None,
                "vat_number": f"VAT{random.randint(1000000, 9999999)}" if random.random() > 0.7 else None,
                "payment_terms_days": random.choice([0, 7, 14, 30]),
                "default_currency": random.choice(currencies),
                "status": "active",
                "created_at": past(days=random.randint(30, 365)),
                "outstanding_balance": 0,
                "total_spent": 0
            }
            await db.clients.insert_one(doc)
            clients_created.append(doc)
        print(f"Created {len(clients_created)} new clients")
    else:
        print(f"Clients already sufficient ({existing_clients})")

    # Get all clients
    all_clients = await db.clients.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(300)
    print(f"Total clients: {len(all_clients)}")

    # --- GET WAREHOUSES ---
    warehouses = await db.warehouses.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(10)
    warehouse_ids = [w.get("id") for w in warehouses if w.get("id")]
    if not warehouse_ids:
        # Create 2 warehouses
        for wname in ["JHB Main Warehouse", "DBN Branch"]:
            wid = str(uuid.uuid4())
            await db.warehouses.insert_one({
                "id": wid, "tenant_id": tenant_id, "name": wname,
                "address": f"123 {wname} Road", "city": "Johannesburg",
                "status": "active", "created_at": now()
            })
            warehouse_ids.append(wid)
        print("Created 2 warehouses")

    # --- SEED 5 TRIPS (S03-S07) ---
    existing_trips = await db.trips.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(20)
    existing_numbers = [t.get("trip_number") for t in existing_trips]
    trip_specs = [
        {"number": "S03", "status": "arrived", "days_ago": 45, "route_idx": 0, "cap_kg": 2000, "cap_cbm": 12},
        {"number": "S04", "status": "in_transit", "days_ago": 5, "route_idx": 2, "cap_kg": 1800, "cap_cbm": 10},
        {"number": "S05", "status": "planning", "days_ago": -3, "route_idx": 1, "cap_kg": 2500, "cap_cbm": 14},
        {"number": "S06", "status": "closed", "days_ago": 90, "route_idx": 3, "cap_kg": 1500, "cap_cbm": 8},
        {"number": "S07", "status": "planning", "days_ago": -7, "route_idx": 4, "cap_kg": 2200, "cap_cbm": 11},
    ]

    trips = {}
    for spec in trip_specs:
        if spec["number"] in existing_numbers:
            t = next((t for t in existing_trips if t.get("trip_number") == spec["number"]), None)
            trips[spec["number"]] = t
            print(f"Trip {spec['number']} already exists")
        else:
            tid = str(uuid.uuid4())
            depart = past(days=spec["days_ago"]) if spec["days_ago"] > 0 else past(days=0)
            route = WAREHOUSE_ROUTES[spec["route_idx"]]
            doc = {
                "id": tid,
                "tenant_id": tenant_id,
                "trip_number": spec["number"],
                "status": spec["status"],
                "route": route,
                "departure_date": depart[:10],
                "actual_departure": depart if spec["status"] in ["in_transit", "arrived", "closed"] else None,
                "actual_arrival": past(days=spec["days_ago"] - 10) if spec["status"] in ["arrived", "closed"] else None,
                "capacity_kg": spec["cap_kg"],
                "capacity_cbm": spec["cap_cbm"],
                "warehouse_id": random.choice(warehouse_ids),
                "destination_warehouse_id": random.choice(warehouse_ids),
                "notes": f"Seed trip {spec['number']}",
                "created_at": past(days=spec["days_ago"] + 5)
            }
            await db.trips.insert_one(doc)
            trips[spec["number"]] = doc
            print(f"Created trip {spec['number']}")

    # --- SEED 500+ SHIPMENTS ---
    existing_shipments = await db.shipments.count_documents({"tenant_id": tenant_id})
    shipments_to_create = max(0, 500 - existing_shipments)
    print(f"Seeding {shipments_to_create} shipments (existing: {existing_shipments})...")

    trip_list = list(trips.values())
    new_shipments = []

    for i in range(shipments_to_create):
        cl = random.choice(all_clients)
        trip = random.choice(trip_list)
        trip_id = trip.get("id")
        days_ago = random.randint(1, 90)
        weight = round(random.uniform(0.5, 50) * random.choice([1, 1, 1, 2, 5, 10]), 2)
        has_dims = random.random() > 0.4
        l = round(random.uniform(20, 120), 0) if has_dims else None
        w = round(random.uniform(20, 80), 0) if has_dims else None
        h = round(random.uniform(10, 60), 0) if has_dims else None
        dest = random.choice(DESTINATIONS)
        desc = random.choice(DESCRIPTIONS)
        qty = random.randint(1, 20)
        trip_status = trip.get("status")
        # Assign parcel status based on trip status
        if trip_status == "arrived":
            status = random.choice(["arrived", "arrived", "delivered", "collected"])
        elif trip_status == "in_transit":
            status = "in_transit"
        elif trip_status == "closed":
            status = random.choice(["delivered", "collected"])
        else:  # planning
            status = random.choice(["warehouse", "warehouse", "staged"])

        sid = str(uuid.uuid4())
        barcode = f"SVX{random.randint(100000, 999999)}"
        doc = {
            "id": sid,
            "tenant_id": tenant_id,
            "client_id": cl.get("id"),
            "trip_id": trip_id,
            "warehouse_id": random.choice(warehouse_ids),
            "status": status,
            "description": desc,
            "quantity": qty,
            "total_weight": weight,
            "length_cm": l,
            "width_cm": w,
            "height_cm": h,
            "destination": dest,
            "recipient": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "recipient_phone": f"+254{random.randint(700000000, 799999999)}",
            "recipient_address": f"P.O. Box {random.randint(1000,9999)}, {dest}",
            "barcode": barcode,
            "invoice_id": None,  # Will be set when invoiced
            "invoice_number": None,
            "created_at": past(days=days_ago + random.randint(0, 5)),
            "notes": ""
        }
        new_shipments.append(doc)

    if new_shipments:
        await db.shipments.insert_many(new_shipments)
        print(f"Created {len(new_shipments)} shipments")

    # --- SEED 60+ INVOICES ---
    existing_invoices = await db.invoices.count_documents({"tenant_id": tenant_id})
    invoices_to_create = max(0, 65 - existing_invoices)
    print(f"Seeding {invoices_to_create} invoices (existing: {existing_invoices})...")

    # Get shipments per trip for invoicing
    all_shipments = await db.shipments.find({"tenant_id": tenant_id, "invoice_id": None}, {"_id": 0}).to_list(2000)
    shipments_by_trip = {}
    for s in all_shipments:
        tid = s.get("trip_id")
        if tid not in shipments_by_trip:
            shipments_by_trip[tid] = []
        shipments_by_trip[tid].append(s)

    inv_num = existing_invoices + 1
    new_invoices = []
    statuses = ["draft", "sent", "sent", "paid", "paid", "paid", "overdue"]

    for trip in trip_list:
        tid = trip.get("id")
        trip_shipments = shipments_by_trip.get(tid, [])
        if not trip_shipments:
            continue
        # Group shipments by client
        by_client = {}
        for s in trip_shipments[:100]:  # limit per trip
            cid = s.get("client_id")
            if cid not in by_client:
                by_client[cid] = []
            by_client[cid].append(s)

        for cid, c_ships in list(by_client.items())[:20]:  # max 20 clients per trip
            if invoices_to_create <= 0:
                break
            cl = next((c for c in all_clients if c.get("id") == cid), {})
            status = random.choice(statuses)
            days_ago = random.randint(5, 60)
            due_days = random.randint(-10, 30)  # negative = overdue
            if status == "overdue":
                due_days = -random.randint(5, 30)

            rate = random.uniform(8, 25)
            total_kg = sum(s.get("total_weight", 0) or 0 for s in c_ships)
            subtotal = round(total_kg * rate, 2)
            total = subtotal
            paid = total if status == "paid" else (round(total * random.uniform(0.3, 0.7), 2) if random.random() > 0.8 else 0)
            if paid > 0 and status not in ["paid"]:
                status = "partial"

            iid = str(uuid.uuid4())
            inv_number = f"INV-{inv_num:04d}"
            due_date = (datetime.now(timezone.utc) + timedelta(days=due_days)).date().isoformat()
            created_date = past(days=days_ago)

            inv_doc = {
                "id": iid,
                "tenant_id": tenant_id,
                "invoice_number": inv_number,
                "client_id": cid,
                "trip_id": tid,
                "client_name_snapshot": cl.get("name", ""),
                "client_phone_snapshot": cl.get("phone", ""),
                "status": status,
                "subtotal": subtotal,
                "adjustments": 0,
                "total": total,
                "paid_amount": paid,
                "currency": cl.get("default_currency", "ZAR"),
                "display_currency": cl.get("default_currency", "ZAR"),
                "issue_date": created_date[:10],
                "due_date": due_date,
                "created_at": created_date,
                "updated_at": created_date,
                "comment": ""
            }
            new_invoices.append(inv_doc)

            # Update shipments with invoice_id
            ship_ids = [s.get("id") for s in c_ships]
            await db.shipments.update_many(
                {"id": {"$in": ship_ids}, "tenant_id": tenant_id},
                {"$set": {"invoice_id": iid, "invoice_number": inv_number}}
            )

            inv_num += 1
            invoices_to_create -= 1

    if new_invoices:
        await db.invoices.insert_many(new_invoices)
        print(f"Created {len(new_invoices)} invoices")

    # Final counts
    tc = await db.clients.count_documents({"tenant_id": tenant_id})
    tt = await db.trips.count_documents({"tenant_id": tenant_id})
    ts = await db.shipments.count_documents({"tenant_id": tenant_id})
    ti = await db.invoices.count_documents({"tenant_id": tenant_id})
    print(f"\n=== FINAL COUNTS ===")
    print(f"Clients: {tc} | Trips: {tt} | Shipments: {ts} | Invoices: {ti}")
    print("Seed complete!")

asyncio.run(seed())

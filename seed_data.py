"""
MedTrack ERP — Seed Data Script
=================================
Creates a complete demo dataset via the live API so you can log in
as admin and test all Phase 1.1 + 1.2 + 1.3 features from the dashboard.

Usage:
    python seed_data.py

Admin Login Credentials (printed at the end):
    Email    : admin@medtrack-demo.com
    Password : Demo@1234
    Tenant ID: (printed by the script)
"""

import requests
import sys
import json
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000/api/v1"

ADMIN_EMAIL    = "admin@medtrack-demo.com"
ADMIN_PASSWORD = "Demo@1234"
TENANT_NAME    = "MedTrack Demo Hospital"
TENANT_SLUG    = "medtrack-demo"

SEPARATOR = "─" * 60


def step(msg: str):
    print(f"\n✦ {msg}")


def ok(msg: str):
    print(f"  ✅ {msg}")


def fail(msg: str, resp: requests.Response):
    print(f"  ❌ FAILED: {msg}")
    print(f"     Status : {resp.status_code}")
    print(f"     Body   : {resp.text[:300]}")
    sys.exit(1)


def post(url, json_body, headers=None, expected=(200, 201)):
    r = requests.post(url, json=json_body, headers=headers)
    if r.status_code not in expected:
        fail(url, r)
    return r.json()


def get(url, headers=None, params=None, expected=(200,)):
    r = requests.get(url, headers=headers, params=params)
    if r.status_code not in expected:
        fail(url, r)
    return r.json()


# ══════════════════════════════════════════════════════════════════════════════
print(SEPARATOR)
print("  MedTrack ERP — Seed Data")
print(SEPARATOR)

# ─── 1. Register Tenant & Admin User ─────────────────────────────────────────
step("Registering demo tenant + admin user …")
reg = post(
    f"{BASE_URL}/auth/register-tenant",
    {
        "name"             : TENANT_NAME,
        "slug"             : TENANT_SLUG,
        "admin_email"      : ADMIN_EMAIL,
        "admin_password"   : ADMIN_PASSWORD,
        "admin_first_name" : "Admin",
        "admin_last_name"  : "User",
        "plan"             : "professional",
    },
)
tenant_id    = reg["tenant_id"]
access_token = reg["access_token"]
headers      = {"Authorization": f"Bearer {access_token}"}
ok(f"Tenant   : {TENANT_NAME}  (id={tenant_id})")
ok(f"Admin    : {ADMIN_EMAIL}")

# ─── 2. Master Data: Units of Measure ────────────────────────────────────────
step("Creating Units of Measure …")
units = {}
for u in [
    {"code": "PCS",   "name": "Pieces"},
    {"code": "BOX",   "name": "Box"},
    {"code": "STRIP", "name": "Strip"},
    {"code": "VIAL",  "name": "Vial"},
    {"code": "KG",    "name": "Kilogram"},
    {"code": "LTR",   "name": "Litre"},
]:
    r = post(f"{BASE_URL}/inventory/master-data/units", u, headers=headers)
    units[u["code"]] = r["id"]
    ok(f"{u['code']} → {r['id']}")

# ─── 3. Master Data: Categories ──────────────────────────────────────────────
step("Creating Material Categories …")
cats = {}
for c in [
    {"name": "Pharmaceuticals",    "description": "Medicines and drugs"},
    {"name": "Surgical Supplies",  "description": "Surgical instruments and disposables"},
    {"name": "Medical Devices",    "description": "Serialized medical equipment"},
    {"name": "Consumables",        "description": "Single-use consumables"},
    {"name": "Raw Materials",      "description": "Manufacturing raw inputs"},
]:
    r = post(f"{BASE_URL}/inventory/master-data/categories", c, headers=headers)
    cats[c["name"]] = r["id"]
    ok(f"{c['name']} → {r['id']}")

# ─── 4. Master Data: Locations ───────────────────────────────────────────────
step("Creating Locations …")
locs = {}
for l in [
    {"name": "Main Warehouse",     "type": "warehouse", "is_active": True},
    {"name": "Pharmacy Store",     "type": "warehouse", "is_active": True},
    {"name": "Cold Chain Storage", "type": "warehouse", "is_active": True},
    {"name": "OT Store",           "type": "warehouse", "is_active": True},
    {"name": "Dispatch Bay",       "type": "warehouse", "is_active": True},
]:
    r = post(f"{BASE_URL}/inventory/master-data/locations", l, headers=headers)
    locs[l["name"]] = r["id"]
    ok(f"{l['name']} → {r['id']}")

# ─── 5. Standard Materials (no batch / serial) ───────────────────────────────
step("Creating standard materials …")
mats = {}

STANDARD = [
    {
        "code": "SALINE-500ML",  "name": "Normal Saline 500ml",
        "material_type": "finished",
        "category_id": cats["Consumables"],
        "base_unit_id": units["PCS"],
        "location_id": locs["Main Warehouse"],
        "reorder_level": 50,
        "description": "0.9% NaCl IV Fluid 500ml bag",
    },
    {
        "code": "GLOVES-L",  "name": "Surgical Gloves (Large)",
        "material_type": "finished",
        "category_id": cats["Surgical Supplies"],
        "base_unit_id": units["PCS"],
        "location_id": locs["OT Store"],
        "reorder_level": 100,
        "description": "Sterile latex surgical gloves size L",
    },
    {
        "code": "SYRINGE-5ML",  "name": "Syringe 5ml",
        "material_type": "finished",
        "category_id": cats["Consumables"],
        "base_unit_id": units["PCS"],
        "location_id": locs["Pharmacy Store"],
        "reorder_level": 200,
        "description": "Disposable 5ml hypodermic syringe",
    },
    {
        "code": "ETHANOL-70",  "name": "Isopropyl Alcohol 70%",
        "material_type": "raw",
        "category_id": cats["Raw Materials"],
        "base_unit_id": units["LTR"],
        "location_id": locs["Main Warehouse"],
        "reorder_level": 20,
        "description": "Disinfectant alcohol for surface cleaning",
    },
    {
        "code": "COTTON-ROLL",  "name": "Cotton Roll 500g",
        "material_type": "finished",
        "category_id": cats["Consumables"],
        "base_unit_id": units["KG"],
        "location_id": locs["OT Store"],
        "reorder_level": 10,
        "description": "Absorbent surgical cotton roll",
    },
]

for m in STANDARD:
    r = post(f"{BASE_URL}/inventory/materials", m, headers=headers)
    mats[m["code"]] = r["id"]
    ok(f"{m['code']} — {m['name']}")

# ─── 6. Add Stock for Standard Materials ─────────────────────────────────────
step("Adding stock for standard materials …")
STOCK = [
    ("SALINE-500ML",  500, units["PCS"]),
    ("GLOVES-L",      800, units["PCS"]),
    ("SYRINGE-5ML",  1200, units["PCS"]),
    ("ETHANOL-70",     50, units["LTR"]),
    ("COTTON-ROLL",    30, units["KG"]),
]
for code, qty, unit_id in STOCK:
    post(
        f"{BASE_URL}/inventory/transactions",
        {
            "material_id":       mats[code],
            "transaction_type":  "in",
            "quantity":          qty,
            "unit_id":           unit_id,
            "remarks":           "Opening stock — seed data",
        },
        headers=headers,
    )
    ok(f"{code}: +{qty}")

# Remove some stock to show transactions
step("Removing some stock (simulating consumption) …")
ISSUES = [
    ("SALINE-500ML",  30, units["PCS"],  "Issued to Ward A"),
    ("GLOVES-L",      50, units["PCS"],  "Issued to OT"),
    ("SYRINGE-5ML",  100, units["PCS"],  "Issued to ICU"),
    ("ETHANOL-70",     5, units["LTR"],  "Issued to Cleaning Dept"),
]
for code, qty, unit_id, remark in ISSUES:
    post(
        f"{BASE_URL}/inventory/transactions",
        {
            "material_id":       mats[code],
            "transaction_type":  "out",
            "quantity":          qty,
            "unit_id":           unit_id,
            "remarks":           remark,
        },
        headers=headers,
    )
    ok(f"{code}: -{qty}  ({remark})")

# ─── 7. Batch-Tracked Materials ──────────────────────────────────────────────
step("Creating batch-tracked pharmaceutical materials …")
BATCH_MEDS = [
    {
        "code": "AMOX-500MG", "name": "Amoxicillin 500mg Capsules",
        "material_type": "finished",
        "category_id": cats["Pharmaceuticals"],
        "base_unit_id": units["STRIP"],
        "location_id": locs["Pharmacy Store"],
        "is_batch_tracked": True,
        "reorder_level": 30,
        "description": "Antibiotic — batch & expiry tracked",
    },
    {
        "code": "PARA-650MG", "name": "Paracetamol 650mg Tablets",
        "material_type": "finished",
        "category_id": cats["Pharmaceuticals"],
        "base_unit_id": units["STRIP"],
        "location_id": locs["Pharmacy Store"],
        "is_batch_tracked": True,
        "reorder_level": 50,
        "description": "Analgesic/Antipyretic — batch & expiry tracked",
    },
    {
        "code": "INS-RAPID", "name": "Insulin Rapid Acting (Vial)",
        "material_type": "finished",
        "category_id": cats["Pharmaceuticals"],
        "base_unit_id": units["VIAL"],
        "location_id": locs["Cold Chain Storage"],
        "is_batch_tracked": True,
        "reorder_level": 10,
        "description": "Refrigerated insulin — cold chain, batch tracked",
    },
]
for m in BATCH_MEDS:
    r = post(f"{BASE_URL}/inventory/materials", m, headers=headers)
    mats[m["code"]] = r["id"]
    ok(f"{m['code']} — {m['name']}")

# ─── 8. Add Batch Stock (mix of near-expiry + healthy stock) ─────────────────
step("Adding batch stock …")
today = date.today()

BATCHES = [
    # Amoxicillin — 3 batches (one near-expiry in 15 days, one in 6 months, one in 2 years)
    ("AMOX-500MG", "AMX-2024-001", 200,  15),
    ("AMOX-500MG", "AMX-2024-002", 500, 180),
    ("AMOX-500MG", "AMX-2025-001", 800, 720),

    # Paracetamol — 2 batches
    ("PARA-650MG", "PAR-2024-A01", 300,  25),  # expiring in 25 days → alert!
    ("PARA-650MG", "PAR-2025-B01", 600, 365),

    # Insulin — 2 batches (one near-expiry in 20 days)
    ("INS-RAPID",  "INS-2024-001", 50,   20),  # near-expiry → alert!
    ("INS-RAPID",  "INS-2025-001", 120, 300),
]
for code, batch_num, qty, days_until_expiry in BATCHES:
    expiry = (today + timedelta(days=days_until_expiry)).isoformat()
    post(
        f"{BASE_URL}/inventory/batches/add-stock",
        {
            "material_id":  mats[code],
            "batch_number": batch_num,
            "quantity":     qty,
            "expiry_date":  expiry,
            "remarks":      "Opening batch stock — seed data",
        },
        headers=headers,
    )
    ok(f"{code} / {batch_num}: qty={qty}, expiry={expiry} (+{days_until_expiry}d)")

# Remove some batch stock to show consumption
step("Removing stock from batches (simulating dispense) …")
BATCH_ISSUES = [
    ("AMOX-500MG", "AMX-2024-001", 40,  "Dispensed to Ward B"),
    ("PARA-650MG", "PAR-2024-A01", 80,  "Dispensed to Emergency"),
    ("INS-RAPID",  "INS-2024-001", 10,  "Issued to Diabetic OPD"),
]
for code, batch_num, qty, remark in BATCH_ISSUES:
    post(
        f"{BASE_URL}/inventory/batches/remove-stock",
        {
            "material_id":  mats[code],
            "batch_number": batch_num,
            "quantity":     qty,
            "remarks":      remark,
        },
        headers=headers,
    )
    ok(f"{code} / {batch_num}: -{qty} ({remark})")

# ─── 9. Serialized Medical Devices ───────────────────────────────────────────
step("Creating serialized medical device materials …")
SERIAL_ITEMS = [
    {
        "code": "BP-MONITOR-01", "name": "Digital Blood Pressure Monitor",
        "material_type": "finished",
        "category_id": cats["Medical Devices"],
        "base_unit_id": units["PCS"],
        "location_id": locs["Main Warehouse"],
        "is_serialized": True,
        "description": "Omron HBP-1100 — serial tracked",
    },
    {
        "code": "PULSE-OX-01", "name": "Fingertip Pulse Oximeter",
        "material_type": "finished",
        "category_id": cats["Medical Devices"],
        "base_unit_id": units["PCS"],
        "location_id": locs["Main Warehouse"],
        "is_serialized": True,
        "description": "SpO2 monitor — serial tracked",
    },
    {
        "code": "GLUCOMETER-01", "name": "Glucometer Device",
        "material_type": "finished",
        "category_id": cats["Medical Devices"],
        "base_unit_id": units["PCS"],
        "location_id": locs["Pharmacy Store"],
        "is_serialized": True,
        "description": "Blood glucose meter — serial tracked",
    },
]
for m in SERIAL_ITEMS:
    r = post(f"{BASE_URL}/inventory/materials", m, headers=headers)
    mats[m["code"]] = r["id"]
    ok(f"{m['code']} — {m['name']}")

# ─── 10. Register Serial Numbers ──────────────────────────────────────────────
step("Registering serial numbers …")
SERIALS = {
    "BP-MONITOR-01": [
        "BP-2024-SN-001", "BP-2024-SN-002", "BP-2024-SN-003",
        "BP-2024-SN-004", "BP-2024-SN-005",
    ],
    "PULSE-OX-01": [
        "POX-2024-SN-001", "POX-2024-SN-002", "POX-2024-SN-003",
    ],
    "GLUCOMETER-01": [
        "GLU-2024-SN-001", "GLU-2024-SN-002", "GLU-2024-SN-003",
        "GLU-2024-SN-004",
    ],
}
for code, sns in SERIALS.items():
    post(
        f"{BASE_URL}/inventory/serial-numbers/add-stock",
        {
            "material_id":    mats[code],
            "serial_numbers": sns,
            "remarks":        "Asset registration — seed data",
        },
        headers=headers,
    )
    ok(f"{code}: {len(sns)} serials registered → {', '.join(sns)}")

# ─── 11. Issue some serials (show lifecycle in action) ────────────────────────
step("Issuing some serials (to show issued status on dashboard) …")
TO_ISSUE = [
    ("BP-2024-SN-001", "Issued to Ward A Nursing Station"),
    ("BP-2024-SN-002", "Issued to ICU"),
    ("POX-2024-SN-001", "Issued to Emergency Dept"),
    ("GLU-2024-SN-001", "Issued to Diabetic Clinic"),
    ("GLU-2024-SN-002", "Issued to OPD"),
]
for sn, remark in TO_ISSUE:
    post(
        f"{BASE_URL}/inventory/serial-numbers/issue",
        {"serial_number": sn, "remarks": remark},
        headers=headers,
    )
    ok(f"ISSUED: {sn} — {remark}")

# Return one to show RETURNED lifecycle
step("Returning one serial (show returned status) …")
post(
    f"{BASE_URL}/inventory/serial-numbers/return",
    {"serial_number": "BP-2024-SN-001", "remarks": "Returned from Ward A — needs calibration"},
    headers=headers,
)
ok("RETURNED: BP-2024-SN-001")

# ─── 12. Summary ─────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("  ✅  SEED DATA COMPLETE")
print(SEPARATOR)
print(f"""
  🏥  Tenant  : {TENANT_NAME}
  🔑  Tenant ID: {tenant_id}

  LOGIN CREDENTIALS
  ─────────────────
  Email    : {ADMIN_EMAIL}
  Password : {ADMIN_PASSWORD}
  Tenant ID: {tenant_id}

  WHAT'S IN THE DATABASE
  ───────────────────────
  Units of Measure : 6
  Categories       : 5
  Locations        : 5 (Main WH, Pharmacy, Cold Chain, OT, Dispatch)

  Standard Materials (5):
    SALINE-500ML  —  500 pcs  (−30 issued)
    GLOVES-L      —  800 pcs  (−50 issued)
    SYRINGE-5ML   — 1200 pcs  (−100 issued)
    ETHANOL-70    —   50 ltr  (−5 issued)
    COTTON-ROLL   —   30 kg

  Batch-Tracked Pharmaceuticals (3 materials, 7 batches):
    AMOX-500MG    — 3 batches  (1 near-expiry in 15d ⚠️)
    PARA-650MG    — 2 batches  (1 near-expiry in 25d ⚠️)
    INS-RAPID     — 2 batches  (1 near-expiry in 20d ⚠️)
    → Run GET /inventory/batches/expiring?days=30 to see 3 alerts

  Serialized Medical Devices (3 materials, 12 serials):
    BP-MONITOR-01  — 5 serials  (2 ISSUED, 1 RETURNED, 2 IN_STOCK)
    PULSE-OX-01    — 3 serials  (1 ISSUED, 2 IN_STOCK)
    GLUCOMETER-01  — 4 serials  (2 ISSUED, 2 IN_STOCK)

  Total Inventory Transactions: ~20 (add + remove operations)
""")
print(SEPARATOR)
print("  Open http://localhost:5173 and log in with the credentials above")
print(SEPARATOR)

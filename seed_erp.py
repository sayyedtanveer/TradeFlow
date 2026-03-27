"""
MedTrack ERP — Comprehensive ERP Seed Data (Phase 2+)
=======================================================
Creates a rich ERP dataset including:
  - Full product catalog (Raw, Semi-finished, Finished goods)
  - Item variants with pricing and costs
  - Workstations and Operations (Routing)
  - Bills of Materials (BOMs) for multiple products
  - Simulated sales dispatches

Usage:
    python seed_erp.py

ENV: Assumes server is running at http://127.0.0.1:8000

AFTER RUNNING: Set tenant currency in DB:
  UPDATE tenants SET currency_code='INR', currency_symbol='₹'
  WHERE id='<printed tenant_id>';
"""

import requests
import sys
import io

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')

from datetime import date, timedelta

BASE_URL   = "http://127.0.0.1:8000/api/v1"

ADMIN_EMAIL    = "admin@synapse-erp-v16.com"
ADMIN_PASSWORD = "Erp@1234"
TENANT_NAME    = "Synapse Manufacturing Pvt Ltd"
TENANT_SLUG    = "synapse-mfg-v16"

SEP = "─" * 65


def step(msg):   print(f"\n✦ {msg}")
def ok(msg):     print(f"  ✅ {msg}")
def warn(msg):   print(f"  ⚠️  {msg}")

def fail(msg, resp):
    print(f"  ❌ FAILED: {msg}")
    print(f"     Status : {resp.status_code}")
    print(f"     Body   : {resp.text[:500]}")
    sys.exit(1)

def post(url, body, headers=None, expected=(200, 201)):
    r = requests.post(url, json=body, headers=headers)
    if r.status_code not in expected:
        fail(url, r)
    return r.json()

def get(url, headers=None, params=None, expected=(200,)):
    r = requests.get(url, headers=headers, params=params)
    if r.status_code not in expected:
        fail(url, r)
    return r.json()

def put(url, body, headers=None, expected=(200,)):
    r = requests.put(url, json=body, headers=headers)
    if r.status_code not in expected:
        fail(url, r)
    return r.json()


# ══════════════════════════════════════════════════════════════════════════════
print(SEP)
print("  Synapse Manufacturing ERP — Full Seed Data")
print(SEP)

# ─── 1. Register Tenant & Admin User ─────────────────────────────────────────
step("Registering tenant + admin …")
reg = post(
    f"{BASE_URL}/auth/register-tenant",
    {
        "name"             : TENANT_NAME,
        "slug"             : TENANT_SLUG,
        "admin_email"      : ADMIN_EMAIL,
        "admin_password"   : ADMIN_PASSWORD,
        "admin_first_name" : "Rohan",
        "admin_last_name"  : "Mehta",
        "plan"             : "professional",
    },
)
tenant_id    = reg["tenant_id"]
access_token = reg["access_token"]
headers      = {"Authorization": f"Bearer {access_token}"}
ok(f"Tenant : {TENANT_NAME}  (id={tenant_id})")
ok(f"Admin  : {ADMIN_EMAIL}")

# ─── 2. Units of Measure ─────────────────────────────────────────────────────
step("Creating Units of Measure …")
units = {}
for u in [
    {"code": "PCS",  "name": "Pieces"},
    {"code": "KG",   "name": "Kilogram"},
    {"code": "LTR",  "name": "Litre"},
    {"code": "MTR",  "name": "Metre"},
    {"code": "BOX",  "name": "Box"},
    {"code": "ROLL", "name": "Roll"},
    {"code": "GM",   "name": "Gram"},
    {"code": "ML",   "name": "Millilitre"},
    {"code": "PKT",  "name": "Packet"},
    {"code": "SET",  "name": "Set"},
]:
    r = post(f"{BASE_URL}/inventory/master-data/units", u, headers=headers)
    units[u["code"]] = r["id"]
    ok(f"{u['code']} → {r['id']}")

# ─── 3. Categories ────────────────────────────────────────────────────────────
step("Creating Categories …")
cats = {}
for c in [
    {"name": "Raw Materials",        "description": "Basic inputs for manufacturing"},
    {"name": "Packaging Materials",  "description": "Boxes, bottles, labels, films"},
    {"name": "Semi-Finished Goods",  "description": "WIP intermediate assemblies"},
    {"name": "Finished Goods",       "description": "Ready-to-sell products"},
    {"name": "Electronic Components","description": "PCBs, ICs, connectors"},
    {"name": "Metal Parts",          "description": "Machined and fabricated metal parts"},
    {"name": "Plastic Parts",        "description": "Injection-moulded plastic parts"},
    {"name": "Consumables",          "description": "Factory consumables"},
]:
    r = post(f"{BASE_URL}/inventory/master-data/categories", c, headers=headers)
    cats[c["name"]] = r["id"]
    ok(f"{c['name']} → {r['id']}")

# ─── 4. Locations ─────────────────────────────────────────────────────────────
step("Creating Locations …")
locs = {}
for l in [
    {"name": "Raw Material Store",   "type": "warehouse", "is_active": True},
    {"name": "Finished Goods Store", "type": "warehouse", "is_active": True},
    {"name": "WIP Store",            "type": "warehouse", "is_active": True},
    {"name": "Packaging Store",      "type": "warehouse", "is_active": True},
    {"name": "Dispatch Bay",         "type": "warehouse", "is_active": True},
    {"name": "QC Hold Area",         "type": "warehouse", "is_active": True},
]:
    r = post(f"{BASE_URL}/inventory/master-data/locations", l, headers=headers)
    locs[l["name"]] = r["id"]
    ok(f"{l['name']} → {r['id']}")

# ─── 5. Raw Materials (Inventory) ─────────────────────────────────────────────
step("Creating raw materials …")
mats = {}
RAW_MATS = [
    # Electronic Components
    {"code": "PCB-MAIN-001",    "name": "Main PCB Assembly",            "material_type": "raw", "category_id": cats["Electronic Components"], "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 50,   "current_cost": 850,  "description": "Main circuit board for controller unit"},
    {"code": "IC-ATMEGA-328",   "name": "ATmega328P Microcontroller",   "material_type": "raw", "category_id": cats["Electronic Components"], "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 200,  "current_cost": 120,  "description": "8-bit AVR microcontroller IC"},
    {"code": "CAP-100UF",       "name": "Capacitor 100µF 25V",          "material_type": "raw", "category_id": cats["Electronic Components"], "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 500,  "current_cost": 4,    "description": "Electrolytic capacitor"},
    {"code": "RES-10K",         "name": "Resistor 10kΩ 1/4W",          "material_type": "raw", "category_id": cats["Electronic Components"], "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 1000, "current_cost": 0.5,  "description": "Carbon film resistor"},
    {"code": "DISP-LCD-16X2",   "name": "LCD Display 16x2 Blue",        "material_type": "raw", "category_id": cats["Electronic Components"], "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 100,  "current_cost": 95,   "description": "16x2 character LCD module"},
    {"code": "SENSOR-TEMP-NTC", "name": "NTC Temperature Sensor 10kΩ", "material_type": "raw", "category_id": cats["Electronic Components"], "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 200,  "current_cost": 35,   "description": "10kΩ NTC thermistor"},
    # Metal Parts
    {"code": "ALUM-PLATE-2MM",  "name": "Aluminium Plate 2mm (1x1m)",  "material_type": "raw", "category_id": cats["Metal Parts"],           "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 20,   "current_cost": 750,  "description": "6061 grade aluminium sheet"},
    {"code": "STEEL-ROD-10MM",  "name": "Steel Rod 10mm dia (1m)",     "material_type": "raw", "category_id": cats["Metal Parts"],           "base_unit_id": units["MTR"], "location_id": locs["Raw Material Store"], "reorder_level": 50,   "current_cost": 180,  "description": "MS round bar"},
    {"code": "SCREW-M3-10MM",   "name": "Screw M3 x 10mm SS",          "material_type": "raw", "category_id": cats["Metal Parts"],           "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 2000, "current_cost": 1.5,  "description": "Stainless steel pan head screw"},
    # Plastic Parts
    {"code": "ABS-HOUSING-A",   "name": "ABS Enclosure Top Shell",      "material_type": "raw", "category_id": cats["Plastic Parts"],         "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 100,  "current_cost": 65,   "description": "Injection-moulded ABS top cover"},
    {"code": "ABS-HOUSING-B",   "name": "ABS Enclosure Bottom Shell",   "material_type": "raw", "category_id": cats["Plastic Parts"],         "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 100,  "current_cost": 55,   "description": "Injection-moulded ABS base"},
    {"code": "BUTTON-TACTILE",  "name": "Tactile Push Button 6x6mm",   "material_type": "raw", "category_id": cats["Plastic Parts"],         "base_unit_id": units["PCS"], "location_id": locs["Raw Material Store"], "reorder_level": 500,  "current_cost": 3,    "description": "6x6mm tactile switch"},
    # Packaging
    {"code": "CARTON-MED",      "name": "Carton Box 30x20x15cm",        "material_type": "raw", "category_id": cats["Packaging Materials"],   "base_unit_id": units["PCS"], "location_id": locs["Packaging Store"],   "reorder_level": 200,  "current_cost": 22,   "description": "Single-wall corrugated carton"},
    {"code": "FOAM-SHEET-5MM",  "name": "PE Foam Sheet 5mm",            "material_type": "raw", "category_id": cats["Packaging Materials"],   "base_unit_id": units["PCS"], "location_id": locs["Packaging Store"],   "reorder_level": 100,  "current_cost": 18,   "description": "Protective polyethylene foam insert"},
    {"code": "LABEL-PROD",      "name": "Product Label (self-adhesive)","material_type": "raw", "category_id": cats["Packaging Materials"],   "base_unit_id": units["PCS"], "location_id": locs["Packaging Store"],   "reorder_level": 500,  "current_cost": 2,    "description": "Printed product label 10x6cm"},
    {"code": "MANUAL-A4",       "name": "User Manual A4 8-page",        "material_type": "raw", "category_id": cats["Packaging Materials"],   "base_unit_id": units["PCS"], "location_id": locs["Packaging Store"],   "reorder_level": 200,  "current_cost": 8,    "description": "Printed user instruction booklet"},
]
for m in RAW_MATS:
    r = post(f"{BASE_URL}/inventory/materials", m, headers=headers)
    mats[m["code"]] = r["id"]
    ok(f"  {m['code']} — {m['name']}")

# ─── 6. Opening Stock ─────────────────────────────────────────────────────────
step("Adding opening raw material stock …")
STOCK = [
    ("PCB-MAIN-001",    250,  "PCS"),
    ("IC-ATMEGA-328",   500,  "PCS"),
    ("CAP-100UF",      3000,  "PCS"),
    ("RES-10K",        8000,  "PCS"),
    ("DISP-LCD-16X2",   400,  "PCS"),
    ("SENSOR-TEMP-NTC", 600,  "PCS"),
    ("ALUM-PLATE-2MM",   80,  "PCS"),
    ("STEEL-ROD-10MM",  120,  "MTR"),
    ("SCREW-M3-10MM",  5000,  "PCS"),
    ("ABS-HOUSING-A",   600,  "PCS"),
    ("ABS-HOUSING-B",   600,  "PCS"),
    ("BUTTON-TACTILE", 2000,  "PCS"),
    ("CARTON-MED",      800,  "PCS"),
    ("FOAM-SHEET-5MM",  800,  "PCS"),
    ("LABEL-PROD",     1500,  "PCS"),
    ("MANUAL-A4",      1000,  "PCS"),
]
for code, qty, unit_key in STOCK:
    post(
        f"{BASE_URL}/inventory/transactions",
        {"material_id": mats[code], "transaction_type": "in", "quantity": qty, "unit_id": units[unit_key], "remarks": "Opening stock — ERP seed"},
        headers=headers,
    )
    ok(f"{code}: +{qty} {unit_key}")

# ─── 7. Item Templates ────────────────────────────────────────────────────────
step("Creating product templates …")
templates = {}
TEMPLATES = [
    {
        "code": "SYN-CTRL-100",
        "name": "Synapse Temperature Controller",
        "description": "Industrial PID temperature controller with LCD display and multi-sensor support.",
        "category_id": cats["Finished Goods"],
        "base_unit_id": units["PCS"],
        "attributes": [
            {"key": "INPUT_TYPE", "label": "Input Type",  "values": ["NTC", "PT100", "Thermocouple K"]},
            {"key": "OUTPUT",     "label": "Output",      "values": ["Relay", "SSR", "4-20mA"]},
            {"key": "VOLTAGE",    "label": "Voltage",     "values": ["230V AC", "110V AC", "24V DC"]},
        ],
    },
    {
        "code": "SYN-LOGGER-200",
        "name": "Synapse Data Logger",
        "description": "8-channel analog input data logger with SD card storage and optional WiFi.",
        "category_id": cats["Finished Goods"],
        "base_unit_id": units["PCS"],
        "attributes": [
            {"key": "CHANNELS",      "label": "Channels",     "values": ["4-channel", "8-channel", "16-channel"]},
            {"key": "CONNECTIVITY",  "label": "Connectivity", "values": ["USB Only", "USB + WiFi"]},
            {"key": "MEMORY",        "label": "Memory",       "values": ["8GB SD", "32GB SD"]},
        ],
    },
    {
        "code": "SYN-RELAY-300",
        "name": "Synapse Smart Relay Module",
        "description": "4/8-channel WiFi-controlled smart relay module for industrial automation.",
        "category_id": cats["Finished Goods"],
        "base_unit_id": units["PCS"],
        "attributes": [
            {"key": "CHANNELS",  "label": "Channels",  "values": ["4-channel", "8-channel"]},
            {"key": "PROTOCOL",  "label": "Protocol",  "values": ["MQTT", "Modbus RTU", "MQTT + Modbus"]},
        ],
    },
    {
        "code": "SYN-SENSOR-400",
        "name": "Synapse Wireless Sensor Node",
        "description": "Battery-powered wireless sensor node for IoT monitoring.",
        "category_id": cats["Finished Goods"],
        "base_unit_id": units["PCS"],
        "attributes": [
            {"key": "SENSOR_TYPE", "label": "Sensor Type",  "values": ["Temp+Humidity", "CO2+Temp", "Vibration"]},
            {"key": "RADIO",       "label": "Radio",        "values": ["LoRa 868MHz", "Zigbee 2.4GHz"]},
            {"key": "BATTERY",     "label": "Battery Life", "values": ["1 Year", "3 Year"]},
        ],
    },
    {
        "code": "SYN-SUBASSY-PCB",
        "name": "Controller PCB Sub-Assembly",
        "description": "Populated PCB sub-assembly (WIP) shared across the controller family.",
        "category_id": cats["Semi-Finished Goods"],
        "base_unit_id": units["PCS"],
        "attributes": [
            {"key": "REVISION", "label": "Revision", "values": ["Rev A", "Rev B", "Rev C"]},
        ],
    },
    {
        "code": "SYN-ACC-KIT",
        "name": "Installation Accessories Kit",
        "description": "Bundled kit: mounting screws, terminal block covers, ferrite beads.",
        "category_id": cats["Finished Goods"],
        "base_unit_id": units["SET"],
        "attributes": [
            {"key": "TYPE", "label": "Type", "values": ["Standard", "DIN Rail"]},
        ],
    },
]
for t in TEMPLATES:
    r = post(f"{BASE_URL}/products/templates", t, headers=headers)
    templates[t["code"]] = r["id"]
    ok(f"{t['code']} → {r['id']}")

# ─── 8. Item Variants ─────────────────────────────────────────────────────────
step("Creating item variants …")
variants = {}
VARIANTS = [
    # Temperature Controller — 3 variants
    {"template": "SYN-CTRL-100",    "attribute_values": {"INPUT_TYPE": "NTC",            "OUTPUT": "Relay", "VOLTAGE": "230V AC"},  "standard_cost": 1250, "selling_price": 2499, "_key": "CTRL-NTC-R-230"},
    {"template": "SYN-CTRL-100",    "attribute_values": {"INPUT_TYPE": "PT100",          "OUTPUT": "SSR",   "VOLTAGE": "230V AC"},  "standard_cost": 1380, "selling_price": 2749, "_key": "CTRL-PT100-S-230"},
    {"template": "SYN-CTRL-100",    "attribute_values": {"INPUT_TYPE": "Thermocouple K", "OUTPUT": "4-20mA","VOLTAGE": "24V DC"},   "standard_cost": 1450, "selling_price": 2999, "_key": "CTRL-K-MA-24"},
    # Data Logger — 2 variants
    {"template": "SYN-LOGGER-200",  "attribute_values": {"CHANNELS": "4-channel",  "CONNECTIVITY": "USB Only",  "MEMORY": "8GB SD"},  "standard_cost": 2100, "selling_price": 3999, "_key": "LOG-4-U-8"},
    {"template": "SYN-LOGGER-200",  "attribute_values": {"CHANNELS": "8-channel",  "CONNECTIVITY": "USB + WiFi","MEMORY": "32GB SD"}, "standard_cost": 2800, "selling_price": 5499, "_key": "LOG-8-W-32"},
    # Smart Relay — 3 variants
    {"template": "SYN-RELAY-300",   "attribute_values": {"CHANNELS": "4-channel",  "PROTOCOL": "MQTT"},          "standard_cost": 850,  "selling_price": 1799, "_key": "RELAY-4-MQTT"},
    {"template": "SYN-RELAY-300",   "attribute_values": {"CHANNELS": "8-channel",  "PROTOCOL": "Modbus RTU"},    "standard_cost": 1100, "selling_price": 2299, "_key": "RELAY-8-MODB"},
    {"template": "SYN-RELAY-300",   "attribute_values": {"CHANNELS": "8-channel",  "PROTOCOL": "MQTT + Modbus"},"standard_cost": 1300, "selling_price": 2699, "_key": "RELAY-8-DUAL"},
    # Wireless Sensor — 2 variants
    {"template": "SYN-SENSOR-400",  "attribute_values": {"SENSOR_TYPE": "Temp+Humidity", "RADIO": "LoRa 868MHz",   "BATTERY": "1 Year"}, "standard_cost": 650,  "selling_price": 1399, "_key": "SENS-TH-LO-1Y"},
    {"template": "SYN-SENSOR-400",  "attribute_values": {"SENSOR_TYPE": "CO2+Temp",      "RADIO": "Zigbee 2.4GHz", "BATTERY": "3 Year"}, "standard_cost": 920,  "selling_price": 1899, "_key": "SENS-CO2-ZB-3Y"},
    # PCB Sub-Assembly — 1 variant
    {"template": "SYN-SUBASSY-PCB", "attribute_values": {"REVISION": "Rev B"},           "standard_cost": 550,  "selling_price": None,  "_key": "SUBPCB-B"},
    # Accessories — 2 variants
    {"template": "SYN-ACC-KIT",     "attribute_values": {"TYPE": "Standard"},             "standard_cost": 85,   "selling_price": 199,   "_key": "ACC-STD"},
    {"template": "SYN-ACC-KIT",     "attribute_values": {"TYPE": "DIN Rail"},             "standard_cost": 120,  "selling_price": 249,   "_key": "ACC-DIN"},
]
for v in VARIANTS:
    body = {
        "attribute_values": v["attribute_values"],
        "base_unit_id":     units["SET"] if v["template"] == "SYN-ACC-KIT" else units["PCS"],
        "standard_cost":    v["standard_cost"],
    }
    if v.get("selling_price"):
        body["selling_price"] = v["selling_price"]
    r = post(f"{BASE_URL}/products/templates/{templates[v['template']]}/variants", body, headers=headers)
    variants[v["_key"]] = r["id"]
    ok(f"  {v['_key']} → {r['id']}")

# ─── 9. Workstations ─────────────────────────────────────────────────────────
step("Creating Workstations …")
wss = {}
WS_LIST = [
    {"name": "SMT Line 1",        "code": "V5-SMT-L1",  "description": "Surface mount PCB assembly line", "hourly_rate": 1200, "is_active": True},
    {"name": "SMT Line 2",        "code": "V5-SMT-L2",  "description": "SMT line with AOI inspection",    "hourly_rate": 1350, "is_active": True},
    {"name": "Through-Hole Line", "code": "V5-THL-01",  "description": "Through-hole component line",     "hourly_rate": 800,  "is_active": True},
    {"name": "Soldering Station", "code": "V5-SOL-01",  "description": "Wave soldering machine",          "hourly_rate": 600,  "is_active": True},
    {"name": "Housing Assembly",  "code": "V5-HSG-ASY", "description": "Mechanical assembly station",     "hourly_rate": 450,  "is_active": True},
    {"name": "Test Bench 1",      "code": "V5-TST-B1",  "description": "Functional test station",         "hourly_rate": 700,  "is_active": True},
    {"name": "QC Inspection",     "code": "V5-QC-INS",  "description": "Quality inspection station",      "hourly_rate": 500,  "is_active": True},
    {"name": "Packaging Line",    "code": "V5-PKG-LN",  "description": "Final packaging station",         "hourly_rate": 350,  "is_active": True},
]
for ws in WS_LIST:
    r = post(
        f"{BASE_URL}/workstations",
        {
            "code": ws["code"],
            "name": ws["name"],
            "hourly_rate": ws["hourly_rate"],
        },
        headers=headers
    )
    wss[ws["code"]] = r
    ok(f"  {ws['code']} — {ws['name']}")

# ─── 10. Operations ───────────────────────────────────────────────────────────
step("Creating Operations …")
ops = {}
OPS_LIST = [
    {"name": "SMT Component Placement", "code": "OP-SMT-PLACE", "workstation": "V5-SMT-L1",  "setup_time": 30, "run_time": 45},
    {"name": "SMT Reflow Soldering",    "code": "OP-SMT-REFLO", "workstation": "V5-SMT-L1",  "setup_time": 20, "run_time": 25},
    {"name": "AOI Inspection",          "code": "OP-AOI",       "workstation": "V5-SMT-L2",  "setup_time": 10, "run_time": 15},
    {"name": "Through-Hole Insertion",  "code": "OP-THL-INS",   "workstation": "V5-THL-01",  "setup_time": 15, "run_time": 30},
    {"name": "Wave Soldering",          "code": "OP-WAVE-SOL",  "workstation": "V5-SOL-01",  "setup_time": 20, "run_time": 20},
    {"name": "Housing Assembly",        "code": "OP-HSG-ASY",   "workstation": "V5-HSG-ASY", "setup_time": 10, "run_time": 20},
    {"name": "Functional Testing",      "code": "OP-FUNC-TEST", "workstation": "V5-TST-B1",  "setup_time": 5,  "run_time": 30},
    {"name": "Quality Check",           "code": "OP-QC-CHECK",  "workstation": "V5-QC-INS",  "setup_time": 5,  "run_time": 15},
    {"name": "Final Packaging",         "code": "OP-PKG-FINAL", "workstation": "V5-PKG-LN",  "setup_time": 5,  "run_time": 10},
    {"name": "Firmware Flash",          "code": "OP-FW-FLASH",  "workstation": "V5-TST-B1",  "setup_time": 10, "run_time": 15},
]
for op in OPS_LIST:
    r = post(
        f"{BASE_URL}/operations",
        {
            "name": op["name"],
            "workstation_id": wss[op["workstation"]],
            "setup_time": op["setup_time"], 
            "run_time": op["run_time"],
        },
        headers=headers,
    )
    ops[op["code"]] = r
    ok(f"  {op['code']} — {op['name']}")

# ─── 11. BOMs ─────────────────────────────────────────────────────────────────
step("Creating Bills of Materials …")
today_iso = date.today().isoformat()

def create_bom(template_code, lines, operations, version="v1.0"):
    tpl_id = templates[template_code]
    bom = post(
        f"{BASE_URL}/products/{tpl_id}/boms",
        {"version": version, "valid_from": f"{today_iso}T00:00:00", "template_id": tpl_id, "lines": lines},
        headers=headers,
    )
    bom_id = bom["id"]
    for i, op_code in enumerate(operations):
        post(
            f"{BASE_URL}/boms/{bom_id}/operations",
            {"operation_id": ops[op_code], "sequence": (i + 1) * 10, "notes": ""},
            headers=headers,
        )
    post(f"{BASE_URL}/boms/{bom_id}/activate", {}, headers=headers)
    return bom_id

# BOM 1: Temperature Controller
step("  BOM: SYN-CTRL-100 …")
ctrl_bom = create_bom(
    "SYN-CTRL-100",
    lines=[
        {"material_id": mats["PCB-MAIN-001"],    "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["IC-ATMEGA-328"],   "quantity": 2,  "unit_id": units["PCS"]},
        {"material_id": mats["CAP-100UF"],       "quantity": 8,  "unit_id": units["PCS"]},
        {"material_id": mats["RES-10K"],         "quantity": 12, "unit_id": units["PCS"]},
        {"material_id": mats["DISP-LCD-16X2"],   "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["SENSOR-TEMP-NTC"], "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["ABS-HOUSING-A"],   "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["ABS-HOUSING-B"],   "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["BUTTON-TACTILE"],  "quantity": 4,  "unit_id": units["PCS"]},
        {"material_id": mats["SCREW-M3-10MM"],   "quantity": 8,  "unit_id": units["PCS"]},
        {"material_id": mats["CARTON-MED"],      "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["FOAM-SHEET-5MM"],  "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["LABEL-PROD"],      "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["MANUAL-A4"],       "quantity": 1,  "unit_id": units["PCS"]},
    ],
    operations=["OP-SMT-PLACE","OP-SMT-REFLO","OP-AOI","OP-THL-INS","OP-WAVE-SOL","OP-HSG-ASY","OP-FW-FLASH","OP-FUNC-TEST","OP-QC-CHECK","OP-PKG-FINAL"],
)
ok(f"SYN-CTRL-100 BOM active → {ctrl_bom}")

# BOM 2: Data Logger
step("  BOM: SYN-LOGGER-200 …")
logger_bom = create_bom(
    "SYN-LOGGER-200",
    lines=[
        {"material_id": mats["PCB-MAIN-001"],    "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["IC-ATMEGA-328"],   "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["CAP-100UF"],       "quantity": 16, "unit_id": units["PCS"]},
        {"material_id": mats["RES-10K"],         "quantity": 20, "unit_id": units["PCS"]},
        {"material_id": mats["DISP-LCD-16X2"],   "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["SENSOR-TEMP-NTC"], "quantity": 4,  "unit_id": units["PCS"]},
        {"material_id": mats["ABS-HOUSING-A"],   "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["ABS-HOUSING-B"],   "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["BUTTON-TACTILE"],  "quantity": 6,  "unit_id": units["PCS"]},
        {"material_id": mats["SCREW-M3-10MM"],   "quantity": 10, "unit_id": units["PCS"]},
        {"material_id": mats["CARTON-MED"],      "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["FOAM-SHEET-5MM"],  "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["LABEL-PROD"],      "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["MANUAL-A4"],       "quantity": 1,  "unit_id": units["PCS"]},
    ],
    operations=["OP-SMT-PLACE","OP-SMT-REFLO","OP-AOI","OP-THL-INS","OP-WAVE-SOL","OP-HSG-ASY","OP-FW-FLASH","OP-FUNC-TEST","OP-QC-CHECK","OP-PKG-FINAL"],
)
ok(f"SYN-LOGGER-200 BOM active → {logger_bom}")

# BOM 3: Smart Relay Module
step("  BOM: SYN-RELAY-300 …")
relay_bom = create_bom(
    "SYN-RELAY-300",
    lines=[
        {"material_id": mats["PCB-MAIN-001"],   "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["IC-ATMEGA-328"],  "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["CAP-100UF"],      "quantity": 6,  "unit_id": units["PCS"]},
        {"material_id": mats["RES-10K"],        "quantity": 10, "unit_id": units["PCS"]},
        {"material_id": mats["ABS-HOUSING-A"],  "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["ABS-HOUSING-B"],  "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["SCREW-M3-10MM"],  "quantity": 6,  "unit_id": units["PCS"]},
        {"material_id": mats["CARTON-MED"],     "quantity": 1,  "unit_id": units["PCS"]},
        {"material_id": mats["LABEL-PROD"],     "quantity": 1,  "unit_id": units["PCS"]},
    ],
    operations=["OP-SMT-PLACE","OP-SMT-REFLO","OP-AOI","OP-HSG-ASY","OP-FW-FLASH","OP-FUNC-TEST","OP-QC-CHECK","OP-PKG-FINAL"],
)
ok(f"SYN-RELAY-300 BOM active → {relay_bom}")

# BOM 4: Wireless Sensor Node
step("  BOM: SYN-SENSOR-400 …")
sensor_bom = create_bom(
    "SYN-SENSOR-400",
    lines=[
        {"material_id": mats["IC-ATMEGA-328"],   "quantity": 1, "unit_id": units["PCS"]},
        {"material_id": mats["CAP-100UF"],       "quantity": 4, "unit_id": units["PCS"]},
        {"material_id": mats["RES-10K"],         "quantity": 8, "unit_id": units["PCS"]},
        {"material_id": mats["SENSOR-TEMP-NTC"], "quantity": 2, "unit_id": units["PCS"]},
        {"material_id": mats["ABS-HOUSING-A"],   "quantity": 1, "unit_id": units["PCS"]},
        {"material_id": mats["ABS-HOUSING-B"],   "quantity": 1, "unit_id": units["PCS"]},
        {"material_id": mats["SCREW-M3-10MM"],   "quantity": 4, "unit_id": units["PCS"]},
        {"material_id": mats["CARTON-MED"],      "quantity": 1, "unit_id": units["PCS"]},
        {"material_id": mats["LABEL-PROD"],      "quantity": 1, "unit_id": units["PCS"]},
    ],
    operations=["OP-SMT-PLACE","OP-SMT-REFLO","OP-AOI","OP-HSG-ASY","OP-FW-FLASH","OP-QC-CHECK","OP-PKG-FINAL"],
)
ok(f"SYN-SENSOR-400 BOM active → {sensor_bom}")

# ─── 12. Finished Goods Stock ─────────────────────────────────────────────────
step("Creating finished goods inventory items …")
FG_MATS = [
    {"code": "FG-CTRL-100",   "name": "Temp Controller (Finished)",  "material_type": "finished", "category_id": cats["Finished Goods"], "base_unit_id": units["PCS"], "location_id": locs["Finished Goods Store"], "reorder_level": 20, "current_cost": 1250, "description": "Production-complete temperature controller"},
    {"code": "FG-LOGGER-200", "name": "Data Logger (Finished)",      "material_type": "finished", "category_id": cats["Finished Goods"], "base_unit_id": units["PCS"], "location_id": locs["Finished Goods Store"], "reorder_level": 10, "current_cost": 2100, "description": "Production-complete data logger"},
    {"code": "FG-RELAY-300",  "name": "Smart Relay Module (Finished)","material_type": "finished", "category_id": cats["Finished Goods"], "base_unit_id": units["PCS"], "location_id": locs["Finished Goods Store"], "reorder_level": 25, "current_cost": 850,  "description": "Production-complete relay module"},
    {"code": "FG-SENSOR-400", "name": "Wireless Sensor (Finished)",  "material_type": "finished", "category_id": cats["Finished Goods"], "base_unit_id": units["PCS"], "location_id": locs["Finished Goods Store"], "reorder_level": 30, "current_cost": 650,  "description": "Production-complete sensor node"},
]
for m in FG_MATS:
    r = post(f"{BASE_URL}/inventory/materials", m, headers=headers)
    mats[m["code"]] = r["id"]
    ok(f"  {m['code']}")

step("Adding finished goods production receipts …")
for code, qty in [("FG-CTRL-100", 85), ("FG-LOGGER-200", 42), ("FG-RELAY-300", 120), ("FG-SENSOR-400", 230)]:
    post(f"{BASE_URL}/inventory/transactions", {"material_id": mats[code], "transaction_type": "in", "quantity": qty, "unit_id": units["PCS"], "remarks": "Production receipt — seed"}, headers=headers)
    ok(f"{code}: +{qty}")

# ─── 13. Simulated Sales Dispatches ───────────────────────────────────────────
step("Simulating client sales dispatches …")
DISPATCHES = [
    ("FG-CTRL-100",   15, "Tata Power Ltd — Purchase Order PO-2024-0892"),
    ("FG-CTRL-100",    8, "ABB India Pvt Ltd — Purchase Order PO-2024-0915"),
    ("FG-CTRL-100",   12, "Larsen & Toubro Automation — PO-2024-1001"),
    ("FG-LOGGER-200",  5, "Siemens India Ltd — PO-2024-0933"),
    ("FG-LOGGER-200",  8, "BHEL Haridwar — PO-2024-0944"),
    ("FG-RELAY-300",  20, "Honeywell India — PO-2024-0960"),
    ("FG-RELAY-300",  15, "Rockwell Automation India — PO-2024-0972"),
    ("FG-RELAY-300",  10, "Schneider Electric India — PO-2024-0985"),
    ("FG-SENSOR-400", 50, "Bosch India Ltd — PO-2024-1010"),
    ("FG-SENSOR-400", 30, "Mahindra Electric — PO-2024-1025"),
    ("FG-SENSOR-400", 25, "JSW Steel — PO-2024-1038"),
]
for code, qty, remark in DISPATCHES:
    post(f"{BASE_URL}/inventory/transactions", {"material_id": mats[code], "transaction_type": "out", "quantity": qty, "unit_id": units["PCS"], "remarks": remark}, headers=headers)
    ok(f"  {code}: −{qty} → {remark.split(' — ')[0]}")

# ─── 14. Summary ──────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  ✅  ERP SEED DATA COMPLETE")
print(SEP)
print(f"""
  🏭  Tenant  : {TENANT_NAME}
  🔑  Tenant ID: {tenant_id}

  LOGIN CREDENTIALS
  ─────────────────
  Email    : {ADMIN_EMAIL}
  Password : {ADMIN_PASSWORD}

  ⚠️  RUN THIS SQL TO ENABLE ₹ CURRENCY:
      UPDATE tenants
      SET currency_code='INR', currency_symbol='₹'
      WHERE id='{tenant_id}';

  SEEDED DATA SUMMARY
  ────────────────────
  Units of Measure  : 10
  Categories        : 8
  Locations         : 6

  Raw Materials (Inventory): 16 items with opening stock

  Product Catalog   : 6 templates, 13 variants
    ├─ SYN-CTRL-100    Temperature Controller  [3 variants]  ₹2,499–₹2,999
    ├─ SYN-LOGGER-200  Data Logger             [2 variants]  ₹3,999–₹5,499
    ├─ SYN-RELAY-300   Smart Relay Module      [3 variants]  ₹1,799–₹2,699
    ├─ SYN-SENSOR-400  Wireless Sensor Node    [2 variants]  ₹1,399–₹1,899
    ├─ SYN-SUBASSY-PCB PCB Sub-Assembly        [1 variant]   (WIP)
    └─ SYN-ACC-KIT     Accessories Kit         [2 variants]  ₹199–₹249

  Workstations      : 8  (SMT, THL, Soldering, Housing, Test, QC, Packing)
  Routing Steps     : 10 operations

  BOMs (Active)     : 4
    ├─ SYN-CTRL-100   14 lines × 10 ops
    ├─ SYN-LOGGER-200 14 lines × 10 ops
    ├─ SYN-RELAY-300   9 lines ×  8 ops
    └─ SYN-SENSOR-400  9 lines ×  7 ops

  Finished Goods    : 4 items in stock
  Client Dispatches : 11 transactions (6 clients)
    Tata Power, ABB India, L&T, Siemens, Honeywell,
    Rockwell, Schneider, Bosch, Mahindra, JSW Steel, BHEL
""")
print(SEP)
print("  Open http://localhost:5173 and log in with the credentials above")
print(SEP)

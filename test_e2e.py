import requests
import sys
import uuid
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_tests():
    print("starting e2e tests...")
    
    run_id = str(uuid.uuid4())[:8]
    tenant_email = f"admin{run_id}@e2e.com"
    
    # 1. Register Tenant
    print(f"1. Registering Tenant {run_id}...")
    res = requests.post(
        f"{BASE_URL}/auth/register-tenant",
        json={
            "name": f"E2E Test Tenant {run_id}",
            "slug": f"e2e-tenant-{run_id}",
            "admin_email": tenant_email,
            "admin_password": "Password123!",
            "admin_first_name": "Test",
            "admin_last_name": "Admin"
        }
    )
    if res.status_code not in (201, 400): # 400 might mean already registered
        print("Failed to register tenant:", res.text)
        sys.exit(1)
        
    if res.status_code == 201:
        tenant_id = res.json()["tenant_id"]
    else:
        # Assuming it already exists, authenticate to get a token.
        print("Tenant probably exists, skipping registration.")

    # 2. Login
    print("2. Logging In...")
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": tenant_email, 
        "password": "Password123!", 
        "tenant_id": tenant_id
    })
    if res.status_code != 200:
        print("Login failed:", res.text)
        sys.exit(1)
    
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Create Category
    print("3. Creating Master Data: Category...")
    res = requests.post(f"{BASE_URL}/inventory/master-data/categories", json={"name": "Raw Materials", "description": "Raw goods", "is_active": True}, headers=headers)
    if res.status_code != 201:
        print("Failed to create category:", res.text)
        sys.exit(1)
    category_id = res.json()["id"]
    
    # 4. Create Unit
    print("4. Creating Master Data: Unit of Measure...")
    res = requests.post(f"{BASE_URL}/inventory/master-data/units", json={"code": "KG", "name": "Kilograms", "precision": 2, "is_active": True}, headers=headers)
    if res.status_code != 201:
        print("Failed to create unit:", res.text)
        sys.exit(1)
    unit_id = res.json()["id"]
    
    # 5. Create Location
    print("5. Creating Master Data: Location...")
    res = requests.post(f"{BASE_URL}/inventory/master-data/locations", json={"name": "Warehouse A", "type": "warehouse", "is_active": True}, headers=headers)
    if res.status_code != 201:
        print("Failed to create location:", res.text)
        sys.exit(1)
    location_id = res.json()["id"]
    
    # 6. Create Material
    print("6. Creating Material utilizing generated config IDs...")
    res = requests.post(f"{BASE_URL}/inventory/materials", json={
        "code": f"STEEL-{run_id}",
        "name": "Steel Sheet",
        "material_type": "raw",
        "description": "Premium industrial steel.",
        "category_id": category_id,
        "base_unit_id": unit_id,
        "location_id": location_id,
    }, headers=headers)
    if res.status_code != 201:
        if "already exists" in res.text:
            print("Material already exists.")
            # find the ID
            res = requests.get(f"{BASE_URL}/inventory/materials", headers=headers)
            material_id = res.json()["items"][0]["id"]
        else:
            print("Failed to create material:", res.text)
            sys.exit(1)
    else:
        material_id = res.json()["id"]
    
    # 7. Add Stock
    print("7. Adding Stock (Transaction in)...")
    res = requests.post(f"{BASE_URL}/inventory/transactions", json={
        "material_id": material_id,
        "transaction_type": "in",
        "quantity": 1000.0,
        "unit_id": unit_id,
        "to_location_id": location_id,
        "remarks": "Initial Restock"
    }, headers=headers)
    
    if res.status_code != 201:
        print("Failed to add stock:", res.text)
        sys.exit(1)
        
    print("SUCCESS: Phase 1.1 Configurable Inventory Schema E2E Flow verified! 🎉")

    # ── Phase 1.2 — Batch Tracking ────────────────────────────────────────
    print("\n--- Phase 1.2: Batch & Expiry Tracking ---")

    # Create a batch-tracked material
    print("8. Creating batch-tracked material...")
    res = requests.post(f"{BASE_URL}/inventory/materials", json={
        "code": f"BATCH-MED-{run_id}",
        "name": "Batch Tracked Medicine",
        "material_type": "finished",
        "is_batch_tracked": True,
    }, headers=headers)
    if res.status_code != 201:
        print("Failed to create batch material:", res.text)
        sys.exit(1)
    batch_material_id = res.json()["id"]

    # Add stock with batch
    print("9. Adding stock with batch number + expiry...")
    expiry = (date.today() + timedelta(days=20)).isoformat()
    res = requests.post(f"{BASE_URL}/inventory/batches/add-stock", json={
        "material_id": batch_material_id,
        "batch_number": "BATCH-001",
        "quantity": 500,
        "expiry_date": expiry,
        "remarks": "Initial batch"
    }, headers=headers)
    if res.status_code != 201:
        print("Failed to add batch stock:", res.text)
        sys.exit(1)
    batch_data = res.json()
    assert batch_data["batch_number"] == "BATCH-001", "Batch number mismatch"
    assert float(batch_data["quantity"]) == 500.0, "Batch quantity mismatch"
    print(f"   Batch created: {batch_data['batch_number']} qty={batch_data['quantity']} expiry={batch_data['expiry_date']}")

    # List batches for material
    print("10. Listing batches for the material...")
    res = requests.get(f"{BASE_URL}/inventory/batches?material_id={batch_material_id}", headers=headers)
    if res.status_code != 200:
        print("Failed to list batches:", res.text)
        sys.exit(1)
    assert res.json()["total"] == 1, "Expected 1 batch"

    # Get expiring batches (within 30 days)
    print("11. Querying expiring batches (next 30 days)...")
    res = requests.get(f"{BASE_URL}/inventory/batches/expiring?days=30", headers=headers)
    if res.status_code != 200:
        print("Failed to get expiring batches:", res.text)
        sys.exit(1)
    expiring = res.json()
    assert expiring["total"] >= 1, f"Expected ≥1 expiring batch, got {expiring['total']}"
    print(f"   Found {expiring['total']} expiring batch(es) in the next 30 days ✓")

    # Remove stock from batch
    print("12. Removing stock from batch...")
    res = requests.post(f"{BASE_URL}/inventory/batches/remove-stock", json={
        "material_id": batch_material_id,
        "batch_number": "BATCH-001",
        "quantity": 100,
        "remarks": "Dispensed 100 units"
    }, headers=headers)
    if res.status_code != 200:
        print("Failed to remove batch stock:", res.text)
        sys.exit(1)
    assert float(res.json()["remaining_quantity"]) == 400.0, "Expected remaining quantity = 400"
    print("   Batch remaining_quantity after removal = 400 ✓")

    print("SUCCESS: Phase 1.2 Batch & Expiry Tracking E2E Flow verified! 🎉")

    # ── Phase 1.3 — Serial Number Tracking ───────────────────────────────
    print("\n--- Phase 1.3: Serial Number Tracking ---")

    # Create a serialized material
    print("13. Creating serialized material...")
    res = requests.post(f"{BASE_URL}/inventory/materials", json={
        "code": f"SERIAL-DEV-{run_id}",
        "name": "Serialized Medical Device",
        "material_type": "finished",
        "is_serialized": True,
    }, headers=headers)
    if res.status_code != 201:
        print("Failed to create serialized material:", res.text)
        sys.exit(1)
    serial_material_id = res.json()["id"]

    # Add serial stock
    print("14. Registering serial numbers...")
    serials = [f"SN-{run_id}-001", f"SN-{run_id}-002", f"SN-{run_id}-003"]
    res = requests.post(f"{BASE_URL}/inventory/serial-numbers/add-stock", json={
        "material_id": serial_material_id,
        "serial_numbers": serials,
        "remarks": "Goods received"
    }, headers=headers)
    if res.status_code != 201:
        print("Failed to add serial stock:", res.text)
        sys.exit(1)
    added = res.json()
    assert len(added) == 3, f"Expected 3 serials created, got {len(added)}"
    for s in added:
        assert s["status"] == "in_stock", f"Expected in_stock, got {s['status']}"
    print(f"   {len(added)} serials registered, all status=in_stock ✓")

    # List serials by material
    print("15. Listing serials for the material...")
    res = requests.get(f"{BASE_URL}/inventory/serial-numbers?material_id={serial_material_id}", headers=headers)
    if res.status_code != 200:
        print("Failed to list serials:", res.text)
        sys.exit(1)
    assert res.json()["total"] == 3, "Expected 3 serials"

    # Issue one serial
    sn_to_issue = serials[0]
    print(f"16. Issuing serial {sn_to_issue}...")
    res = requests.post(f"{BASE_URL}/inventory/serial-numbers/issue", json={
        "serial_number": sn_to_issue,
        "remarks": "Issued to patient"
    }, headers=headers)
    if res.status_code != 200:
        print("Failed to issue serial:", res.text)
        sys.exit(1)
    assert res.json()["status"] == "issued", f"Expected issued, got {res.json()['status']}"
    print(f"   Serial {sn_to_issue} status=issued ✓")

    # Return the serial
    print(f"17. Returning serial {sn_to_issue}...")
    res = requests.post(f"{BASE_URL}/inventory/serial-numbers/return", json={
        "serial_number": sn_to_issue,
        "remarks": "Returned by patient"
    }, headers=headers)
    if res.status_code != 200:
        print("Failed to return serial:", res.text)
        sys.exit(1)
    assert res.json()["status"] == "returned", f"Expected returned, got {res.json()['status']}"
    print(f"   Serial {sn_to_issue} status=returned ✓")

    # Get serial details
    print(f"18. Fetching serial detail for {sn_to_issue}...")
    res = requests.get(f"{BASE_URL}/inventory/serial-numbers/{sn_to_issue}", headers=headers)
    if res.status_code != 200:
        print("Failed to get serial detail:", res.text)
        sys.exit(1)
    assert res.json()["serial_number"] == sn_to_issue
    print(f"   Serial detail fetched correctly ✓")

    print("SUCCESS: Phase 1.3 Serial Number Tracking E2E Flow verified! 🎉")
    print("\n✅ ALL E2E TESTS PASSED — Phase 1.1 + 1.2 + 1.3 complete!")

if __name__ == "__main__":
    run_tests()

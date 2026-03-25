"""
Phase 2.2 E2E Test: Bill of Materials (Basic Structure)

Covers:
1. Login
2. Create Item Template + get a unit ID
3. Create BOM v1.0 with 1 material component
4. Activate BOM v1.0
5. Copy BOM -> v1.1
6. Activate BOM v1.1 (auto-deactivates v1.0)
7. Assert v1.0 is inactive
"""
import sys
import time
from fastapi.testclient import TestClient
from backend.app.main import app

with TestClient(app) as client:
    BASE = "/api/v1"

    # ─── 1. Login ────────────────────────────────────────────────────────────────
    r = client.post(f"{BASE}/auth/login", json={
        "email": "admin@medtrack-demo.com",
        "password": "Demo@1234",
        "tenant_id": "b5ef68c4-18be-4fa6-a439-a23c34877550"
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("LOGIN: OK")

    # ─── 2. Fetch a known unit ID ────────────────────────────────────────────────
    r = client.get(f"{BASE}/inventory/master-data/units", headers=headers)
    assert r.status_code == 200, f"Failed to list units: {r.text}"
    units_data = r.json()
    units = units_data if isinstance(units_data, list) else units_data.get("items", units_data)
    assert len(units) > 0, "No units found in master data"
    unit_id = units[0]["id"]
    print(f"UNIT: {units[0].get('name', 'unknown')} | id: {unit_id}")

    # ─── 3. Create an Item Template ───────────────────────────────────────────────
    uid = str(int(time.time()))[-5:]
    r = client.post(f"{BASE}/products/templates", json={
        "code": f"BOM-TEST-{uid}",
        "name": "BOM Test Product",
        "attributes": [{"key": "SIZE", "label": "Size"}]
    }, headers=headers)
    assert r.status_code == 201, f"Template creation failed: {r.text}"
    template_id = r.json()["id"]
    print(f"CREATE TEMPLATE: {r.json()['code']} | id: {template_id}")

    # ─── 4. Fetch a material to use as component ─────────────────────────────────
    r = client.get(f"{BASE}/inventory/materials", headers=headers)
    assert r.status_code == 200, f"Failed to list materials: {r.text}"
    mats = r.json().get("items", r.json())
    assert len(mats) > 0, "No materials in system - please seed at least one material"
    material_id = mats[0]["id"]
    print(f"MATERIAL: {mats[0].get('name', 'unknown')} | id: {material_id}")

    # ─── 5. Create BOM v1.0 ──────────────────────────────────────────────────────
    from datetime import datetime, timezone
    r = client.post(f"{BASE}/products/{template_id}/boms", json={
        "version": "v1.0",
        "valid_from": datetime.now(timezone.utc).isoformat(),
        "template_id": template_id,
        "lines": [
            {
                "material_id": material_id,
                "quantity": "10.0",
                "scrap_percentage": "5.0",
                "unit_id": unit_id,
            }
        ]
    }, headers=headers)
    print("CREATE BOM v1.0:", r.status_code)
    if r.status_code != 201:
        print(r.text); sys.exit(1)
    bom_v1 = r.json()
    bom_v1_id = bom_v1["id"]
    assert bom_v1["version"] == "v1.0"
    assert bom_v1["is_active"] is False
    assert len(bom_v1["lines"]) == 1
    print(f"  id: {bom_v1_id} | active: {bom_v1['is_active']} | lines: {len(bom_v1['lines'])}")

    # ─── 6. Activate BOM v1.0 ────────────────────────────────────────────────────
    activate_url = f"{BASE}/boms/{bom_v1_id}/activate"
    print("SENDING POST TO", activate_url)
    r = client.post(activate_url, headers=headers)
    print("ACTIVATE BOM v1.0:", r.status_code)
    if r.status_code != 200:
        print("ERROR RESPONSE:", r.text)
        sys.exit(1)
        print(r.text); sys.exit(1)
    assert r.json()["is_active"] is True
    print("  Activation PASSED")

    # ─── 7. Copy BOM v1.0 -> v1.1 ────────────────────────────────────────────────
    r = client.post(f"{BASE}/boms/{bom_v1_id}/copy", json={"new_version": "v1.1"}, headers=headers)
    print("COPY BOM v1.0 -> v1.1:", r.status_code)
    if r.status_code != 201:
        print(r.text); sys.exit(1)
    bom_v1_1 = r.json()
    bom_v1_1_id = bom_v1_1["id"]
    assert bom_v1_1["version"] == "v1.1"
    assert bom_v1_1["is_active"] is False
    assert len(bom_v1_1["lines"]) == 1, "Lines should be duplicated"
    print(f"  Copy PASSED | id: {bom_v1_1_id} | lines: {len(bom_v1_1['lines'])}")

    # ─── 8. Activate v1.1 (v1.0 should go inactive) ──────────────────────────────
    r = client.post(f"{BASE}/boms/{bom_v1_1_id}/activate", headers=headers)
    print("ACTIVATE BOM v1.1:", r.status_code)
    if r.status_code != 200:
        print(r.text); sys.exit(1)
    assert r.json()["is_active"] is True
    print("  Activation PASSED")

    # ─── 9. Verify v1.0 is now inactive ──────────────────────────────────────────
    r = client.get(f"{BASE}/boms/{bom_v1_id}", headers=headers)
    assert r.status_code == 200
    v10_after = r.json()
    assert v10_after["is_active"] is False, f"v1.0 should be deactivated but got: {v10_after['is_active']}"
    print("  v1.0 auto-deactivation PASSED")

    # ─── 10. List all BOMs ────────────────────────────────────────────────────────
    r = client.get(f"{BASE}/products/{template_id}/boms?is_template=true", headers=headers)
    assert r.status_code == 200
    listing = r.json()
    assert listing["total"] == 2
    print(f"LIST BOMs: {listing['total']} versions found PASSED")

    print("\nALL PHASE 2.2 TESTS PASSED")

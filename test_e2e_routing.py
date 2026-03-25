from fastapi.testclient import TestClient
from backend.app.main import app
import sys
import uuid

def run_routing_tests():
    print("starting Phase 2.3 routing tests...")
    with TestClient(app) as client:
        run_id = str(uuid.uuid4())[:8]
        tenant_email = f"routing{run_id}@e2e.com"
        
        # 1. Register Tenant
        print(f"1. Registering Tenant {run_id}...")
        res = client.post(
            "/api/v1/auth/register-tenant",
            json={
                "name": f"E2E Routing Tenant {run_id}",
                "slug": f"routing-tenant-{run_id}",
                "admin_email": tenant_email,
                "admin_password": "Password123!",
                "admin_first_name": "Test",
                "admin_last_name": "Routing"
            }
        )
        if res.status_code != 201:
            print("Failed to register tenant:", res.text)
            sys.exit(1)
            
        tenant_id = res.json()["tenant_id"]

        # 2. Login
        print("2. Logging In...")
        res = client.post("/api/v1/auth/login", json={
            "email": tenant_email, 
            "password": "Password123!", 
            "tenant_id": tenant_id
        })
        if res.status_code != 200:
            print("Login failed:", res.text)
            sys.exit(1)
        
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create a Workstation
        print("3. Create Workstation...")
        ws_payload = {
            "code": f"WS-ASSEMBLY-{run_id}",
            "name": "Main Assembly Line",
            "capacity_hours_per_day": 8.0,
            "hourly_rate": 120.0
        }
        res = client.post("/api/v1/workstations", json=ws_payload, headers=headers)
        if res.status_code != 201:
            print("Failed to create workstation:", res.text)
            sys.exit(1)
        workstation_id = res.json()

        # 4. Create an Operation
        print("4. Create Operation...")
        op_payload = {
            "name": f"Final Assembly {run_id}",
            "workstation_id": workstation_id,
            "setup_time": 30.0,
            "run_time": 15.0,
            "description": "Assemble components into final product"
        }
        res = client.post("/api/v1/operations", json=op_payload, headers=headers)
        if res.status_code != 201:
            print("Failed to create operation:", res.text)
            sys.exit(1)
        operation_id = res.json()

        # 5. Create core Master Data (Category & Unit)
        print("5. Create Master Data...")
        res = client.post("/api/v1/inventory/master-data/categories", json={"name": f"Routing Comp {run_id}", "description": "Test"}, headers=headers)
        if res.status_code != 201:
            print("Failed to create category:", res.text)
            sys.exit(1)
        cat_id = res.json()["id"]
        
        res = client.post("/api/v1/inventory/master-data/units", json={"code": f"PCS-{run_id}", "name": f"PCS {run_id}"}, headers=headers)
        if res.status_code != 201:
            print("Failed to create unit:", res.text)
            sys.exit(1)
        unit_id = res.json()["id"]

        # 6. Create Material
        print("6. Create Material...")
        res = client.post("/api/v1/inventory/materials", json={
            "code": f"RM-23-{run_id}", "name": "Metal Sheet", "category_id": cat_id, "base_unit_id": unit_id, "is_active": True,
            "current_cost": 45.0
        }, headers=headers)
        if res.status_code != 201:
            print("Failed to create material:", res.text)
            sys.exit(1)
        mat_id = res.json()["id"]

        # 7. Create Item Template and Variants
        print("7. Create Item Template & Variants...")
        res = client.post("/api/v1/products/templates", json={
            "code": f"TPL-23-{run_id}", "name": "Bicycle Frame", "category_id": cat_id, "base_unit_id": unit_id, "is_active": True,
            "is_stockable": True, "is_purchasable": False, "is_manufacturable": True,
            "attributes": [{"key": "SIZE", "label": "Size"}]
        }, headers=headers)
        if res.status_code != 201:
            print("Failed to create template:", res.text)
            sys.exit(1)
        tpl_id = res.json()["id"]

        res = client.post(f"/api/v1/products/templates/{tpl_id}/variants", json={
            "attribute_values": {"SIZE": "SMALL"}
        }, headers=headers)
        if res.status_code != 201:
            print("Failed to create variant:", res.text)
            sys.exit(1)
        sub_variant_id = res.json()["id"]

        res = client.post(f"/api/v1/products/templates/{tpl_id}/variants", json={
            "attribute_values": {"SIZE": "LARGE"}
        }, headers=headers)
        if res.status_code != 201:
            print("Failed to create variant 2:", res.text)
            sys.exit(1)
        final_variant_id = res.json()["id"]

        # 8. Create Sub-Assembly BOM
        print("8. Create Sub-Assembly BOM...")
        res = client.post(f"/api/v1/products/{sub_variant_id}/boms", json={
            "variant_id": sub_variant_id,
            "version": "1.0",
            "valid_from": "2026-01-01T00:00:00Z",
            "lines": [
                {"material_id": mat_id, "quantity": 2.0, "unit_id": unit_id}
            ]
        }, headers=headers)
        if res.status_code != 201:
            print("Sub-Assembly BOM failed:", res.text)
            sys.exit(1)
        sub_bom_id = res.json()["id"]
        client.post(f"/api/v1/boms/{sub_bom_id}/activate", headers=headers)

        # 9. Create Final Assembly BOM
        print("9. Create Final Assembly BOM...")
        res = client.post(f"/api/v1/products/{final_variant_id}/boms", json={
            "variant_id": final_variant_id,
            "version": "1.0",
            "valid_from": "2026-01-01T00:00:00Z",
            "lines": [
                {"variant_id": sub_variant_id, "quantity": 1.0, "unit_id": unit_id}
            ]
        }, headers=headers)
        if res.status_code != 201:
            print("Final BOM failed:", res.text)
            sys.exit(1)
        final_bom_id = res.json()["id"]

        # 10. Attach Operation to Final BOM
        print("10. Attach Operation...")
        res = client.post(f"/api/v1/boms/{final_bom_id}/operations", json={
            "operation_id": operation_id,
            "sequence": 10
        }, headers=headers)
        if res.status_code != 200:
            print("Failed to attach operation:", res.text)
            sys.exit(1)
        
        client.post(f"/api/v1/boms/{final_bom_id}/activate", headers=headers)

        # 11. Test BOM Tree
        print("11. Get BOM Tree...")
        res = client.get(f"/api/v1/boms/{final_bom_id}/tree", headers=headers)
        if res.status_code != 200:
            print("Failed to get tree:", res.text)
            sys.exit(1)
        tree = res.json()
        assert tree["id"] == final_bom_id, "Tree root ID mismatch"
        assert len(tree["children"]) == 1, "Tree children missing"
        
        # 12. Test BOM Cost
        print("12. Get BOM Cost...")
        res = client.get(f"/api/v1/boms/{final_bom_id}/cost", headers=headers)
        if res.status_code != 200:
            print("Failed to get cost:", res.text)
            sys.exit(1)
        cost = res.json()["cost"]
        print(f"Calculated standard cost: {cost}")
        assert float(cost) >= 0.0, f"Expected non-negative cost, got {cost}"

        # 13. Test Circular Dependency validation
        print("13. Testing Circular Dependency Protection...")
        res = client.post(f"/api/v1/products/{sub_variant_id}/boms", json={
            "variant_id": sub_variant_id,
            "version": "2.0",
            "valid_from": "2026-01-01T00:00:00Z",
            "lines": [
                {"variant_id": final_variant_id, "quantity": 1.0, "unit_id": unit_id}
            ]
        }, headers=headers)
        if res.status_code != 400:
            print("Expected 400 for Circular Dependency, got:", res.status_code, res.text)
            sys.exit(1)
        print("Successfully blocked circular dependency!")

        print("\n✅ All Advanced BOM & Routing Phase 2.3 Tests Passed!")

if __name__ == "__main__":
    run_routing_tests()

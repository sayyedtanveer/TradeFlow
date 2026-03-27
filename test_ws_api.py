import requests
import uuid

def test_workflow():
    slug = f"test-tenant-{uuid.uuid4().hex[:8]}"
    print(f"Registering tenant {slug}...")
    reg = requests.post("http://127.0.0.1:8000/api/v1/auth/register-tenant", json={
        "name"             : "Test Corp",
        "slug"             : slug,
        "admin_email"      : f"admin@{slug}.com",
        "admin_password"   : "Erp@1234",
        "admin_first_name" : "A",
        "admin_last_name"  : "B",
        "plan"             : "professional",
    })
    
    if reg.status_code != 201:
        print("Register failed:", reg.status_code, reg.text)
        return
        
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Creating UOM...")
    u = requests.post("http://127.0.0.1:8000/api/v1/inventory/master-data/units", json={"code": "KG", "name": "Kilogram"}, headers=headers)
    if u.status_code != 201:
        print("UOM failed:", u.status_code, u.text)
        return
        
    print("Creating Workstation...")
    ws = requests.post("http://127.0.0.1:8000/api/v1/workstations", json={"code": "WS-1", "name": "Test", "hourly_rate": 10.0}, headers=headers)
    if ws.status_code != 201:
        print("Workstation failed:", ws.status_code, ws.text)
        return
        
    print("SUCCESS!")

if __name__ == "__main__":
    test_workflow()

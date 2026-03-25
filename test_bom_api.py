"""
BOM Testing Script - Test the Bill of Materials API with authentication
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

def login():
    """Login and get access token"""
    payload = {
        "email": "admin@medtrack-demo.com",
        "password": "Demo@1234",
        "tenant_id": "b5ef68c4-18be-4fa6-a439-a23c34877550"
    }
    
    r = requests.post(f"{BASE_URL}/auth/login", json=payload)
    if r.status_code == 200:
        token = r.json()["access_token"]
        print("✅ Login successful")
        return token
    else:
        print(f"❌ Login failed: {r.text}")
        return None

def get_headers(token):
    """Get headers with authentication token"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_bom_endpoints(token):
    """Test various BOM endpoints"""
    headers = get_headers(token)
    
    print("\n" + "="*70)
    print("  BOM API Testing")
    print("="*70)
    
    # 1. Create a BOM
    print("\n1️⃣  CREATE BOM")
    print("-" * 70)
    create_payload = {
        "product_id": "product-uuid-here",  # Replace with actual product ID
        "code": "BOM-TEST-001",
        "description": "Test Bill of Materials",
        "version": "1.0",
        "quantity": 1,
        "unit": "PCS",
        "is_active": True,
        "lines": [
            {
                "material_id": "material-uuid-here",  # Replace with actual material ID
                "quantity": 2,
                "unit_id": "unit-uuid-here",
                "scrap_percentage": 5.0,
                "sequence": 1
            }
        ]
    }
    
    print(f"Creating BOM...")
    r = requests.post(f"{BASE_URL}/boms", json=create_payload, headers=headers)
    print(f"Status: {r.status_code}")
    if r.status_code in [200, 201]:
        bom = r.json()
        print(f"✅ BOM created successfully")
        print(f"   ID: {bom.get('id')}")
        print(f"   Code: {bom.get('code')}")
        bom_id = bom.get('id')
    else:
        print(f"❌ Failed to create BOM: {r.text[:200]}")
        bom_id = None
    
    # 2. List BOMs for a product
    print("\n2️⃣  LIST BOMs FOR A PRODUCT")
    print("-" * 70)
    product_id = "product-uuid-here"  # Replace with actual product ID
    r = requests.get(f"{BASE_URL}/boms/products/{product_id}", headers=headers)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        boms = r.json()
        print(f"✅ Found {len(boms)} BOM(s)")
        for bom in boms[:3]:  # Show first 3
            print(f"   - {bom.get('code')} (v{bom.get('version')})")
    else:
        print(f"ℹ️  No BOMs found or error: {r.status_code}")
    
    # 3. Get specific BOM
    if bom_id:
        print(f"\n3️⃣  GET SPECIFIC BOM")
        print("-" * 70)
        r = requests.get(f"{BASE_URL}/boms/{bom_id}", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            bom = r.json()
            print(f"✅ BOM Details:")
            print(f"   ID: {bom.get('id')}")
            print(f"   Code: {bom.get('code')}")
            print(f"   Description: {bom.get('description')}")
            print(f"   Version: {bom.get('version')}")
            print(f"   Active: {bom.get('is_active')}")
            print(f"   Lines: {len(bom.get('lines', []))}")
        else:
            print(f"❌ Failed: {r.text[:200]}")
    
        # 4. Get BOM Tree Structure
        print(f"\n4️⃣  GET BOM TREE STRUCTURE")
        print("-" * 70)
        r = requests.get(f"{BASE_URL}/boms/{bom_id}/tree", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            tree = r.json()
            print(f"✅ BOM Tree retrieved")
            print(json.dumps(tree, indent=2)[:300] + "...")
        else:
            print(f"ℹ️  Tree endpoint: {r.status_code}")
    
        # 5. Get BOM Cost
        print(f"\n5️⃣  GET BOM COST")
        print("-" * 70)
        r = requests.get(f"{BASE_URL}/boms/{bom_id}/cost", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            cost = r.json()
            print(f"✅ BOM Cost calculated")
            print(f"   Total Cost: {cost.get('total_cost', 'N/A')}")
            print(f"   Material Cost: {cost.get('material_cost', 'N/A')}")
            print(f"   Labor Cost: {cost.get('labor_cost', 'N/A')}")
        else:
            print(f"ℹ️  Cost endpoint: {r.status_code}")
    
        # 6. Activate BOM
        print(f"\n6️⃣  ACTIVATE BOM")
        print("-" * 70)
        r = requests.post(f"{BASE_URL}/boms/{bom_id}/activate", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(f"✅ BOM activated successfully")
        else:
            print(f"ℹ️  Activate result: {r.status_code}")
    
    print("\n" + "="*70)
    print("  Testing Complete")
    print("="*70)

def main():
    print("BOM API Testing Tool")
    print("=" * 70)
    
    # Login
    token = login()
    if not token:
        print("\n❌ Cannot proceed without valid token")
        return
    
    # Test BOM endpoints
    test_bom_endpoints(token)
    
    print("\n📝 NOTES:")
    print("  • Replace 'product-uuid-here' and 'material-uuid-here' with actual IDs")
    print("  • Use GET /api/v1/inventory/products to find product IDs")
    print("  • Use GET /api/v1/inventory/materials to find material IDs")
    print("  • All BOM operations require valid authentication token")

if __name__ == "__main__":
    main()

import requests, json, sys, time

BASE = 'http://127.0.0.1:8000/api/v1'
TENANT_ID = 'b5ef68c4-18be-4fa6-a439-a23c34877550'

r = requests.post(f'{BASE}/auth/login', json={'email':'admin@medtrack-demo.com','password':'Demo@1234','tenant_id':TENANT_ID})
if r.status_code != 200:
    print('LOGIN FAIL:', r.text); sys.exit(1)
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print('LOGIN: OK')

# 1. Create Template
tmpl_body = {
    'code': 'TSHIRT',
    'name': 'T-Shirt',
    'description': 'Classic T-Shirt',
    'attributes': [
        {'key': 'SIZE',  'label': 'Size'},
        {'key': 'COLOR', 'label': 'Color'}
    ]
}
r = requests.post(f'{BASE}/products/templates', json=tmpl_body, headers=headers)
print('CREATE TEMPLATE:', r.status_code)
if r.status_code != 201:
    print(r.text); sys.exit(1)
tmpl = r.json()
tmpl_id = tmpl['id']
print(f"  code: {tmpl['code']}  id: {tmpl_id}")

# 2. Create Variant 1
v1 = requests.post(f'{BASE}/products/templates/{tmpl_id}/variants', headers=headers, json={
    'attribute_values': {'SIZE': 'Small', 'COLOR': 'Red'},
    'standard_cost': '50.00',
    'selling_price': '99.00'
})
print('CREATE VARIANT 1:', v1.status_code)
if v1.status_code != 201:
    print(v1.text); sys.exit(1)
variant1 = v1.json()
print(f"  code: {variant1['code']} | key: {variant1['variant_key']}")
assert variant1['code'] == 'TSHIRT-SMALL-RED', f"Expected TSHIRT-SMALL-RED, got {variant1['code']}"
assert variant1['variant_key'] == 'SIZE=SMALL|COLOR=RED', f"Bad variant_key: {variant1['variant_key']}"
print('  Code + variant_key assertions PASSED')

# 3. Create Variant 2
v2 = requests.post(f'{BASE}/products/templates/{tmpl_id}/variants', headers=headers, json={
    'attribute_values': {'SIZE': 'Medium', 'COLOR': 'Blue'},
})
print('CREATE VARIANT 2:', v2.status_code)
if v2.status_code != 201:
    print(v2.text); sys.exit(1)
print(f"  code: {v2.json()['code']}")

# 4. Duplicate variant must be rejected with 409
v_dup = requests.post(f'{BASE}/products/templates/{tmpl_id}/variants', headers=headers, json={
    'attribute_values': {'SIZE': 'Small', 'COLOR': 'Red'},
})
print(f'DUPLICATE VARIANT (expect 409): {v_dup.status_code}')
assert v_dup.status_code == 409, f'Expected 409, got {v_dup.status_code}'
print('  Duplicate rejection PASSED')

# 5. List variants — expect 2
vlist = requests.get(f'{BASE}/products/templates/{tmpl_id}/variants', headers=headers)
print(f"LIST VARIANTS: {vlist.status_code} - total: {vlist.json()['total']}")
assert vlist.json()['total'] == 2, 'Expected 2 variants'

# 6. Get single template
tget = requests.get(f'{BASE}/products/templates/{tmpl_id}', headers=headers)
print(f"GET TEMPLATE: {tget.status_code} - name: {tget.json()['name']}")

# 7. List templates
tlist = requests.get(f'{BASE}/products/templates', headers=headers)
print(f"LIST TEMPLATES: {tlist.status_code} - total: {tlist.json()['total']}")

# 8. Update variant pricing
v_update = requests.put(f'{BASE}/products/variants/{variant1[\"id\"]}', headers=headers, json={
    'selling_price': '120.00'
})
print(f'UPDATE VARIANT PRICING: {v_update.status_code}')
assert v_update.status_code == 200

print()
print('ALL PHASE 2.1 TESTS PASSED')

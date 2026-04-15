#!/usr/bin/env python
"""Test frontend, backend, and proxy connectivity."""
import requests
import json

print('\n=== FRONTEND DEV SERVER TEST ===')
try:
    r = requests.get('http://localhost:3001/', timeout=2)
    print(f'✅ Frontend running on port 3001: Status {r.status_code}')
except Exception as e:
    print(f'❌ Frontend not responding: {e}')

print('\n=== TESTING PROXY: Frontend → Backend ===')
print('POST http://localhost:3001/api/v1/auth/login')
try:
    r = requests.post('http://localhost:3001/api/v1/auth/login',
        json={'email': 'admin@medtrack-demo.com', 'password': 'Demo@1234', 'tenant_id': 'b5ef68c4-18be-4fa6-a439-a23c34877550'},
        timeout=3
    )
    print(f'Status: {r.status_code}')
    resp = r.json()
    print(f'Response: {json.dumps(resp, indent=2)[:400]}')
except Exception as e:
    print(f'Error: {e}')

print('\n=== DIRECT BACKEND TEST ===')
print('POST http://localhost:8000/api/v1/auth/login')
try:
    r = requests.post('http://localhost:8000/api/v1/auth/login',
        json={'email': 'admin@medtrack-demo.com', 'password': 'Demo@1234', 'tenant_id': 'b5ef68c4-18be-4fa6-a439-a23c34877550'},
        timeout=3
    )
    print(f'Status: {r.status_code}')
    resp = r.json()
    if 'access_token' in resp:
        print(f'✅ Login successful! Token: {resp["access_token"][:20]}...')
        print(f'   User: {resp.get("email")}')
        print(f'   Role: {resp.get("role")}')
    else:
        print(f'Response: {json.dumps(resp, indent=2)[:500]}')
except Exception as e:
    print(f'Error: {e}')

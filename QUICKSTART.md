# 🚀 MedTrack ERP - Quick Start Guide

## One-Command Setup

### **Windows Users - Easiest Way**

**Option 1: Run the batch file (Double-click)**
```
run.bat
```

**Option 2: Run PowerShell script**
```powershell
.\run.ps1
```

**Option 3: Manual terminal commands**
```powershell
# Terminal 1 - Backend
cd c:\Users\sayye\source\repos\MedTrack
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 - Frontend
cd c:\Users\sayye\source\repos\MedTrack\frontend
npm run dev
```

---

## ✅ What You'll See

### **Backend Terminal**
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete
```

### **Frontend Terminal**
```
VITE v6.4.1 ready in 500 ms
Local:   http://localhost:3003/
```

---

## 🌐 Access Application

1. Open browser: **http://localhost:3003**
2. Login with:
   - **Email**: `admin@medtrack-demo.com`
   - **Password**: `Demo@1234`

---

## 📡 Test BOM Features

Open a **new terminal** and run:

```powershell
cd c:\Users\sayye\source\repos\MedTrack
python test_bom_api.py
```

### Expected Output:
```
========================================
  BOM API Testing
========================================

1️⃣  CREATE BOM
Status: 201
✅ BOM created successfully

2️⃣  LIST BOMs FOR A PRODUCT
Status: 200
✅ Found X BOM(s)

3️⃣  GET SPECIFIC BOM
✅ BOM Details...

4️⃣  GET BOM TREE STRUCTURE
✅ BOM Tree retrieved

5️⃣  GET BOM COST
✅ BOM Cost calculated
```

---

## 📊 Project URLs

| Service | URL | Status |
|---------|-----|--------|
| Frontend | http://localhost:3003 | 🟢 Dev Mode |
| Backend API | http://localhost:8001 | 🟢 Running |
| API Docs | http://localhost:8001/docs | 🟢 Swagger UI |

---

## 🔑 Available Scripts

```powershell
# From root directory
npm run dev              # Run backend + frontend together
npm run backend:dev      # Backend only
npm run frontend:dev     # Frontend only
npm run build            # Build frontend for production
npm run test:e2e         # Run E2E tests
npm run test:bom         # Test BOM API
npm run test:login       # Test login
```

---

## 🛠️ Troubleshooting

### **Port Already in Use**
```powershell
# Kill process on port 8001
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# Kill process on port 3003
netstat -ano | findstr :3003
taskkill /PID <PID> /F
```

### **Python Environment Issues**
```powershell
# Recreate virtual environment
rm -r .venv
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### **Node Modules Issues**
```powershell
# Reinstall node modules
cd frontend
rm -r node_modules
npm install
npm run build
```

---

## 📝 Database Info

- **Type**: PostgreSQL
- **Host**: localhost:5432
- **Database**: medtrack
- **User**: postgres
- **Password**: 123

---

## 🧪 Testing Commands

```powershell
# Test login
python debug_login.py

# Test BOM API
python test_bom_api.py

# Test E2E flows
python test_e2e.py

# Unit tests
python -m pytest
```

---

## ✨ Features Ready to Test

- ✅ **Authentication** - Multi-tenant login
- ✅ **Inventory Management** - Materials, batches, serials
- ✅ **Bill of Materials (BOM)** - Full CRUD with versioning
- ✅ **Cost Calculations** - BOM cost rollup
- ✅ **Batch Tracking** - Expiry dates, near-expiry alerts
- ✅ **Serial Numbers** - Device tracking and lifecycle

---

## 🎯 BOM Feature Demo

1. **Create BOM** - Design product composition
2. **List BOMs** - View all BOMs for a product
3. **Get BOM Details** - View specific BOM with line items
4. **Get BOM Tree** - Hierarchical structure
5. **Calculate Cost** - Total material cost
6. **Activate BOM** - Make BOM active for production
7. **Copy BOM** - Clone existing BOM as new version

---

**Ready? Run `.\run.ps1` or `run.bat` now! 🚀**

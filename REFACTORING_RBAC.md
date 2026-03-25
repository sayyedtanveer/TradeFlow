# RBAC Refactoring: Industry Standards Implementation

## ❌ **What Was Wrong**
Your project had enums defined but wasn't following the industry standard pattern:

```typescript
// BAD: Hardcoded role strings scattered everywhere
const NAV_ITEMS = [
  { roles: ["ADMIN", "MANAGER"] },
  { roles: ["ADMIN", "MANAGER", "OPERATOR"] },
]

// BAD: Same roles hardcoded in user forms
<SelectItem value="ADMIN">Admin (Full Access)</SelectItem>
<SelectItem value="MANAGER">Manager (View + Edit)</SelectItem>

// BAD: Different case formats between backend and frontend
// Backend returns "admin" (lowercase)
// Frontend expects "ADMIN" (uppercase)
```

**Issues Identified:**
- ❌ Frontend `UserRole` enum (uppercase) didn't match backend `Role` enum values (lowercase)
- ❌ Role strings hardcoded in 4+ separate locations (constants.ts, UserFormPage, UserFormDrawer, navigation)
- ❌ No single source of truth for role metadata (labels, descriptions, permissions)
- ❌ No role-to-module access matrix - just scattered role arrays
- ❌ No database table for roles - hardcoded in both frontend and backend code

---

## ✅ **What We Fixed (Frontend)**

### 1. **Created Centralized Role Configuration** (`lib/roles.config.ts`)
```typescript
// GOOD: Single source of truth
export const ROLE_CONFIG: Record<UserRole, {
  label: string
  description: string
  icon: LucideIcon
  color: string
}> = {
  [UserRole.ADMIN]: {
    label: "Administrator",
    description: "Full access to all modules and settings",
    icon: Shield,
  },
  // ...
}

// Automatic generation of form options
export const AVAILABLE_ROLES = Object.entries(ROLE_CONFIG)
  .map(([role, config]) => ({
    value: role,
    label: config.label,
    description: config.description,
  }))

// Module-level access matrix
export const MODULE_ROLES: Record<string, UserRole[]> = {
  dashboard: [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR, UserRole.VIEWER],
  bom: [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR],
  // ... define once, use everywhere
}

// Helper: Normalize backend's "admin" to frontend's UserRole.ADMIN
export function normalizeRole(role: string | undefined): UserRole | undefined {
  const normalized = role?.toUpperCase()
  return Object.values(UserRole).includes(normalized) ? normalized : undefined
}
```

### 2. **Updated All Files to Use Centralized Config**

#### [lib/constants.ts](src/lib/constants.ts)
```typescript
// BEFORE: Hardcoded roles in 10 places
const NAV_ITEMS = [
  { roles: ["ADMIN", "MANAGER", "OPERATOR", "VIEWER"] },
  { roles: ["ADMIN", "MANAGER"] },
]

// AFTER: Uses helper from roles.config
import { getRolesForModule } from "@/lib/roles.config"

const NAV_ITEMS = [
  { roles: getRolesForModule("dashboard") },
  { roles: getRolesForModule("products") },
]
```

#### [components/layout/Sidebar.tsx](src/components/layout/Sidebar.tsx)
```typescript
// BEFORE: Manual string comparison with case normalization
const visibleNavItems = NAV_ITEMS.filter(item => 
  role?.toUpperCase() && item.roles.includes(role?.toUpperCase())
)

// AFTER: Using normalizeRole helper and type-safe enum
import { normalizeRole, UserRole } from "@/lib/roles.config"

const normalizedRole = normalizeRole(role)
const visibleNavItems = NAV_ITEMS.filter(item =>
  normalizedRole && item.roles.includes(normalizedRole)
)
```

#### [hooks/usePermissions.ts](src/hooks/usePermissions.ts)
```typescript
// BEFORE: Manual normalization, inconsistent method names
hasRole: (roles: string[]) => roles.includes(user.role?.toUpperCase())
canWriteInventory: () => hasRole(["ADMIN", "MANAGER", "OPERATOR"])

// AFTER: Using helpers from roles.config, cleaner API
import { normalizeRole, UserRole, canAccessModule } from "@/lib/roles.config"

hasRole: (roles: (UserRole | string)[]) => {
  const normalized = normalizeRole(user.role)
  return roles.some(r => normalizeRole(r as string) === normalized)
}
isAdmin: () => hasRole([UserRole.ADMIN])
isManager: () => hasRole([UserRole.MANAGER])
canAccessModule: (module) => canAccessModule(module, user.role)
```

#### [modules/users/pages/UserFormPage.tsx](src/modules/users/pages/UserFormPage.tsx)
```typescript
// BEFORE: Hardcoded SelectItems
<SelectItem value="ADMIN">Admin (Full Access)</SelectItem>
<SelectItem value="MANAGER">Manager (View + Edit)</SelectItem>
<SelectItem value="OPERATOR">Operator (Limited Actions)</SelectItem>
<SelectItem value="VIEWER">Viewer (Read Only)</SelectItem>

// AFTER: Generated from centralized config
import { AVAILABLE_ROLES } from "@/lib/roles.config"

{AVAILABLE_ROLES.map(role => (
  <SelectItem key={role.value} value={role.value}>
    {role.label} ({role.description})
  </SelectItem>
))}
```

#### [modules/users/components/UserFormDrawer.tsx](src/modules/users/components/UserFormDrawer.tsx)
Same update as UserFormPage.tsx - now uses `AVAILABLE_ROLES`

---

## ⏳ **What Still Needs Backend Work** (CRITICAL)

### Backend Enum Case Mismatch
Backend defines roles as **lowercase** (`"admin"`, `"manager"`) but frontend expects **uppercase** (`"ADMIN"`, `"MANAGER"`).

**File**: [backend/app/domain/tenant/value_objects/role.py](../../backend/app/domain/tenant/value_objects/role.py)
```python
# CURRENT (lowercase)
class Role(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"

# SHOULD BE (uppercase to match frontend)
class Role(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"
```

**Why this matters:**
- Prevents bugs when comparing roles
- Maintains consistency between frontend and backend
- Follows uppercase enum naming convention in most languages
- Our frontend fix is a workaround; the real fix is in backend

**Required Changes:**
1. Update `Role` enum values to uppercase in `value_objects/role.py`
2. Update database seed/migration if roles stored as strings
3. Update `ROLE_PERMISSIONS` dict in `domain/shared/permissions.py` (uses lowercase keys)
4. Test all role comparisons and permission checks

### Industry Standard: Database-Driven Roles (Optional, Best Practice)

For production systems, create a `roles` table:

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,  -- "ADMIN", "MANAGER", etc
    label VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE role_permissions (
    id UUID PRIMARY KEY,
    role_id UUID REFERENCES roles(id),
    permission_code VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

Then load roles from database at startup instead of hardcoding.

---

## 📊 Summary of Changes

| Area | Before | After | Status |
|------|--------|-------|--------|
| **Role Definition** | Scattered strings | `UserRole` enum | ✅ Fixed |
| **Role Metadata** | Hardcoded in 4+ places | Centralized in `roles.config.ts` | ✅ Fixed |
| **Navigation Configuration** | Hardcoded role arrays | Uses `getRolesForModule()` | ✅ Fixed |
| **User Forms** | Hardcoded SelectItems | Generated from `AVAILABLE_ROLES` | ✅ Fixed |
| **Permission Checking** | String comparisons | Type-safe enum checks | ✅ Fixed |
| **Backend/Frontend Case Match** | Mismatched (backend lowercase, frontend uppercase) | Normalized with `normalizeRole()` helper | ⏳ Needs backend fix |
| **Database-Driven Roles** | Hardcoded in code | ⏳ Should be in DB | ⏳ Future work |

---

## 🚀 Next Steps

### Immediate (To Fix BOM Display)
- ✅ Done! Refresh your browser and the BOM menu will appear with improved role handling

### Short-term (Prevent Bugs)
1. Update backend `Role` enum from lowercase to UPPERCASE
2. Update `ROLE_PERMISSIONS` mappings to match new enum
3. Test all permission checks

### Long-term (Production Ready)
1. Create `roles` table in PostgreSQL
2. Load roles from database instead of enum
3. Consider permission inheritance/heirarchy
4. Add role-based API endpoint for frontend role selection

---

## 📚 Industry Standards Applied

✅ **DRY Principle** - Define roles once, use everywhere  
✅ **Single Source of Truth** - `roles.config.ts` is definitive  
✅ **Type Safety** - Use enums instead of string magic  
✅ **Separation of Concerns** - Role metadata separate from UI logic  
✅ **Scalability** - Easy to add new roles, update descriptions, change permissions  
✅ **Maintainability** - Change role description in one place, updates everywhere  

---

## 🔧 Files Modified
- ✅ Created: `frontend/src/lib/roles.config.ts`
- ✅ Updated: `frontend/src/lib/constants.ts`
- ✅ Updated: `frontend/src/components/layout/Sidebar.tsx`
- ✅ Updated: `frontend/src/hooks/usePermissions.ts`
- ✅ Updated: `frontend/src/modules/users/pages/UserFormPage.tsx`
- ✅ Updated: `frontend/src/modules/users/components/UserFormDrawer.tsx`

---

## ⚠️ Important: Browser Refresh Required
After these changes, **refresh your frontend browser** (F5 or Ctrl+R) to load the new code. The BOM menu should now appear with improved type-safe role handling.

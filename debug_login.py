"""
Debug script to verify login credentials and user account status
"""
import asyncio
import os
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:123@localhost:5432/medtrack")

async def debug_user():
    """Check user account status in database"""
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Query to find the user
            query = text("""
                SELECT 
                    id,
                    email,
                    tenant_id,
                    first_name,
                    last_name,
                    role,
                    is_active,
                    is_deleted,
                    hashed_password,
                    created_at,
                    updated_at
                FROM users
                WHERE email = :email
                    AND tenant_id = :tenant_id
                LIMIT 1;
            """)
            
            result = await session.execute(query, {
                "email": "admin@medtrack-demo.com",
                "tenant_id": "b5ef68c4-18be-4fa6-a439-a23c34877550"
            })
            
            user = result.fetchone()
            
            if not user:
                print("❌ USER NOT FOUND")
                print("   No user with email 'admin@medtrack-demo.com' for tenant 'b5ef68c4-18be-4fa6-a439-a23c34877550'")
                
                # Try to find user by email across all tenants
                all_users = await session.execute(text("""
                    SELECT id, email, tenant_id, is_active, is_deleted
                    FROM users
                    WHERE email = :email
                """), {"email": "admin@medtrack-demo.com"})
                
                found_users = all_users.fetchall()
                if found_users:
                    print("\n   Found users with this email in OTHER tenants:")
                    for u in found_users:
                        print(f"     - ID: {u[0]}, Tenant: {u[2]}, Active: {u[3]}, Deleted: {u[4]}")
                else:
                    print("\n   No users with this email found in ANY tenant")
            else:
                print("✅ USER FOUND")
                print(f"\n   ID: {user[0]}")
                print(f"   Email: {user[1]}")
                print(f"   Tenant ID: {user[2]}")
                print(f"   Name: {user[3]} {user[4]}")
                print(f"   Role: {user[5]}")
                print(f"   Active: {user[6]} {'✅' if user[6] else '❌'}")
                print(f"   Deleted: {user[7]} {'❌ SOFT DELETED' if user[7] else '✅'}")
                print(f"   Password Hash: {user[8][:50]}..." if user[8] else "   Password Hash: None")
                print(f"   Created: {user[9]}")
                print(f"   Updated: {user[10]}")
                
                # Check why login might be failing
                print("\n📋 LOGIN CHECK:")
                if not user[6]:
                    print("   ❌ Account is INACTIVE - user.is_active = False")
                    print("   → This is why login fails!")
                else:
                    print("   ✅ Account is active")
                
                if user[7]:
                    print("   ❌ Account is SOFT DELETED - user.is_deleted = True")
                    print("   → This is why login fails!")
                else:
                    print("   ✅ Account is not deleted")
                
                # Show password hash status
                if user[8]:
                    print(f"   ✅ Password hash exists (length: {len(user[8])})")
                    print(f"      Hash: {user[8]}")
                    
                    # Try to test if it's a valid bcrypt hash
                    import bcrypt
                    try:
                        test_password = "Demo@1234"
                        is_valid = bcrypt.checkpw(test_password.encode(), user[8].encode())
                        if is_valid:
                            print(f"   ✅ Password 'Demo@1234' MATCHES the hash")
                        else:
                            print(f"   ❌ Password 'Demo@1234' DOES NOT match the hash")
                            print(f"      → The password in the database is different")
                    except Exception as e:
                        print(f"   ⚠️  Could not verify password hash: {e}")
                else:
                    print("   ❌ No password hash found")
            
            # Also check tenant exists
            print("\n📋 TENANT CHECK:")
            tenant_query = text("""
                SELECT id, name, slug FROM tenants WHERE id = :tenant_id
            """)
            tenant_result = await session.execute(tenant_query, {
                "tenant_id": "b5ef68c4-18be-4fa6-a439-a23c34877550"
            })
            tenant = tenant_result.fetchone()
            
            if tenant:
                print(f"   ✅ Tenant found: {tenant[1]} (slug: {tenant[2]})")
            else:
                print(f"   ❌ Tenant NOT found with ID b5ef68c4-18be-4fa6-a439-a23c34877550")
    
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("=" * 70)
    print("  DEBUG: Login Credential Verification")
    print("=" * 70)
    print(f"\nChecking credentials:")
    print(f"  Email: admin@medtrack-demo.com")
    print(f"  Password: Demo@1234")
    print(f"  Tenant ID: b5ef68c4-18be-4fa6-a439-a23c34877550")
    print("\n" + "=" * 70 + "\n")
    
    asyncio.run(debug_user())
    
    print("\n" + "=" * 70)

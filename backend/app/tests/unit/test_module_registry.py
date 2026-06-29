from backend.app.core.module_registry import ModuleRegistry


def test_get_system_map_matches_lowercase_role_names():
    registry = ModuleRegistry()
    original_modules = registry._modules.copy()
    original_locked = registry._locked

    try:
        registry._modules = {}
        registry._locked = False
        registry.register(
            id="warehouse",
            name="Warehouse Management",
            route="/warehouses",
            dependencies=[],
            roles=["ADMIN"],
            status="active",
            icon="Warehouse",
        )

        result = registry.get_system_map("admin")

        assert any(module["id"] == "warehouse" for module in result["modules"])
    finally:
        registry._modules = original_modules
        registry._locked = original_locked

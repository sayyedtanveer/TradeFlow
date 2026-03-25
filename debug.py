import traceback

try:
    from backend.app.main import app
    print("App imported successfully!")
except Exception as e:
    traceback.print_exc()

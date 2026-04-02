import traceback
try:
    from api.main import app
    print("Import OK!")
except Exception as e:
    traceback.print_exc()

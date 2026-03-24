import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

modules_to_test = [
    'utils.data_utils',
    'utils.ui_utils',
    'utils.geo_utils',
    'ml.model',
    'ml.image_model',
    'ml.model_tracker',
    'auth.user_auth',
    'auth.agent_auth',
    'dashboard.landing',
    'dashboard.user_dashboard',
    'dashboard.agent_dashboard',
    'main'
]

print("Starting Import Diagnostics...")
errors = []

for module in modules_to_test:
    try:
        print(f"Testing {module}...", end=" ")
        __import__(module)
        print("OK")
    except Exception as e:
        print("FAILED")
        errors.append((module, str(e)))

if errors:
    print("\nErrors Found:")
    for mod, err in errors:
        print(f"- {mod}: {err}")
else:
    print("\nAll core modules imported successfully!")

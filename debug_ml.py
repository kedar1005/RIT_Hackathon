from ml.model import init_model
import os

print("Initializing ML model...")
init_model()
model_path = os.path.join("db", "models", "classifier.pkl")
if os.path.exists(model_path):
    print(f"✅ ML model initialized successfully at {model_path}")
else:
    print(f"❌ ML model initialization failed.")

import pandas as pd
from utils.report_utils import generate_word_report
import traceback

df = pd.DataFrame({"ID": [1], "Status": ["Pending"]})

try:
    generate_word_report(df)
    print("SUCCESS: Word document with charts generated successfully.")
except Exception as e:
    print(f"FAILED: {e}")
    traceback.print_exc()

import os
import sys

# Add root folder to path
sys.path.append(os.getcwd())

from utils.security import build_google_auth_flow

try:
    print("Building flow...")
    flow = build_google_auth_flow()
    print("Running local server...")
    # Run with open_browser=False so it doesn't open a browser on the machine in the background
    creds = flow.run_local_server(host="127.0.0.1", port=0, prompt="consent", open_browser=False)
    print("Done!")
except Exception as e:
    import traceback
    traceback.print_exc()

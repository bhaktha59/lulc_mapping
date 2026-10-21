"""
Secure Helper Utility to Export Google Earth Engine Token for Cloud Deployment.
Run this script to retrieve the single-line JSON string needed for the
EARTHENGINE_TOKEN secret environment variable on Render, Railway, or Google Cloud Run.
"""

import os
import json
import ee.oauth

def export_token():
    cred_path = ee.oauth.get_credentials_path()
    if not os.path.exists(cred_path):
        print(f"[ERROR] No Earth Engine credentials found at: {cred_path}")
        print("Please run 'earthengine authenticate' first.")
        return

    try:
        with open(cred_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Verify required keys
        if "refresh_token" not in data:
            print("[ERROR] Credentials file does not contain a refresh_token.")
            return

        token_str = json.dumps(data)
        print("=" * 70)
        print(" GOOGLE EARTH ENGINE CLOUD ENVIRONMENT VARIABLE (EARTHENGINE_TOKEN)")
        print("=" * 70)
        print("\nCopy the single line below and paste it as the value for:")
        print("Variable Name: EARTHENGINE_TOKEN\n")
        print(token_str)
        print("\n" + "=" * 70)
        print("Keep this token private! Do not commit it to GitHub or share publicly.")
        print("=" * 70)
    except Exception as e:
        print(f"[ERROR] Failed to read credentials: {e}")

if __name__ == "__main__":
    export_token()

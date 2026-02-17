import os
import sys
from pathlib import Path

def validate():
    # Look for .env in the workspace root relative to the script location
    # Structure: skills/.env <- skills/stitch-ui-generator/scripts/validate_env.py
    root_env = Path(__file__).parent.parent.parent / ".env"
    
    if not root_env.exists():
        print(f"ERROR: .env file not found at {root_env}")
        sys.exit(1)

    with open(root_env, "r") as f:
        content = f.read()
        if "GOOGLE_STITCH_API_KEY" not in content:
            print("ERROR: GOOGLE_STITCH_API_KEY not found in .env")
            sys.exit(1)
            
    print("SUCCESS: Environment validated. API key found.")
    sys.exit(0)

if __name__ == "__main__":
    validate()

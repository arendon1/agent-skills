import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")

if not MONDAY_API_KEY:
    print("Error: MONDAY_API_KEY environment variable not found.")
    sys.exit(1)

def get_config():
    if os.path.exists(".monday_config.json"):
        try:
            with open(".monday_config.json", 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def update_column_value(board_id, item_id, column_id, value):
    # Try to parse value as JSON, if it fails, treat as simple string (which works for simple_column_value)
    # Actually, change_simple_column_value takes a string. change_column_value takes JSON.
    # We will use change_simple_column_value for ease of use with Status labels and Text.
    
    mutation = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: String!) {
        change_simple_column_value (board_id: $boardId, item_id: $itemId, column_id: $columnId, value: $value) {
            id
        }
    }
    """
    
    variables = {
        "boardId": int(board_id),
        "itemId": int(item_id),
        "columnId": column_id,
        "value": value
    }
    
    headers = {"Authorization": MONDAY_API_KEY, "API-Version": "2023-10"}
    try:
        response = requests.post(url=MONDAY_API_URL, json={'query': mutation, 'variables': variables}, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error updating item: {e}")
        sys.exit(1)

def main():
    # Usage: python update_item.py <item_id> <column_id> <value>
    # or with flags
    if len(sys.argv) < 4:
        print("Usage: python update_item.py <item_id> <column_id> <value>")
        sys.exit(1)
        
    item_id = sys.argv[1]
    column_id = sys.argv[2]
    value = sys.argv[3]
    
    config = get_config()
    board_id = config.get('board_id')
    
    if not board_id:
        print("Error: Board ID not configured. Run save_config.py first or provide board_id manually (not supported in cli yet).")
        sys.exit(1)
        
    print(f"Updating Item {item_id}: {column_id} -> {value}")
    result = update_column_value(board_id, item_id, column_id, value)
    
    if 'data' in result and result['data']['change_simple_column_value']:
        print("Update successful.")
    else:
        print("Update failed.")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

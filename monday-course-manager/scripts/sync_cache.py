import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
CACHE_FILE = ".monday_cache.json"

if not MONDAY_API_KEY:
    print("Error: MONDAY_API_KEY environment variable not found. Please set it in your .env file.")
    sys.exit(1)

def get_boards_query(board_ids=None):
    """Constructs the GraphQL query to fetch board data."""
    board_filter = ""
    if board_ids:
        # Convert all IDs to integers if they are digit strings, to be safe, or just use json.dumps
        # Monday IDs are typically exceptionally large integers.
        # But let's just make sure we use double quotes.
        # If board_ids contains strings, json.dumps will produce ["id1", "id2"] which is valid GraphQL.
        # If they are ints, it produces [id1, id2].
        # The issue was Python's str() using single quotes for list of strings.
        board_filter = f"(ids: {json.dumps(board_ids)})"
    
    return """
    query {
      boards%s {
        id
        name
        items_page(limit: 500) {
          items {
            id
            name
            state
            group {
              id
              title
            }
            column_values {
              id
              text
              value
              type
            }
          }
        }
      }
    }
    """ % board_filter

def fetch_data(query):
    """Executes the GraphQL query against the Monday.com API."""
    headers = {"Authorization": MONDAY_API_KEY, "API-Version": "2023-10"}
    try:
        response = requests.post(url=MONDAY_API_URL, json={'query': query}, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

def save_cache(data, filepath):
    """Saves the fetched data to a local JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Successfully cached Monday.com data to {filepath}")
    except IOError as e:
        print(f"Error saving cache file: {e}")

def main():
    # If board IDs are passed as arguments, use them. Otherwise fetch all (or limit logic).
    board_ids = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Check for config file if no args provided
    if not board_ids and os.path.exists(".monday_config.json"):
        try:
            with open(".monday_config.json", 'r') as f:
                config = json.load(f)
                if 'board_id' in config:
                    board_ids = [config['board_id']]
                    print(f"Using configured board ID: {config['board_id']}")
        except Exception as e:
            print(f"Warning: Could not read config file: {e}")
            
    print("Fetching data from Monday.com...")
    query = get_boards_query(board_ids)
    result = fetch_data(query)
    
    if 'data' in result:
        save_cache(result['data'], CACHE_FILE)
    elif 'errors' in result:
        print("API returned errors:")
        for error in result['errors']:
            print(f"- {error['message']}")
    else:
        print("Unexpected response format.")

if __name__ == "__main__":
    main()

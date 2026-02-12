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

if not MONDAY_API_KEY:
    print("Error: MONDAY_API_KEY environment variable not found. Please set it in your .env file.")
    sys.exit(1)

def query_monday(query):
    headers = {"Authorization": MONDAY_API_KEY, "API-Version": "2023-10"}
    try:
        response = requests.post(url=MONDAY_API_URL, json={'query': query}, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

def list_boards():
    query = """
    query {
        boards(limit: 50) {
            id
            name
            workspace {
                id
                name
            }
        }
    }
    """
    data = query_monday(query)
    if 'data' in data and 'boards' in data['data']:
        return data['data']['boards']
    return []

def main():
    boards = list_boards()
    print(json.dumps(boards, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()

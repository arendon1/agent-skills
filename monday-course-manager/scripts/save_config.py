import os
import sys
import json

CONFIG_FILE = ".monday_config.json"

def save_config(board_id, board_name=None):
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    config = loaded
        except:
            pass
            
    config['board_id'] = board_id
    if board_name:
        config['board_name'] = board_name
        
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"Configuration saved to {CONFIG_FILE}: Board ID = {board_id}, Name = {board_name or 'N/A'}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python save_config.py <board_id> [board_name]")
        return
        
    board_id = sys.argv[1]
    board_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    save_config(board_id, board_name)

if __name__ == "__main__":
    main()

import sys
import re

def validate_code(code):
    # Check for basic HTML structure if it looks like a full page
    has_errors = False
    
    if "<html" in code.lower() and "</html>" not in code.lower():
        print("WARNING: Missing </html> tag.")
        has_errors = True
        
    # Check for jQuery usage if requested
    if "jquery" in code.lower() and "$" not in code:
        print("WARNING: Code mentions jQuery but no $ usage found.")
        
    # Check for common script tag errors
    if "<script" in code and "</script>" not in code:
        print("ERROR: Unclosed <script> tag detected.")
        has_errors = True

    if has_errors:
        print("\nStatus: FAILED validation. Review code manually.")
    else:
        print("\nStatus: PASSED basic syntax check.")

if __name__ == "__main__":
    # Expect code to be passed via stdin or file
    code_input = sys.stdin.read()
    if not code_input.strip():
        print("ERROR: No code provided for validation.")
        sys.exit(1)
    
    validate_code(code_input)

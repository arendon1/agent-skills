from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    print(f"p: {type(p)}")
    print(f"p.chromium: {type(p.chromium)}")
    print(f"Has launch_persistent_context? {hasattr(p.chromium, 'launch_persistent_context')}")

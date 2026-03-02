# Authentication Architecture

## Overview

This skill uses a **hybrid authentication approach** that combines the best of both worlds:

1. **Persistent Browser Profile** (`user_data_dir`) for consistent browser fingerprinting.
2. **Manual Cookie Injection** from `state.json` for reliable session cookie persistence.

## Why This Approach?

### The Problem

Playwright/Patchright has a known bug where **session cookies** (cookies without an `Expires` attribute) do not persist correctly when using `launch_persistent_context()` with `user_data_dir`.

**What happens:**

- ✅ Persistent cookies (with `Expires` date) → Saved correctly to browser profile.
- ❌ Session cookies (without `Expires`) → **Lost after browser restarts**.

**Impact:**

- Some Google auth cookies are session cookies.
- Users experience random authentication failures.

### Python Workaround

Python's Playwright API doesn't support passing `storage_state` directly into `launch_persistent_context` (unlike the TypeScript version).

## Our Solution: Hybrid Approach

We use a **two-phase authentication system**:

### Phase 1: Setup (`auth_manager.py setup`)

1. Launch persistent context with `user_data_dir`.
2. User logs in manually in the appearing browser window.
3. **Save state to TWO places:**
   - Browser profile directory (automatic, for fingerprint + persistent cookies).
   - `state.json` file (explicit save, for session cookies).

### Phase 2: Runtime (`ask_question.py`)

1. Launch persistent context with `user_data_dir`.
2. **Manually inject cookies** from `state.json`.

```python
with open("state.json", 'r') as f:
    state = json.load(f)
    context.add_cookies(state['cookies'])  # ← Workaround for session cookies!
```

## Benefits

- **Browser Fingerprint Consistency**: High trust from Google's anti-bot systems.
- **Session Cookie Persistence**: No random logouts.
- **Cache Performance**: Retains browser cache for faster loading.

## File Structure

```
notebooklm-skill/data/
├── auth_info.json              # Metadata about authentication
├── browser_state/
│   ├── state.json             # Cookies + localStorage (for manual injection)
│   └── browser_profile/       # Chrome user profile (for fingerprint + cache)
```

## Disclaimer

This architecture is designed for reliability and anti-detection. Always follow Google's Terms of Service and use a dedicated account for automated research tasks.

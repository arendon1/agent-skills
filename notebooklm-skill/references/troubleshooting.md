# NotebookLM Skill Troubleshooting Guide

## Quick Fix Table

| Error | Solution |
|-------|----------|
| ModuleNotFoundError | Use `python scripts/run.py [script].py` |
| Authentication failed | Browser must be visible for setup |
| Browser crash | `python scripts/run.py cleanup_manager.py --preserve-library` |
| Rate limit hit | Wait 1 hour or switch accounts |
| Notebook not found | `python scripts/run.py notebook_manager.py list` |
| Script not working | Always use run.py wrapper |

## Critical: Always Use run.py

Most issues are solved by using the `run.py` wrapper:

```bash
# ✅ CORRECT - Always:
python scripts/run.py auth_manager.py status
python scripts/run.py ask_question.py --question "..."

# ❌ WRONG - Never:
python scripts/auth_manager.py status  # ModuleNotFoundError!
```

## Common Issues and Solutions

### Authentication Issues

#### Not authenticated error

```
Error: Not authenticated. Please run auth setup first.
```

**Solution:**

```bash
# Check status
python scripts/run.py auth_manager.py status

# Setup authentication (browser MUST be visible!)
python scripts/run.py auth_manager.py setup
# User must manually log in to Google
```

### Browser Issues

#### Browser crashing or hanging

**Solution:**

```bash
# Clean browser state
python scripts/run.py cleanup_manager.py --confirm --preserve-library

# Re-authenticate
python scripts/run.py auth_manager.py reauth
```

#### Browser not found error

**Solution:**

```bash
# Use run.py (automatic setup)
python scripts/run.py auth_manager.py status

# Manual install if needed
cd notebooklm-skill
.venv/Scripts/activate  # Windows
python -m patchright install chromium
```

---

## Prevention Tips

1. **Always use run.py** - Prevents 90% of issues.
2. **Regular maintenance** - Clear browser state weekly.
3. **Monitor queries** - Track daily count to avoid limits.
4. **Backup library** - Export `data/library.json` regularly.
5. **Use dedicated account** - Separate Google account for automation.

## FAQ

**Q: Why doesn't this work in the Web UI?**
A: Web UIs run in a sandbox without network access. This skill requires local machine execution for browser automation.

**Q: Is this safe for my Google account?**
A: Real Chrome/Playwright interactions are used with human-like delays. However, a dedicated Google account is always recommended for automated tasks.

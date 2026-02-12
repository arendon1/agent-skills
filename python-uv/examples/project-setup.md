
# Example: Setting up a new Python Data Project

This example demonstrates how an agent interacts with a user to set up a new data science project using `uv`.

**User:** "Create a new python project called 'data-analysis' with pandas and numpy."

**Agent:**

I'll create a new Python project named `data-analysis` using `uv` and add the requested dependencies.

```bash
# Initialize the project
uv init data-analysis
cd data-analysis

# Add dependencies
uv add pandas numpy
```

*Output:*

```text
Initialized project `data-analysis` at `/path/to/data-analysis`
Added pandas v2.2.0
Added numpy v1.26.0
```

**User:** "Great, now add ruff for linting and run it."

**Agent:**

I'll add `ruff` as a development dependency and run a check.

```bash
# Add ruff as dev dependency
uv add --dev ruff

# Run ruff check
uv run ruff check .
```

*Output:*

```text
Added ruff v0.1.0 to dev-dependencies
All checks passed!
```

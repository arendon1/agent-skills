# Context Patterns: Course Manager

Patterns for maximizing signal-to-noise ratio in student workspaces.

## 📉 Token-Lean AGENTS.md

Always prioritize permanent links over relative navigation. Use the following structured blocks:

1. **Identity Block**: Clearly define `COURSE_ID` and `PERIOD`.
2. **Resource Table**: Only list authoritative Moodle links.
3. **PGA Summary**: Use a compact Markdown table.

## 📝 README.md Standards

The `README.md` is for the human (the student). Keep it visually rich:

- Use Emojis for status (✅, 📥, 📅).
- Link to internal `Unidad-X` folders.
- Maintain a "Próximas Entrega" section for quick visibility.

## 🧠 Rule Context

Deploy `.agents/rules/moodle-folders.md` to ensure any LLM opening this folder immediately understands the architectural constraints and does not create disorganized files.

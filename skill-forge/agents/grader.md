# Grader Agent Instructions

You are a grader agent evaluating the output of a skill evaluation run.

## Input

You will receive:

- `eval_metadata.json` - Contains the eval prompt and expected output description
- `outputs/` directory - Contains the files produced by the skill
- `grading.json` (template to fill) - Where you save your grades

## Your Task

1. Read `eval_metadata.json` to understand what was being tested
2. Navigate the `outputs/` directory to examine what the skill produced
3. For each expectation in `eval_metadata.json["expectations"]`:
   - Evaluate whether the output satisfies the expectation
   - Mark as passed=true or passed=false
   - Provide evidence explaining your reasoning

## Grading Criteria

- **Factual assertions**: Verify against the actual output files
- **Structural assertions**: Check if expected format/structure is present
- **Behavioral assertions**: Confirm the skill followed the documented workflow
- **Quality assertions**: Judge completeness and coherence

## Output Format

Write your grades to `grading.json` in the same directory as this readme:

```json
{
  "expectations": [
    {
      "text": "The exact expectation text",
      "passed": true,
      "evidence": "Why it passed - quote from output or observation"
    },
    {
      "text": "Another expectation",
      "passed": false,
      "evidence": "Why it failed - what was missing or incorrect"
    }
  ],
  "summary": {
    "passed": 5,
    "failed": 2,
    "total": 7,
    "pass_rate": 0.71
  },
  "execution_metrics": {
    "tool_calls": { "Read": 5, "Write": 2, "Bash": 8 },
    "total_tool_calls": 15,
    "total_steps": 6,
    "errors_encountered": 0,
    "output_chars": 12450,
    "transcript_chars": 3200
  },
  "timing": {
    "executor_duration_seconds": 165.0,
    "grader_duration_seconds": 26.0,
    "total_duration_seconds": 191.0
  },
  "claims": [
    {
      "claim": "The form has 12 fillable fields",
      "type": "factual",
      "verified": true,
      "evidence": "Counted 12 fields in field_info.json"
    }
  ],
  "user_notes_summary": {
    "uncertainties": ["Used 2023 data, may be stale"],
    "needs_review": [],
    "workarounds": ["Fell back to text overlay for non-fillable fields"]
  },
  "eval_feedback": {
    "suggestions": [
      {
        "assertion": "The output includes the name 'John Smith'",
        "reason": "A hallucinated document that mentions the name would also pass"
      }
    ],
    "overall": "Assertions check presence but not correctness."
  }
}
```

## Important

- Use the EXACT field names: `text`, `passed`, `evidence` (not `name`/`met`/`details`)
- Be objective and provide clear evidence for each verdict
- For file-based outputs, actually read the files to verify claims
- If an expectation is subjective, note that in the evidence but still provide a pass/fail

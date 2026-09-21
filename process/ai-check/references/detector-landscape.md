# Reference detector landscape (snapshot)

Snapshot of commercial/canonical detectors, for when the user asks "what would tool X say?".

- **GPTZero (2025)** uses RL adversarial self-training plus a learned classifier ensemble, not just
  perplexity + burstiness. Produces a 4-class output (human / slight / moderate / full AI-assist).
  Older "GPTZero relies on perplexity + burstiness" framing is stale.
- **Binoculars** is a strong zero-shot baseline but has the Claude blind spot (recognizes Claude text as human ~60% of the time).
- **Pangram 3.0** claims 99.98% accuracy with 1-in-10,000 FPR and 97% on humanized text per vendor
  benchmarks (independent replication pending).
- **EditLens** estimates AI-edit fraction rather than binary authorship (94.7 F1 binary, 90.4 F1 ternary).
- **Ghostbuster** is the canonical black-box (no token probs needed) detector — 99 F1 in-domain,
  degrades out-of-domain.
- **DependencyAI** uses syntactic dependency n-grams + LightGBM, cross-lingual without LLM access.
- **JEV (TypeSafe)** — system-one decision model. Scores 67.8% on TypeSafe's 4-workflow benchmark
  vs 74.1% GPT-5.6 Sol; reads text and emits typed probabilities for arbitrary categories the
  caller defines. Useful as a programmatic pre-filter (no LLM call needed); not a published
  "AI detector" in itself.

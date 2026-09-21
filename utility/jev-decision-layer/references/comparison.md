# JEV vs Laya vs fallback — decision aid

When to choose which backend for the decision layer.

| Dimension | JEV (TypeSafe, closed) | Laya (Convai, open) | Fallback (heuristic) |
|---|---|---|---|
| **Accuracy (own bench)** | 67.8% (TypeSafe) / 100% binary pass-fail (LangChain) | Reported ≥ JEV on AG News/emotion; weaker on 50+ option tasks | Reproducible but not calibrated |
| **Latency** | 70-500ms (real: 200-300ms) | 30-40ms standalone, 7ms batched (T4 GPU) | <1ms |
| **Cost / request** | ~$0.0004 per typical case | Compute only ($0 + electricity) | $0 |
| **Setup** | API key, 5 minutes | pip install laya, ~10 minutes for a T4 GPU | None |
| **Vendor lock-in** | High (closed weights, single vendor) | None (Apache 2.0) | None |
| **Vendor risk** | Pricing may rise post-subsidy; model may evolve; waitlist for some routes | Maintainer is a single founder (bus factor); smaller community | N/A |
| **Multilingual** | Not documented | 100+ languages | N/A |
| **Schema safety** | Yes | Yes (JEV-compatible) | No (deterministic only) |
| **Independent bench** | Not yet (only TypeSafe self-bench + LangChain eval) | Not yet either | N/A |

## Decision tree

```
Q1: Do you have a T4 GPU class machine and ops time?
├── Yes  → Consider Laya (open-source, no lock-in, ~30ms latency)
└── No   → Q2: Do you have an API key already?
    ├── Vercel AI Gateway key (free tier available)  → Use Vercel route
    ├── TypeSafe API key (waitlist)                  → Use TypeSafe direct
    ├── No key, but willing to spend $0             → Get Vercel key (5 min)
    └── No key, no budget                             → Fallback mode for now
```

## Break-even math (GeneLab, sept-2026)

For our volume today (< 1000 calls/month across all workflows), self-hosting
Laya is **NOT** cost-effective:

| Volume / month | Cheapest option | Cost |
|---|---|---|
| < 100K | Laya (self-host) wins | Compute only |
| 100K – 1M | Laya or JEV API (~$0.04/1M) | Tie at this scale |
| 1M – 52.6M | JEV API wins on simplicity | $0.04/1M |
| > 52.6M | Self-host Laya wins | Ceiling: your compute bill |

Today's recommendation: **Vercel AI Gateway** as default. It's the lowest-friction route:
- Free tier available while in beta
- One API key, no waitlist
- Same pricing as direct ($0.04/1M)
- Provides a clean migration path if TypeSafe changes anything

## When fallback is acceptable

The fallback returns deterministic but uncalibrated answers. It's safe for:
- **CI test runs** (so flows don't break when no key is set)
- **Local development** (when you want to iterate without spending)
- **Pre-deployment smoke tests** (where the real JEV call will happen in prod)
- **First-day adoption** (before credentials are configured)

It's NOT acceptable for:
- **Production traffic** (use live JEV or Laya)
- **Decisions with real blast radius** (always have a human in the loop)

If you want to forbid fallback in production, set `JEV_STRICT=1` — the client
will raise instead of silently returning mock data.

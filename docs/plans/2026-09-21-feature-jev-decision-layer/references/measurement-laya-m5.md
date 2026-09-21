# MEDICIÓN — Laya self-hosted en M5 (on-demand)

**Fecha**: 2026-09-21 · **Método**: instalación real en venv aislado, carga real, 20 corridas cronometradas
**Hardware**: Apple M5, 24 GB RAM, `torch 2.14.0`, **MPS disponible: True**

Anuncio previo (Tier 3 §14): install en venv aislado `~/.cache/laya-probe/`.
Egreso: `pypi.org` (allowlisted) + **`huggingface.co` (host nuevo, registrado aquí)**.

---

## Resultado: estimado vs medido

| Métrica | Estimado | **Medido** | Δ |
|---|---|---|---|
| Disco — pesos del modelo | 842 MB | **807 MB** | ✅ |
| Disco — venv (torch+transformers+laya) | ~3.5 GB | **688 MB** | ✅✅ 5× mejor |
| **Disco — total** | ~4.3 GB | **1.5 GB** | ✅✅ |
| RAM cargado | ~2.4 GB | **3.66 GB** | 🟡 1.5× peor (carga fp32) |
| Cold start desde cache | 3-5 s | **23.3 s** | 🟡 peor |
| Cold start con descarga | — | 179 s (una vez) | — |
| Latencia p50 (1 pregunta) | 40-100 ms | **25.4 ms** | ✅✅ mejor |
| Latencia p95 | — | **28.1 ms** | ✅ |
| Batch 10 preguntas | ~156 ms | **421 ms** | 🟡 2.7× peor |
| % de los 24 GB (en uso) | 10% | **15%** | 🟡 |

**Instalación**: 35 paquetes en 44 s (uv). `torch 2.14.0` con MPS funcional.

## Discriminación real (el test que importa)

Estado real de un slide H5P (uno al 100%, uno parcial) contra el preset `slide_done_v1`:

| Estado | `score_at_max` | `all_answers_committed` |
|---|---|---|
| Slide completo (3/3, todas respondidas) | **0.5546** | 0.6987 |
| Slide parcial (2/4 inputs vacíos) | **0.0011** | 0.0977 |
| **Separación** | **500×** | 7× |

**Laya discrimina correctamente y con enorme margen.** Pero — ver caveat 1.

## ⚠️ Caveat 1: el umbral de 0.95 NO sirve para Laya

Nuestra política `slide_done_v1` exige `>= 0.95` (calibrada para la escala de JEV).
Laya devolvió **0.55** para un slide inequívocamente completo.

- La **separación** (0.55 vs 0.001) es lo valioso — es una señal ordenada y utilizable.
- La **escala absoluta** es mucho más conservadora que la de JEV.

**Invariante**: el umbral es una propiedad del BACKEND, no del preset. Un umbral
único compartido entre JEV y Laya produce falsos negativos sistemáticos.
Debe recalibrarse contra etiquetas reales por backend.

## ⚠️ Caveat 2: el checkpoint avisa de su propia descalibración

```
RuntimeWarning: laya: this checkpoint ships temperatures outside [0.5, 5] which
would distort confidence; clamping choice:11+=0.1006. Treat confidence from the
affected buckets as uncalibrated.
```

El propio código del vendor avisa que, para preguntas `choice` de cardinalidad ≥11,
la **confianza no está calibrada**. Nuestros presets usan `choice` de 3 opciones
(`render_gate`, `triage_quality`, `ai_dimensions`), así que caen fuera del rango
afectado — pero es una advertencia que hay que respetar si algún día se sube la
cardinalidad.

## El veredicto operativo

El patrón on-demand **funciona**, porque el cold start real es 23 s (no los 180 s
que yo temía — esos incluían la descarga) y la latencia por llamada es 25 ms.

| Ruta | Cold start | 60 llamadas | **Total** |
|---|---|---|---|
| **Laya on-demand** | 23.3 s | 60 × 25 ms = 1.5 s | **24.8 s** |
| OpenRouter (v4-text) | 0 | 60 × 2.0 s = 120 s | **120 s** |
| JEV (si se autoriza) | 0 | 60 × 250 ms = 15 s | 15 s |

**Break-even: ~12 llamadas por corrida.** Por encima de eso, Laya on-demand gana.
Nuestro caso (60 slides, 9 drags) está muy por encima.

Sostenido en reposo: **0 bytes**. Durante un run: 3.66 GB por ~2 minutos.

## Lo que hay en disco ahora

```
~/.cache/laya-probe/.venv          688 MB   (torch + transformers + laya)
~/.cache/huggingface/hub/...laya   807 MB   (pesos + config + tokenizer)
────────────────────────────────────────
total                            1,495 MB
```

Nada de esto es persistencia (sin LaunchAgent, sin daemon, sin cron). Se borra con
`rm -rf ~/.cache/laya-probe` + el modelo del cache de HF.

## Pendientes que la medición destapó

1. **Umbrales per-backend** (caveat 1) — sin esto, el guardarraíl da falsos negativos.
2. **Egress `huggingface.co`** — autorizar explícitamente o cachear el modelo y
   cortar la dependencia (el modelo ya está en disco; no hace falta volver a bajarlo).
3. **RAM 3.66 GB** — se puede bajar si `laya.load` acepta dtype; la firma no expone
   `dtype`, pero el fuente lo menciona 10×. Vale la pena investigar bf16 (~2 GB).
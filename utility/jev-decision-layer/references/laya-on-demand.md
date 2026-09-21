# Recipe — Laya on-demand (el carril sin egreso)

Cierra los escenarios con bucle (guardarraíles por slide / por drag), donde el
carril OpenRouter es demasiado lento (2s × 60 = 120s).

## El patrón

Laya es una **librería pura** (`pip install laya`), no un servidor. Este skill
trae dos piezas que la convierten en un servicio efímero:

| Archivo | Rol |
|---|---|
| `scripts/laya_server.py` | Wrapper HTTP en `127.0.0.1`. Traduce JEV↔Laya. |
| `scripts/laya_on_demand.py` | Arranca → espera health → corre el comando → mata. |

## Uso

```bash
# 1. Instalar una vez (venv aislado, ~1.5 GB)
uv venv --python 3.12 ~/.cache/laya-probe/.venv
uv pip install --python ~/.cache/laya-probe/.venv/bin/python laya torch transformers

# 2. Correr CUALQUIER cosa con Laya caliente. Se mata al terminar.
python scripts/laya_on_demand.py \
  --python ~/.cache/laya-probe/.venv/bin/python \
  run -- python h5p_solve.py --course-id 16564 --use-jev-guard
```

El runner exporta `JEV_BACKEND=laya` + `JEV_BASE_URL=http://127.0.0.1:<port>` en el
subproceso, así que el cliente lo detecta solo y **no hay egreso a ninguna red**.

## Subcomandos

```bash
python scripts/laya_on_demand.py up       # arranca y deja el env listo
python scripts/laya_on_demand.py status   # ¿está vivo?
python scripts/laya_on_demand.py down     # mata
python scripts/laya_on_demand.py run -- <cmd>   # arranca, corre, mata
```

Reutiliza un servidor ya vivo si lo encuentra — no arranca un segundo.

## Números medidos (Apple M5, 2026-09-21)

| Métrica | Valor |
|---|---|
| Instalación | 688 MB de venv + 807 MB de pesos = **1.5 GB** |
| Cold start desde cache | **23-27 s** |
| Latencia p50 | **25-76 ms** |
| RAM durante el run | 3.66 GB |
| RAM en reposo | **0** |
| Costo por decisión | **$0** |
| Egreso | **ninguno** |

**Break-even vs OpenRouter: ~12 llamadas por corrida.** Por encima, Laya gana.

## El umbral es del backend, no del preset

Medición: Laya devolvió **0.81** en un slide inequívocamente completo, y **0.13**
en uno parcial. La separación es enorme, pero la escala es más conservadora que
la de JEV. Un umbral fijo compartido produce falsos negativos sistemáticos.

`jev.json → thresholds_by_backend` los resuelve:

```json
{"laya": {"noul_default": 0.40},
 "openrouter": {"noul_default": 0.75},
 "typesafe": {"noul_default": 0.95},
 "vercel":   {"noul_default": 0.95}}
```

**Provisional.** Estos valores salen de dos muestras etiquetadas, no de una curva
de calibración. Antes de confiar en producción con blast radius, etiquetar ~200
casos reales y ajustar.

## Aviso del propio checkpoint

```
RuntimeWarning: laya: this checkpoint ships temperatures outside [0.5, 5] which
would distort confidence; clamping choice:11+=0.1006. Treat confidence from the
affected buckets as uncalibrated.
```

Afecta a `choice` con **≥11 opciones**. Nuestros presets usan 3, así que quedan
fuera del rango — pero hay que respetarlo si se sube la cardinalidad.

## Higiene

- Bind **solo a 127.0.0.1** (Tier 3 §11). Nunca `0.0.0.0`.
- **Sin daemon, sin LaunchAgent, sin cron, sin sudo.** El proceso vive lo que dura
  el run y muere.
- `down` hace un barrido defensivo por `lsof` además del SIGTERM al grupo.
- Borrar todo: `rm -rf ~/.cache/laya-probe` + el modelo del cache de HF.
- `huggingface.co` es un **host nuevo** respecto de la allowlist Tier 1. El modelo
  ya está cacheado; la dependencia de red se puede cortar y no volver a tocarla.
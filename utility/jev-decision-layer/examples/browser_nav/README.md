# Experimento — Laya como capa de decisión para un agente de navegación CDP

**Pregunta**: ¿puede Laya decidir el estado de la página para que un agente navegue
un Chrome con CDP, reemplazando los predicados JS con polling del solver de cursos?

**Respuesta corta**: **no en esta tarea.** El heurístico gana, y Laya necesita al
heurístico como red de seguridad para llegar al final. Pero la experimentación
produjo cuatro hallazgos concretos que sí sirven.

---

## El montaje

| Pieza | Qué es |
|---|---|
| `fixture/index.html` | 7 estados que imita el flujo real: login → cursos → curso → H5P cargando → H5P listo → resuelto (+ error) |
| `browser_nav_agent.py` | Cliente CDP mínimo + dos clasificadores + política de acciones |
| Chrome efímero | `--headless=new --remote-debugging-port=9225`, perfil temporal en `/tmp`, borrado al final |
| Laya | Local, puerto 8791, `$0` |

La política vive **en código legible**, no en el modelo:

```python
NEXT_ACTION = {
    "course_list":      ("click", ".course-item"),
    "course_page":      ("click", ".activity.modtype_hvp"),
    "h5p_loading":      ("wait",  None),
    "h5p_ready":        ("click", "a.activity"),
    "content_resolved": ("stop",  "Actividad al máximo. Fin del flujo."),
    ...
}
```

## Resultado

| | **Laya** | **Heurística** |
|---|---|---|
| Navegó el flujo completo | ✅ (con 2 rescates) | ✅ |
| Aciertos de clasificación | **3/5** | **5/5** |
| Latencia de clasificación | 760 ms | **0 ms** |
| Costo | $0 | $0 |
| Determinista | ❌ | ✅ |
| Necesita red de seguridad | **sí** | no |

**Matriz de confusión** (los dos fallos de Laya):

| Página | Esperado | Laya dijo | conf | Heurística |
|---|---|---|---|---|
| login | `login_required` | `login_required` | 0.96 | ✓ |
| cursos | `course_list` | **`course_page`** | 0.56 | ✓ |
| curso | `course_page` | `course_page` | 0.86 | ✓ |
| error | `error_page` | `error_page` | 0.65 | ✓ |
| resuelto | `content_resolved` | **`course_page`** | 0.53 | ✓ |

Laya mapea consistentemente **"página con links" → `course_page`**, sin distinguir
catálogo / curso / resultado.

## Los cuatro hallazgos

### 1. El modelo de decisión tiene una distribución, y esto cae fuera
Laya (base ModernBERT + fine-tune de *email triage* y trayectoria de conversación)
no fue entrenada para clasificar DOM. En cambio **sí** funciona en verificación de
propiedad concreta: el guardarraíl de slides H5P dio **6/7** con el mismo modelo.
La diferencia no es la dificultad — es que una pregunta ("¿este slide llegó al
máximo?") cae en su distribución y la otra ("¿en qué pantalla estoy?") no.

### 2. Los criterios por opción importan, y mucho
Con etiquetas peladas (`["course_list", "course_page", ...]`) Laya dio **0.96 de
confianza en una clase equivocada**. Al darle descripciones por opción —el formato
de su API nativa— bajó a 0.56. Sigue equivocada, pero **la confianza ya avisa**.

### 3. La serialización no rescata una tarea fuera de distribución
Probé el blob en `clave=valor` y en lenguaje natural. El NL fue *peor*. Cuando la
tarea está fuera de distribución, ningún formato la arregla.

### 4. Las dos guardas que hacen usable el patrón (y que sí generalizan)

```
1. COMPUERTA DE CONFIANZA — solo en acciones TERMINALES.
   `stop` es irreversible: exige certeza. Medido: un DOM roto produjo
   `content_resolved` con conf 0.27 y habría cerrado el flujo en falso.
   Aplicarla también a los `click` bloquea clasificaciones CORRECTAS
   (`h5p_ready` con 0.39 quedaba en wait para siempre).

2. PRECONDICIÓN DE LA ACCIÓN — validar el click contra el DOM.
   Si el modelo dice `course_page` pero `.activity.modtype_hvp` no existe,
   la clasificación se contradice con la realidad. Se cae al heurístico
   para ESE paso. Esto rescató el run dos veces.
```

La #2 es la lección transferible: **una clasificación que implica una acción puede
verificarse contra el mundo antes de ejecutarla.** Es más barato y más fiable que
pedirle al modelo que sea más preciso.

## Cuatro bugs reales encontrados en el camino

| # | Bug | Por qué importa |
|---|---|---|
| 1 | `</script>` dentro de un template literal cierra el `<script>` exterior | El DOM quedó con código JS como texto → Laya clasificó basura con 0.27 |
| 2 | Los `<script>` insertados por `innerHTML` **no se ejecutan** | El timer del fixture nunca disparaba; el agente se quedó 12 pasos pegado |
| 3 | Chrome rechaza WebSocket sin `--remote-allow-origins` | Handshake 403 |
| 4 | La compuerta de confianza sobre `click` bloquea aciertos | Correcto pero inseguro ≠ incorrecto |

Los dos primeros son del fixture, no del modelo — pero el #1 muestra algo útil:
**con entrada basura, Laya respondió con confianza baja (0.27).** La calibración
funcionó como señal.

## Reproducir

```bash
# 1. fixture
cd examples/browser_nav/fixture && python3 -m http.server 8899 --bind 127.0.0.1 &

# 2. Chrome efímero
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --remote-debugging-port=9225 --remote-allow-origins=* \
  --user-data-dir=/tmp/chrome-jev-nav-probe --no-first-run about:blank &

# 3. Laya
python scripts/laya_on_demand.py --python <venv-con-laya> up

# 4. comparar
python examples/browser_nav/browser_nav_agent.py --port 9225 \
    --url "http://127.0.0.1:8899/?s=courses" --mode heuristica
python examples/browser_nav/browser_nav_agent.py --port 9225 \
    --url "http://127.0.0.1:8899/?s=courses" --mode laya
```

## Veredicto para el solver de cursos

**No meter Laya en el bucle de navegación.** El heurístico es más rápido, gratis,
determinista y más preciso — y ya está escrito.

**Sí usarlo en el punto de decisión concreto**: "¿este slide llegó al máximo
puntaje?" ahí dio 6/7 y es exactamente el bug que nos costó un trabajo el 14-sept.

La división correcta del trabajo:

| Capa | Responsable | Por qué |
|---|---|---|
| Navegación / máquina de estados | **predicados JS** | deterministas, verificables, 0ms |
| Verificación de propiedad concreta | **Laya** | probabilidad calibrada, 111ms, $0 |
| Juicio abierto / generación | **LLM** | es lo único que puede |
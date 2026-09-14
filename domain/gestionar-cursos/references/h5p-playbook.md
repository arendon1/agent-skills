# Playbook H5P: Resolución Automatizada e Idempotente

Guía técnica y operativa para resolver contenidos interactivos H5P (`mod_hvp`) en Moodle (Aula Virtual Uniremington). Documenta la arquitectura del DOM, invariantes críticos, mitigaciones ante bugs observados y el ritual de mejora continua para evitar repetir errores costosos.

---

## 0. Operativa y criterio de aceptación

Estas actividades **no otorgan nota en el curso (0%)**, pero **su calificación sí queda registrada**. El
criterio de aceptación es **10/10 en todas**: cualquier otra cosa significa que la actividad no quedó
completa o bien resuelta.

**Fuente autoritativa — la ÚNICA válida.** `grade/report/user/index.php?id=<course>`, sección
*Actividades no evaluables 0%*. La página del curso **omite** contenidos H5P: enumerando
`li.activity.modtype_hvp` de `course/view.php` se veían **6 de 12** contenidos, y los 6 restantes
quedaron sin resolver. El informe da el id del HVP, el nombre y la nota en escala 0–10
(`10,00` = 100%; `-` = nunca intentado), y sirve a la vez como **plan** y como **verificación final**.

**Qué cuenta como resuelto** (`ok` en el ledger):

| Condición | Aplica a |
|---|---|
| `score == max` en el propio H5P | todos |
| `deck_completo`: recorrer hasta el último slide **y pulsar el chequeo final** (`.h5p-show-solutions` del slide de resumen) | solo decks (`CoursePresentation`) |
| `verificacion_resumen.todas_al_100` (oráculo del resumen del deck) | decks que exponen resumen |

Resolver el quiz intermedio **no** cierra la actividad: el deck queda a medias. Los contenidos sin
slides (p. ej. `H5P.FindTheWords`) no tienen `deck_completo`; exigírselo produce un falso negativo.

**Higiene de pestañas.** Reusar antes que crear (`--tab-policy reuse`, por defecto) y cerrar las
sobrantes (`--cleanup-tabs`), tocando **solo** URLs del Aula Virtual — nunca pestañas del usuario en
otros sitios. En fan-out paralelo cada agente necesita su propia pestaña (`--tab-policy new`),
porque compartir pestaña los hace pisarse.

---

## 1. Cuándo usar este playbook

- **Ejecución estándar**: Cuando se deban completar actividades H5P interactivas dentro de un curso de Moodle de forma desatendida o asistida.
- **Depuración / Tareas fallidas**: Cuando un contenido reporte puntajes parciales (`0/N`, `N-1/N`), timeouts o falta de registro en calificaciones.
- **Soporte a nuevos tipos**: Cuando se agregue soporte a un nuevo tipo de tarea H5P dentro de [`h5p_solve.py`](file:///Users/andres.rendon/.agents/skills/gestionar-cursos/scripts/h5p_solve.py).
- **Inspección de regresiones**: Antes de modificar la lógica de espera, selectores o eventos xAPI.

---

## 2. Arquitectura del DOM H5P

El contenido interactivo no reside en el documento principal, sino encapsulado dentro de un `iframe`:

```javascript
// Acceso al documento e instancia raíz de H5P
const iframeDoc = document.querySelector('iframe.h5p-iframe').contentDocument;
const H = window[0].H5P; // window[0] corresponde al contentWindow del iframe
```

### Reglas estructurales del contenedor
1. **Verificación de existencia**: Siempre comprobar que `window[0]?.H5P?.instances?.length > 0` antes de invocar métodos.
2. **Jerarquía en CoursePresentation (CP)**:
   - Contenedor raíz: `CP = window[0].H5P.instances[0]`.
   - Diapositivas: `CP.children[slideIdx]`.
   - Tareas internas: `CP.children[slideIdx].children[childIdx].instance`.
   - Identificador de tipo: `instance.libraryInfo.machineName` (ej. `H5P.Blanks`, `H5P.SingleChoiceSet`).
3. **Renderizado perezoso (Lazy DOM)**: Los nodos del DOM correspondientes a una tarea solo existen físicamente en pantalla cuando su slide es el actual (`.h5p-slide.h5p-current`). Consultar `.h5p-blanks input` en el slide 0 devolverá 0 nodos aunque el slide 2 tenga preguntas.
4. **Navegación**: Utilizar exclusivamente `CP.jumpToSlide(slideIndex)`. Los clics sintéticos en la barra inferior de navegación no disparan de forma confiable los eventos de transición.
5. **Transiciones asíncronas**: `jumpToSlide` toma tiempo en montar el DOM, y componentes como `SingleChoiceSet` tardan aproximadamente 2 segundos en avanzar internamente entre preguntas.

### Snippets clave de inspección y salto

```javascript
// 1. Mapeo completo de instancias y tareas contenidas
(() => {
  const w = window[0];
  if (!w || !w.H5P || !w.H5P.instances || !w.H5P.instances.length)
    return JSON.stringify({ready: false});
  const I = w.H5P.instances[0];
  const tasks = [];
  (I.children || []).forEach((sl, si) => {
    (sl.children || []).forEach((c, ci) => {
      const ins = c.instance;
      const mn = ins && ins.libraryInfo && ins.libraryInfo.machineName;
      if (mn && !/^H5P\.(Image|AdvancedText|Video|Audio|Table|Link|Shape|Text)/.test(mn)) {
        tasks.push({slide: si, child: ci, machine: mn, score: ins.getScore?.(), max: ins.getMaxScore?.()});
      }
    });
  });
  return JSON.stringify({ready: true, contentId: I.contentId, tasks});
})();

// 2. Salto seguro de diapositiva
(() => {
  window[0].H5P.instances[0].jumpToSlide(TARGET_SLIDE);
  return JSON.stringify({ok: true});
})();

// 3. Verificación de readiness acotado al slide objetivo
(() => {
  const CP = window[0].H5P.instances[0], d = window[0].document;
  if (typeof CP.getCurrentSlideIndex === 'function' && CP.getCurrentSlideIndex() !== TARGET_SLIDE)
    return JSON.stringify({ok: false, why: 'otro-slide'});
  const slide = d.querySelectorAll('.h5p-slide')[TARGET_SLIDE];
  if (!slide) return JSON.stringify({ok: false, why: 'sin-slide'});
  const vis = Array.from(slide.querySelectorAll(SELECTOR)).filter(e => e.getClientRects().length > 0);
  return JSON.stringify({ok: vis.length > 0, n: vis.length});
})();
```

---

## 3. Reglas duras

1. **NUNCA usar `sleep` ciego ni pausas de tiempo fijas.**
   - *Fallo que la motivó*: Tiempos arbitrarios fallaban en conexiones lentas o generaban tiempos muertos innecesarios. Se debe realizar polling sobre la máquina de estados con predicado explícito (`wait_for(..., until=...)`).
2. **Anclar la condición de readiness al slide objetivo y al selector de la tarea esperada.**
   - *Fallo que la motivó*: Un readiness laxo basado en "hay algún input visible en pantalla" interactuó con el DOM residual del slide previo, rellenando inputs equivocados y degradando 6 contenidos completos de 100% a 0–75%.
3. **Verificar invariantes antes de interactuar (inputs visibles == huecos declarados).**
   - *Fallo que la motivó*: Si los inputs aún no terminaban de montarse en el DOM, se enviaban menos respuestas de las requeridas y se pulsaba comprobar, arruinando el intento.
4. **NUNCA usar banderas internas no verificadas como señal de avance (`answered`).**
   - *Fallo que la motivó*: En `SingleChoiceSet`, `S.choices[cur].answered` pasa a `true` inmediatamente al hacer clic, pero el índice real (`currentIndex`) tarda hasta 2 segundos en cambiar. Usar `answered` provocó bucles de 30 iteraciones sin avance. La señal válida es `S.currentIndex > cur`.
5. **No temer al re-clic: el clic en alternativas es idempotente.**
   - *Fallo que la motivó*: Se intentaba "proteger" el clic para no repetir llamadas, cuando el daño real provenía de no esperar la animación de cambio de pregunta. En H5P, clickear una opción ya respondida no altera negativamente el puntaje.
6. **NO recargar la página (`reload`) a mitad de una corrida.**
   - *Fallo que la motivó*: A diferencia de `Blanks`, `SingleChoiceSet` no reanuda respuestas parciales guardadas al recargar la página. Un refresco destruye inmediatamente el avance de la actividad.
7. **NUNCA adivinar respuestas: extraerlas siempre del propio objeto H5P.**
   - *Fallo que la motivó*: Intentos heurísticos fallaron sistemáticamente. El modelo expone las soluciones directamente en sus estructuras JS (`params.questions`, `choices.options.answers`, `params.correct`).
8. **Scopear el botón de verificación estrictamente al slide actual.**
   - *Fallo que la motivó*: `button.h5p-question-check-answer` global disparaba el chequeo de preguntas en diapositivas ocultas o inactivas.
9. **No confiar en la rehidratación del DOM para saber si un contenido está resuelto.**
   - *Fallo que la motivó*: Al abrir una página de Moodle con CoursePresentation, `getScore()` devuelve 0 porque las instancias se inicializan vacías. El progreso consolidado debe llevarse en un ledger local persistente.
10. **Garantizar idempotencia a nivel de actividad y curso.**
    - *Fallo que la motivó*: Re-ejecutar el solver sin control previo rehacía actividades ya perfectas, sobrecargando el navegador y arriesgando degradación por fallos transitorios.
11. **Resolver la tarea NO cierra la actividad: hay que llegar al slide de RESUMEN y pulsar el chequeo final.**
    - *Fallo que la motivó*: el solver daba la actividad por completa al resolver el quiz del slide 5/13. El deck quedaba a medias y el botón que cierra el intento (`Mostrar solución`, `.h5p-show-solutions` en el slide `.h5p-summary-slide`) nunca se pulsaba. Señalado por Andrés el 2026-09-14.
    - Regla operativa: contestar TODAS las actividades primero, y **después** ir al último slide a dar por terminado.
12. **El total de slides es `CP.slides.length`, NO `CP.children.length`.**
    - *Fallo que la motivó*: en un deck real, `CP.slides.length = 13` y `CP.children.length = 12`: `children` NO incluye el slide de resumen. Iterar por `children` hacía imposible llegar al chequeo final. Verificar siempre contra el contador visible del deck ("3 / 13").
13. **Confirmar que el salto de slide ocurrió; no basta con esperarlo.**
    - *Fallo que la motivó*: `CP.jumpToSlide(i)` se **ignora en silencio** si se pide mientras la transición anterior sigue en curso. En vivo, todos los slides IMPARES quedaban sin alcanzar (el índice se quedaba en el par anterior), la tarea no estaba en el DOM y el solver abortaba con `n inputs == 0`. Hay que **re-emitir el salto** hasta que el índice cambie de verdad, no solo esperar.
14. **El resumen del deck es el ORÁCULO de verificación.**
    - El slide de resumen lista, actividad por actividad, su slide, su porcentaje y su puntaje (`Diapositiva 6: Actividad 1 100% 3/3`). Parsearlo permite verificar que no quedó ninguna sin resolver **sin recorrer el deck entero**, y detectar si un atajo se comió una actividad.
15. **Optimización del recorrido: plan = slides con actividad + slide de resumen.**
    - *Por qué*: recorrer los 13 slides cuando las actividades están en 2 es desperdicio. Medido en el curso 16564: **41 s / 211 llamadas al navegador → 11 s / 71 llamadas** (−73% tiempo, −66% llamadas), con resultado idéntico verificado por el oráculo.
    - *Guardarraíl*: el plan sale del pre-scan de instancias y se verifica contra el resumen; si el resumen conoce más actividades de las que el plan cubrió, se cae a recorrido completo UNA vez (`--full-walk` fuerza el recorrido exhaustivo para validar).
16. **Para fan-out, preferir Chrome (CDP) sobre la WKWebView de cmux.**
    - Chrome carga TODAS las pestañas aunque no tengan foco, así que N agentes en paralelo no se pisan. Usar el perfil autorizado `~/.agents/.browserdata` en el puerto 9224 y verificar la identidad del perfil (`navegador_cdp.perfil_de_puerto` + `is_authorized`) antes de operar. Cada agente abre SU PROPIA pestaña.
17. **Confirmar el slide actual por ÍNDICE **y** por CLASE DOM: no son lo mismo ni se actualizan juntos.**
    - *Fallo que la motivó*: `CP.getCurrentSlideIndex()` se actualiza **antes** de que la clase `.h5p-current` se mueva al nuevo slide. Confirmar solo el índice (o solo esperar) dejaba los selectores scoped apuntando al slide ANTERIOR: al pedir el slide 6 se leyeron los **3 inputs del slide 5** (`nInputs 3 / esperados 2`), la invariante abortó y la actividad quedó en 3/5. Toda query por selector debe anclarse a `.h5p-slide.h5p-current` **verificando además** `indexOf(current) === si`.
    - Corolario: la invariante “nº de inputs visibles == nº de huecos” es la que evita que este desfase **corrompa** un slide ya resuelto; sin ella se habrían escrito las respuestas del slide 6 dentro del slide 5.
18. **El informe de calificaciones (`grade/report/user`) es la fuente AUTORITATIVA, no la página del curso.**
    - *Fallo que la motivó*: enumerar `li.activity.modtype_hvp` en la página del curso veía **6 de 12** contenidos interactivos. Los otros 6 (p. ej. los "Parte 2") no aparecen ahí y quedaron **sin resolver**. El informe lista los 12, con su nota en escala 0–10 (`10,00` = 100%; `-` = nunca intentado). Se usa a la vez como **plan** y como **verificación final**.
19. **CDP usa coordenadas del viewport SUPERIOR: hay que sumar el rect del iframe.**
    - *Fallo que la motivó*: `getBoundingClientRect()` dentro del iframe H5P es relativo al iframe. Sin sumar el offset se enviaba (198,650) y el canvas recibía (56,278) — el drag "no hacía nada" sin error visible.
20. **Comprobar los DOS ejes del viewport, no solo el vertical.**
    - *Fallo que la motivó*: se scrolleaba para que la celda entrara en alto pero no en ancho. Con el canvas a la derecha (x≈1098) el extremo de una palabra larga caía fuera y el evento no llegaba; palabras cortas como `EOQ` quedaban sin marcar. Hay que verificar `innerW` igual que `innerH`.
21. **Sopa de letras (`H5P.FindTheWords`): canvas ⇒ drags REALES por CDP, uno por celda.**
    - No hay celdas en el DOM que clickear y los eventos sintéticos de JS no disparan los handlers: hay que usar `Input.dispatchMouseEvent` (pipeline de input real). Emitir **al menos un `mouseMoved` por celda** (con pasos fijos el puntero salta celdas y la librería reconstruye una palabra más corta) y **releer la geometría del canvas antes de cada palabra** (al marcar palabras cambia la lista de vocabulario y con ella la altura de la página).
    - El grid se construye **de forma asíncrona**: la instancia H5P existe antes que `I.grid.$drawingCanvas`. Falta de puerta de readiness ⇒ `Uncaught` y geometría inválida.
    - Último recurso documentado (si el drag falla 2 veces): reproducir el handler `drawEnd` de la librería (`vocabulary.checkWord(word)` → `numFound++` → `counter.increment()` → `grid.markWord(...)`) y marcarlo como `via: api` en el resultado. **Nunca en silencio.**
22. **Higiene de pestañas: reusar antes que crear, y cerrar las sobrantes.**
    - *Fallo que la motivó*: cada corrida/probe abría su pestaña y `close()` solo cerraba el WebSocket ⇒ 20+ pestañas huérfanas. Política: `--tab-policy reuse` (default) **adopta** una pestaña existente del Aula Virtual y al final deja **una** viva; `--tab-policy new` (obligatorio en fan-out paralelo) abre la propia y la cierra al terminar. `--cleanup-tabs` limpia lo que dejaron corridas anteriores, tocando **solo** URLs del Aula Virtual (nunca pestañas del usuario en otros sitios).
    - Ojo con el constructor: con `reuse` la pestaña adoptada **ya existía**, así que el `url` del constructor no se aplicaba y el consumidor quedaba en la página vieja en silencio. Ahora el contrato es el mismo en ambos casos (al salir se está en `url`).
23. **Para la sopa de letras: ZOOM OUT en vez de scrollear.**
    - Idea de Andrés (2026-09-14). Se agranda el viewport lógico con `Emulation.setDeviceMetricsOverride` al tamaño que necesita el tablero, y así **todas** las celdas caen dentro: los drags quedan triviales y desaparecen los round-trips de scroll (que además son frágiles porque el rect del canvas se mueve al marcarse palabras).
    - *Medición*: ventana 1600×933 ⇒ **4/9 palabras fuera del viewport** (`PUNTODEREORDEN`, `LEADTIME`, `EFICIENCIA`, `ALMACENAMIENTO`) → drags fallidos. Con zoom out ⇒ **0/9 fuera**. Es exactamente la clase de fallo que producía el 8/9.
    - Limpiar siempre al terminar (`Emulation.clearDeviceMetricsOverride`): la pestaña se reusa y la emulación no debe persistir.

---

## 4. Tipos de tarea y extracción de respuestas correctas

| Tipo de Tarea | Origen de Respuestas Correctas | Estado de Verificación |
| :--- | :--- | :--- |
| **`H5P.Blanks`** | `params.questions[0]` (cadena de texto). Las soluciones están delimitadas por asteriscos: `*solución*`. En JS: `(t.match(/\*[^*]+\*/g) \|\| []).map(s => s.slice(1, -1))`. | **VERIFICADO EN VIVO** (Curso 16564) |
| **`H5P.SingleChoiceSet`** | `choices[i].options.answers[k].correct === true`. En el DOM actual: clase `.h5p-sc-alternative.h5p-sc-is-correct`. | **VERIFICADO EN VIVO** (Curso 16564) |
| **`H5P.MultiChoice`** | `params.answers[i].correct === true`. Seleccionar contenedores `.h5p-answer[data-id="i"] .h5p-alternative-container`. | *PENDIENTE DE VERIFICAR* (implementado en código) |
| **`H5P.TrueFalse`** | `params.correct` (booleano / string `"true"` o `"false"`). Buscar `.h5p-true-false-answer[data-value="..."]`. | *PENDIENTE DE VERIFICAR* (implementado en código) |
| **`H5P.DragQuestion`** | Elementos en `draggables[i]` y objetivos en `correctDZs[i]`. Llamada directa `el.addToDropZone(0, el, target)`. | *PENDIENTE DE VERIFICAR* (implementado en código) |
| **`H5P.MarkTheWords`** | Palabras encerradas entre asteriscos en `params.text`. Mapeadas a spans clicables. | *PENDIENTE DE VERIFICAR* (implementado en código) |

---

## 5. Finalización y verificación de red

Para asentar la calificación en Moodle no basta con responder en pantalla; se deben disparar los eventos de cierre y registrar la llamada de red:

```javascript
// Disparo de finalización interna y eventos xAPI
(() => {
  const H = window[0].H5P;
  const I = H.instances[0];
  const s = I.getScore ? I.getScore() : 0, m = I.getMaxScore ? I.getMaxScore() : 0;
  const res = {contentId: I.contentId, score: s, max: m};
  try { H.setFinished(I.contentId, s, m); res.setFinished = 'ok'; } catch (e) { res.setFinished = 'ERR:' + e.message; }
  try {
    if (I.triggerXAPIScored) { I.triggerXAPIScored(s, m, 'completed', true, 1); res.xapi = 'ok'; }
  } catch (e) { res.xapi = 'ERR:' + e.message; }
  return JSON.stringify(res);
})();
```

### Verificación en `PerformanceResourceTiming`
Se valida que el navegador haya despachado la petición AJAX al backend de Moodle inspeccionando las entradas de red cargadas:

```javascript
(() => {
  const hits = performance.getEntriesByType('resource')
    .filter(r => /ajax\.php[^ ]*xapiresult/.test(r.name)).length;
  return JSON.stringify({hits});
})();
```

Un valor de `hits > 0` confirma que el paquete xAPI fue transmitido al servidor. Adicionalmente, se ejecuta el toggle de finalización manual en la vista general del curso (`toggle-manual-completion`) para asegurar el check verde en Moodle.

---

## 6. Idempotencia y ledger

### ¿Por qué existe?
Al recargar una actividad H5P, Moodle instancia un componente nuevo con puntaje inicial en 0. Si el script intentara deducir el estado leyendo `I.getScore()` al entrar, asumiría erróneamente que la actividad nunca se resolvió.

### Implementación
El estado se preserva en disco en `_cache/h5p_ledger_<course_id>.json`:
1. Antes de procesar una actividad, se verifica si en el ledger figura con `ok: true` y en la interfaz de Moodle ya figura marcada como completada (`data-toggletype="manual:undo"`).
2. Si ambas condiciones se cumplen, la actividad se salta inmediatamente sin abrirla ni ejecutar clics.
3. Se guarda checkpoint en disco tras resolver **cada actividad individual**, evitando pérdida de progreso en caso de interrupción del proceso.

---

## 7. Ritual de mejora continua

Tras cada ejecución, el script registra métricas y discrepancias en `references/h5p-lessons.jsonl` (duración, llamadas al navegador, clics, tareas saltadas y lista de oportunidades encontradas).

### Flujo de optimización
1. **Ejecutar el reporte**:
   ```bash
   python3 h5p_solve.py --course-id <id> --dest <ruta_curso> --report
   ```
2. **Analizar la oportunidad más frecuente**: Identificar patrones como `scs_sin_avance`, `blanks_input_mismatch` o `tipo_no_soportado:<tipo>`.
3. **Automatizar en el código base**: Incorporar la solución o selector en `h5p_solve.py`. **Nunca resolver manualmente en el navegador incidencias repetitivas**.

---

## 8. Errores ya pagados

| Síntoma | Causa Raíz | Fix Implementado | Evidencia / Impacto |
| :--- | :--- | :--- | :--- |
| **Degradación de puntaje** (100% → 0–75%) en 6 contenidos simultáneos. | Verificación de readiness laxa (`has inputs visible`); interactuó con inputs del slide anterior durante la animación. | Scopear selectores estrictamente a `.h5p-slide[si]` y verificar `inputs.length === vals.length` antes de escribir. | Sesión 2026-09-14, curso 16564. Error crítico corregido. |
| **Bucle infinito de 30 pasos sin avance** en `SingleChoiceSet`. | Usar `S.choices[cur].answered` como condición de polling. Cambia a `true` de inmediato pero el índice tarda ~2 s en avanzar. | Condición de avance atada estrictamente a `S.currentIndex > __CUR__`. | Sesión 2026-09-14. 0 bucles tras el ajuste. |
| **Inputs vacíos o no encontrados** (`querySelectorAll` devolviendo 0). | Las tareas H5P se montan de forma perezosa; no existen en el DOM hasta que el slide es el actual. | Usar `CP.jumpToSlide(si)` y aguardar visibilidad con `getClientRects().length > 0`. | Verificado en CoursePresentation con diapositivas múltiples. |
| **Re-ejecución redundante** de actividades ya aprobadas. | Pérdida de estado visual en DOM tras recargar página (el puntaje inicial de CP siempre es 0). | Implementación de `h5p_ledger_<course>.json` y lectura de manual-completion en Moodle. | Sesión 2026-09-14: saltos idempotentes automáticos sin llamadas al DOM. |
| **Pérdida de progreso en SCS** tras refrescar navegador. | Intentar recuperarse de un error recargando la página (`reload`). SCS no persiste respuestas intermedias. | Eliminar recargas en caliente durante la resolución; aplicar timeouts de stall y reintentar clics locales. | Sesión 2026-09-14. Evitó reinicios a 0 puntos. |
| **`h5p_no_cargo` engañoso**: el solver reportaba que el H5P no cargó, pero el contenido estaba intacto. | Las superficies de navegador abiertas como TABS del mismo pane (`placement: reuse`) comparten un único slot visible. La que pierde el foco queda `visibilityState: hidden` y su `goto` se suspende a mitad de carga (`readyState: loading`, `body` vacío). | (a) Un pane por superficie, no N tabs en el mismo pane; (b) preflight que distingue `surface_throttled_segundo_plano` de `h5p_no_cargo` en vez de culpar al contenido. Ojo: para fan-out conviene directamente Chrome/CDP, que carga todas las pestañas sin foco. | Sesión 2026-09-14: reproducido en vivo (`hidden:true`, `readyState:loading`). |
| **Actividad "completa" con el deck a medias** (5/13) y el chequeo final sin pulsar. | Se asumía que resolver el quiz terminaba la actividad. Además se contaba el deck con `CP.children.length` (12) en vez de `CP.slides.length` (13), que incluye el slide de resumen donde vive el botón. | Recorrer hasta el último slide, pulsar el chequeo final (`.h5p-show-solutions`) y exigir `deck_completo` para dar `ok`. | Sesión 2026-09-14. Señalado por Andrés con captura: "no estás llegando al último botón, que es el que hace el chequeo final". |
| **Slides impares nunca alcanzados**; `blanks_input_mismatch` con `nInputs: 0`. | `CP.jumpToSlide(i)` se ignora silenciosamente si se pide durante la transición anterior. El índice quedaba en el par previo y la tarea no estaba en el DOM. | Re-emitir el salto hasta confirmar el cambio de índice (`goto_slide`), en vez de solo esperar. | Sesión 2026-09-14: `slide 1, 3, 5 → espera agotada (None)`; el estado real seguía en el slide anterior. |
| **`nInputs: 3 / esperados: 2`** y actividad en 3/5 pese a que el índice decía slide 6. | `CP.getCurrentSlideIndex()` se actualiza antes que la clase `.h5p-current`. El selector scoped leyó los inputs del slide anterior. | Confirmar índice **y** clase DOM (`.h5p-slide` con `.h5p-current` cuyo `indexOf === si`) antes de operar por selector. | Sesión 2026-09-14, 774610. La invariante abortó y el oráculo del resumen lo detectó (`todas_al_100: false`) en vez de darlo por bueno. |
| **12 contenidos interactivos, 6 sin resolver** que "no existían" en la página del curso. | Se descubría enumerando `li.activity.modtype_hvp` de `course/view.php`, que omite contenidos H5P (p. ej. los "Parte 2"). | Descubrir desde `grade/report/user` (la fuente autoritativa, escala 0–10) y usarla también para verificar al final. | Sesión 2026-09-14: el informe mostró 12 donde la página del curso mostraba 6. |
| **Palabras de la sopa de letras que "no se encuentran"** (7/9, 8/9). | Tres causas distintas y acumulativas: (a) `getBoundingClientRect()` del iframe es relativo al iframe y CDP usa el viewport superior; (b) solo se comprobaba el alto del viewport, no el ancho; (c) el rect del canvas se leía una sola vez y se desplaza al marcarse palabras. | Sumar el offset del iframe, validar `innerH` **y** `innerW`, y releer la geometría antes de cada palabra. | Sesión 2026-09-14, 774617 (7/9) y 746510 (8/9) → 9/9 tras los tres fixes. |
| **20+ pestañas huérfanas de Chrome.** | `ChromeBrowser.close()` cerraba el WebSocket y no la pestaña; además se creaba una por operación. | `close()` cierra la pestaña propia, `--tab-policy reuse` adopta una existente y deja una sola viva, `--cleanup-tabs` limpia lo anterior (solo URLs del Aula Virtual). | Sesión 2026-09-14. Estado medido: `0` tras cleanup, `1` con política `reuse`. |

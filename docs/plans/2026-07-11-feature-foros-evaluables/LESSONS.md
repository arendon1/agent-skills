# LESSONS: Foros evaluables

## Lecciones durante el build

### L1: SKILL.md ya violaba el límite de 500 líneas

- **Síntoma:** al agregar la nueva sección de `foros`, SKILL.md pasó
  de 560 → 618 líneas (límite MUST: 500).
- **Causa:** la versión previa del SKILL.md ya estaba en 560 líneas,
  violando la constitución (§15: SKILL.md MUST stay under 500 lines).
- **Mitigación:** moví el detalle de implementación de la nueva feature
  a `references/foros-evaluables.md` y dejé en SKILL.md solo lo
  esencial (uso, qué extrae, dónde está el detalle). 618 → 593.
- **Pendiente:** abrir un refactor que mueva MÁS contenido del SKILL.md
  actual a `references/` (la sección de "Fuente de Verdad de Fechas"
  tiene 50+ líneas que podrían vivir en su propio reference). Esto
  debería ser un plan aparte, no acoplado a esta feature.

### L2: Los foros intro y los foros de actividad son bestias distintas

- **Aprendizaje:** `extractor_foro.py` (intro: Avisos, Consultas,
  Presentación) filtra solo discusiones del profesor — eso es correcto
  para intro donde el profe es el autor de los avisos. NO es correcto
  para foros de actividad donde los compañeros son los autores.
- **Decisión:** NO refactorizar `extractor_foro.py` — crear
  `extractor_foro_evaluable.py` paralelo, dejando el viejo intacto.
  El `cli_init.py` decide cuál usar según `es_evaluable(titulo)`.
- **Beneficio:** cero riesgo de romper el flujo existente de
  intro/Avisos que ya está en producción.

### L3: Cache por `discuss_id` es el identificador canónico

- **Aprendizaje:** la URL completa del hilo es
  `/mod/forum/discuss.php?d=<N>`. El `<N>` es estable (Moodle no lo
  recicla). Usar el ID como key de cache garantiza idempotencia:
  re-ejecuciones no re-abren hilos ya procesados.
- **Verificación:** el smoke test con `tempfile` confirmó que el cache
  hit evita la navegación.

### L4: Selectores de Moodle pueden cambiar entre versiones

- **Riesgo:** el parser de `vencimiento`, `indicaciones`, y `actividad`
  depende de la estructura HTML actual de Moodle (basado en la
  captura del usuario). Si Uniremington actualiza Moodle, estos
  selectores pueden romperse.
- **Mitigación aplicada:** cada extractor tiene fallbacks (ej: la
  extracción de `vencimiento` busca en `div[data-region='activity-dates']`
  y devuelve "" si no encuentra; `indicaciones` y `actividad` buscan
  en el texto y devuelven "[Sin indicaciones]" / "[Sin actividad]").
- **Mitigación futura:** si los selectores fallan en un curso real,
  añadir logs de debug con el HTML descargado para iterar. Por
  ahora, los fallbacks garantizan que el flujo no crashea.

### L5: El cap de 20 hilos es por foro, no por curso

- **Decisión:** el usuario dijo "máximo 20 hilos por foro" (cap por
  foro). Si hay 5 foros con 20 hilos cada uno = 100 navegaciones
  en el peor caso. Aceptable para uso real.
- **Configurable:** `MAX_HILOS = 20` en `extractor_foro_evaluable.py`
  para ajuste futuro.

### L6: El `__pycache__` en el repo de docs es ruido

- Observación menor: hay `.pyc` files en el repo del skill (carpeta
  `__pycache__`). Debería estar en `.gitignore`. No es bloqueante
  pero es limpieza pendiente.

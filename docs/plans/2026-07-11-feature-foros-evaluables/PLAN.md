# PLAN: Foros evaluables → hilos principales de compañeros

## Tasks

| ID | Task | Status | Test |
|----|------|--------|------|
| F1 | `extraer_datos_foro(url)` lee página del foro: title, vencimiento, indicaciones, actividad, lista de hilos | [ ] | unit + manual contra curso real |
| F2 | `extraer_discusiones_foro` sin filtro de profesor, cap 20, devuelve id+metadata | [ ] | unit |
| F3 | `extraer_primer_post_cached(discuss_id, url, cache_path)` con cache por `discuss_id` | [ ] | unit + manual: 2da run no re-abre |
| F4 | `cli_foros.py`: nuevo CLI que itera sidebar → detecta foros evaluables → extrae → guarda en `Unidad-X/Foros/` | [ ] | manual: ejecutar contra curso real |
| F5 | Hook en `cli_init.py` para correr flujo de foros durante init de unidades | [ ] | manual: re-init un curso |
| F6 | Hook en `cli_estado.py` para detectar hilos nuevos en sync | [ ] | manual: añadir hilo en Moodle + sync |
| F7 | `scaffold_curso.py` crea `Unidad-X/Foros/` si no existe | [ ] | manual: init curso nuevo |
| F8 | `SKILL.md` documenta el nuevo comando y output | [ ] | visual |
| F9 | Propagar cambios a `~/.agents/skills/gestionar-cursos/` (instalado) | [ ] | diff |
| F10 | Commit + commit message conventional | [ ] | git log |

## Implementation Notes

### F1: extraer_datos_foro

Input: `url_foro: str`
Output: `dict` con:
```python
{
  "titulo": str,                    # ej: "Foro 1: Seguridad en aplicaciones web (6%)"
  "vencimiento": str,               # ISO 8601 o ""
  "indicaciones": str,              # markdown del bloque de instrucciones
  "actividad": str,                 # markdown del bloque "Pregunta orientadora"
  "es_evaluable": bool,             # True si "(X%)" en title y X>0
  "porcentaje": int,                # ej: 6
  "url": str,
  "hilos": [                        # máx 20
    {
      "discuss_id": str,            # ej: "140651"
      "titulo": str,
      "autor": str,
      "fecha": str,                 # ISO 8601
      "ultimo_mensaje_autor": str,
      "ultimo_mensaje_fecha": str,
      "replicas": int,
      "url": str,                   # discuss.php?d=140651
    }
  ]
}
```

Selector strategy (basado en screenshot de Moodle moderno):
- Título: `h1` o `.page-header-headings h1`
- Vencimiento: `div[data-region='activity-dates'] strong:contains('Vencimiento')` →
  padre `.get_text` con regex para fecha
- Indicaciones: bloque bajo "Para participar siga las instrucciones..."
  → buscar contenedor padre del `<strong>` o párrafo que contiene
  "Para participar siga las instrucciones"
- Actividad: bloque "Pregunta orientadora:" → mismo patrón
- Hilos: tabla `[data-region="discussion-list"]` o `table.forumheaderlist`
  - Cada fila: `a[href*="discuss.php"]` (título), columnas siguientes
    (autor+fecha, último mensaje+fecha, réplicas)

### F2: extraer_discusiones_foro refactor

- Quitar parámetro `nombre_profesor` (ya no se filtra por autor)
- Añadir cap de 20
- Devolver lista de `dict` con `discuss_id` (extraído de URL con regex
  `discuss\.php\?d=(\d+)`)

### F3: extrae primer post cached

```python
def extraer_primer_post_cached(discuss_id: str, url: str, cache: dict) -> str:
    if discuss_id in cache and "contenido" in cache[discuss_id]:
        return cache[discuss_id]["contenido"]
    contenido = _extraer_primer_post(url)
    if contenido is not None:
        cache[discuss_id] = {
            "contenido": contenido,
            "extraido_en": datetime.now().isoformat(),
        }
    return contenido
```

Cache: `_cache/foros_cache.json` por curso (mismo dir que `snapshot.json`).

### F4: cli_foros.py

Flujo:
1. Cargar AGENTS.md → URL del curso
2. Extraer sidebar (reusar `extraer_sidebar()`)
3. Filtrar solo `tipo == "forum"`
4. Para cada foro:
   a. Si sección no matchea `Unidad \d+` → skip (es intro/avisos)
   b. Llamar `extraer_datos_foro(url)`
   c. Si `es_evaluable == False` → skip
   d. Cargar cache `_cache/foros_cache.json`
   e. Para cada hilo (cap 20): `extraer_primer_post_cached`
   f. Guardar cache
   g. Renderizar markdown → `Unidad-X/Foros/<forum-slug>.md`

### F5-F6: hooks

En `cli_init.py` línea 292 (`elif tipo == "forum":`), reemplazar
llamada a `extraer_discusiones_foro` por llamada al nuevo flujo de
foros evaluables. Mantener el flujo intro intacto en
`_extraer_y_guardar_foros`.

En `cli_estado.py`, después de extraer sidebar, identificar foros
evaluables y comparar hilos cacheados vs actuales → reportar nuevos.

### F7: scaffold_curso.py

En `crear_estructura_curso`, después de crear `Unidad-X/`, crear
`Unidad-X/Foros/` también (vacío, los archivos se llenan después).

### Output markdown template

```markdown
# Foro 1: Seguridad en aplicaciones web (6%)

- **URL:** https://aulavirtual.uniremington.edu.co/mod/forum/view.php?id=350767
- **Vencimiento:** 2026-07-19 23:59
- **Unidad:** Unidad 1
- **Hilos extraídos:** 5 (de 5 visibles)
- **Última actualización:** 2026-07-11

## Indicaciones

- Lea con atención las preguntas orientadoras.
- Evite copiar y pegar contenido generado por IA.
[...]

## Actividad a realizar

**Pregunta orientadora:**

1. ¿Cuál consideras...
2. ¿Qué rol juega...

## Hilos principales de compañeros

### 1. Amenazas de Seguridad (ID: 140651)

- **Iniciado por:** Juan Fernando Q... — 2026-07-07
- **Última respuesta:** Laura Vanesa Mo... — 2026-07-11
- **Réplicas:** 3
- **URL:** https://aulavirtual.uniremington.edu.co/mod/forum/discuss.php?d=140651

#### Primer post

[contenido completo, sin truncar]

---

### 2. Foro 1: Seguridad en aplicaciones web (ID: 140652)
[...]
```

## Test Strategy

- **Manual E2E:** ejecutar contra un curso real de Uniremington que
  tenga al menos 1 foro evaluable con hilos de compañeros. Verificar:
  - Archivo se genera en `Unidad-X/Foros/`
  - Metadata correcta (título, %, vencimiento)
  - Hilos listados con autor, fecha, réplicas
  - Contenido del primer post completo
  - 2da ejecución: no re-abre hilos cacheados
  - Foro sin % se omite
- **Sintaxis:** `python -c "import cli_foros"` + dry-run
- **Skill-forge audit:** validar que el SKILL.md sigue la constitución

## Risks

- **R1:** El HTML de Moodle cambia entre cursos/versiones. Mitigación:
  selectores múltiples con fallbacks (ver patrón en `extractor_modulos.py`).
- **R2:** Carga lenta con muchos hilos. Mitigación: cap 20 + cache.
- **R3:** Curso sin secciones "Unidad X" (nombres custom). Mitigación:
  si el section no matchea el patrón, log warning y skip (no crashear).

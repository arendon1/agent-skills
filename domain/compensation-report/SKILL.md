---
name: compensation-report
description: >
  Entrevista al usuario para recolectar los datos del cargo objetivo (cargo(s),
  años de experiencia, ubicación/modalidad, empresa objetivo y stack
  tecnológico), investiga bandas salariales en vivo en múltiples fuentes,
  triangula los datos y genera un reporte de compensación en markdown con
  valores en COP y USD, anuales y mensuales, perfil financiero del empleador,
  estructura de compensación esperada, BATNA implícito y tres tácticas
  defensivas de negociación. Usa cuando el usuario pida un reporte de
  compensación, un análisis salarial para una negociación, bandas salariales
  para un cargo en una ubicación específica, o quiera preparar una
  conversación salarial con un empleador actual o potencial.
invocation: user
layer: domain
loop: compensation-report
provides: [salary-research, employer-profiling, negotiation-scripting, market-band-triangulation]
deliverable: reporte de compensación en markdown (COP + USD, anual + mensual) con perfil del empleador, bandas por percentil, publicaciones activas, estructura de compensación, BATNA y tácticas de negociación
language: es-CO
metadata:
  version: "1.0.0"
  author: agent-skills
  risk_tier: LOW
---

# compensation-report

Skill de loop con entrega única: parte de una necesidad declarada por el
usuario (preparar una negociación, comparar una oferta, entender el mercado)
y produce un reporte de compensación accionable. El reporte siempre incluye
las cuatro representaciones de cada valor monetario (USD/año, USD/mes, COP/año,
COP/mes) porque el usuario lee en pesos colombianos pero negocia (o
contrasta) con cifras en dólares.

## Principios

1. **Las cuatro formas siempre.** Cada cifra salarial aparece en USD/año,
   USD/mes, COP/año y COP/mes. Si una tabla omite una, el reporte no pasa la
   verificación final. Esto se hace por hábito, no por configuración.
2. **Triangulación explícita.** Ningún percentil se reporta con menos de
   tres fuentes independientes. Si solo hay una fuente, se marca como
   "estimación de fuente única" y se reduce la confianza.
3. **Empresa o mercado, no los dos a la fuerza.** Si el usuario nombra
   empleador, el reporte abre con perfil financiero de esa empresa. Si dice
   "mercado general", se analiza el segmento (startup tech LATAM, consultora
   regional, corporativo US, etc.) con cifras representativas.
4. **Stack como palanca, no como descarte.** Las skills específicas del
   usuario (ej. Tableau, dbt, Snowflake) se usan para anclar contra
   publicaciones activas, no para excluir al candidato de un rango.
5. **Advertencias siempre al final.** Varianzas grandes en los datos,
   riesgos cambiarios, recortes activos, BATNA: todos van numerados en la
   sección de advertencias. Negocia con datos, no con presión.
6. **Agnóstico del harness.** El cuerpo describe comportamiento
   ("investigar", "triangular", "escribir archivo"); la herramienta concreta
   la resuelve el adaptador.

## Cuando usar este skill

- El usuario está por entrar a una negociación salarial y quiere argumentos.
- El usuario recibió una oferta y necesita evaluarla contra el mercado.
- El usuario quiere saber "¿cuánto debería ganar?" para uno o varios cargos
  objetivo en una ubicación específica.
- El usuario pide explícitamente "reporte de compensación", "análisis
  salarial", "bandas salariales" o variantes en español o inglés.
- El usuario tiene un stack claro (ej. "Tableau + SQL + Snowflake") y quiere
  saber cuánto vale en el mercado LATAM remoto.

## Cuando NO usar este skill

- El usuario quiere negociar pero no tiene contexto de cargo/empresa — pedir
  contexto antes de proceder.
- El usuario quiere revisar su propio salario actual sin objetivo nuevo —
  derivar a un análisis ad-hoc, no a este loop.
- El usuario pide datos de un cargo en una industria sin mercado público
  transparente (ej. ONG pequeña, gobierno regional) — advertir limitación y
  proceder solo con lo público.

## Flujo de trabajo

### 1. Entrevista (obligatoria, una sola pregunta)

Recolectar los datos del usuario antes de investigar. Usar la herramienta
declarativa de preguntas (clarify) para pedir TODO en una sola llamada, no
preguntar uno por uno. Si el usuario ya mencionó algunos datos en su
mensaje inicial, no volver a preguntarlos.

**Datos requeridos (bloquean el flujo si faltan):**

1. **Cargo(s) objetivo** — uno o varios. Ejemplos: "BI Analyst, BI Engineer,
   Data Engineer" o "Analytics Director".
2. **Años de experiencia** — número entero o rango (ej. "5", "6-8").
3. **Ubicación / modalidad** — ciudad, país y si es remoto, híbrido u
   on-site. Ejemplos: "Colombia/Remoto", "Bogotá/Híbrido", "México/Remoto".
4. **Empresa objetivo** — nombre del empleador potencial o actual. Si no
   aplica, escribir literalmente "mercado general" o "sin empresa
   específica".

**Datos opcionales (mejoran el reporte, no lo bloquean):**

5. **Stack o skills destacadas** — herramientas o dominios que el
   usuario quiere usar como palanca. Ejemplos: "Tableau, SQL, Snowflake",
   "dbt, Airflow, BigQuery".
6. **Salario actual** — para calcular delta vs. bandas. Si no se quiere
   compartir, omitir; el reporte no lo exigirá.
7. **Tipo de contratación** — empleado directo, contratista independiente,
   EOR, freelance. Default si se omite: empleado directo.
8. **Moneda de pago preferida** — COP, USD, o ambas. Default: ambas.
9. **Ciudades específicas** — para refinar la búsqueda a nivel local.
   Default si se omite: país completo.
10. **Nivel del cargo objetivo** — Junior (0-2 años), Mid (3-5), Senior
    (6-9), Staff/Lead (10+). Default si se omite: inferir por años de
    experiencia del usuario.
11. **Sector del empleador** — fintech, retail, salud, etc. Si es
    relevante, ayuda a calibrar la prima o descuento.
12. **Beneficios actuales que no quiere perder** — lista de beneficios
    existentes. Sirve para anclar la sección de estructura de compensación.

**Valores por defecto (si el usuario no responde los opcionales):**
- Sin stack → no filtrar por tecnología.
- Sin salario actual → no calcular delta.
- Sin tipo de contratación → asumir empleado directo.
- Sin moneda → reportar en COP y USD.
- Sin ciudades → buscar a nivel país.
- Sin nivel → inferir de años (0-2 Jr, 3-5 Mid, 6-9 Senior, 10+ Staff/Lead).
- Sin sector → usar mercado general.
- Sin beneficios actuales → listar los típicos del mercado objetivo.

### 2. Investigación de mercado (en paralelo)

Ejecutar todas las búsquedas en un solo turno (batch) para minimizar
latencia. Cuatro hilos de investigación:

**Hilo A — Bandas salariales del cargo en la ubicación especificada.**
Fuentes prioritarias (en orden):
- Glassdoor (filtrar por empresa y ciudad)
- Levels.fyi (filtrar por empresa y seniority)
- PayScale (filtro país y años de experiencia)
- SalaryExpert (ciudad específica)
- HireTalent.lat (datos remote-for-US en LATAM, marzo del año en curso)
- Indeed (publicaciones con salarios publicados)
- Get on Board (publicaciones LATAM)
- Howdy (payroll dataset LATAM con all-in)

Extraer con `web_extract` cuando el snippet no basta. Por cada cargo,
capturar P25, P50 y P75 en USD/año siempre que la fuente lo publique;
si no, registrar el rango o la mediana y marcarlos como tales.

**Hilo B — Publicaciones de empleo activas que coincidan con el cargo +
stack + ubicación.** Buscar el mismo día de generación. Priorizar
publicaciones que mencionen el stack del usuario (ej. "Tableau Developer
remoto Colombia"). Extraer: empresa, cargo, rango publicado (si está
visible), modalidad, fecha de publicación. Marcar como "publicación
reciente" solo las de los últimos 90 días.

**Hilo C — Perfil financiero del empleador (solo si se nombró una
empresa en el paso 1).** Fuentes:
- Investor relations de la empresa (si cotiza en bolsa)
- Macrotrends, Yahoo Finance, CompaniesMarketCap
- Noticias recientes sobre recortes, contrataciones, layoffs, class
  actions
- Glassdoor/Comparably para tamaño aproximado y reviews de compensación

Capturar: ingresos anuales, guía de crecimiento, margen bruto, free cash
flow, market cap, empleados totales, eventos recientes que afecten
contratación.

**Hilo D — Datos macro del día.** TRM actual COP/USD, IPC Colombia del
último mes, salario mínimo legal vigente. Si la TRM no se puede extraer
de una fuente oficial, usar el cierre del día anterior como aproximación y
registrar la fuente y la fecha.

**Reglas duras de investigación:**
- Mínimo 3 fuentes independientes por cada percentil salarial publicado.
- Si solo hay 1 fuente, marcar como "estimación de fuente única" y reducir
  la confianza.
- No inventar datos. Si una búsqueda no devuelve nada útil, escribir
  "no disponible" en el reporte, no rellenar.
- Si la fuente tiene más de 12 meses, marcarla como "dato del año
  anterior" y considerar complementar con publicación más reciente.

### 3. Cálculo de bandas

Para cada cargo objetivo, calcular tres percentiles:

- **P25** — piso del rango, útil como "límite inferior aceptable".
- **P50** — mediana del mercado, ancla neutral.
- **P75+** — techo del rango senior, objetivo para alto desempeño.

Para cada percentil, calcular las cuatro formas:
- USD/año (de la fuente, sin convertir)
- USD/mes (USD/año ÷ 12)
- COP/año (USD/año × TRM)
- COP/mes (USD/año × TRM ÷ 12)

Usar la TRM capturada en el hilo D. Redondear COP a millón o decena de
millón más cercano; USD a centena más cercana. Anotar la TRM y la fecha
al inicio del reporte.

Si dos fuentes tienen P50 con diferencia mayor al 25%, no promediar —
reportar ambos y advertir alta dispersión.

### 4. Generación del reporte

Escribir el reporte como archivo markdown. Por tamaño esperado
(> 200 líneas), usar `write_file` para la primera sección (encabezado +
perfil financiero + inicio de bandas) y luego `patch` en bloques de menos
de 8K tokens para anexar el resto.

**Ruta de guardado:** `compensation-report-<cargo-principal>-<YYYY-MM-DD>.md`
en el directorio de trabajo del usuario. Si el usuario no está en un
directorio de proyecto, guardar en el home con timestamp para evitar
colisiones.

**Estructura obligatoria** (siete secciones, en este orden):

#### §1 Perfil Financiero del Empleador
- Tabla con: ingresos anuales, guía de crecimiento, margen bruto, market
  cap, empleados totales.
- 2-4 viñetas de análisis de capacidad de pago y agresividad en mercado
  de talento.
- Si no se nombró empleador, analizar el segmento (ej. "consultoras
  tech LATAM", "startups US con remote-first").

#### §2 Bandas Salariales Estimadas
- Una subsección por cada cargo objetivo (3.1, 3.2, …).
- Tabla por cargo con columnas: Percentil | USD/año | COP/año | USD/mes
  | COP/mes | Fuente principal.
- Subsección final "Resumen comparativo (P50)" con tabla de todos los
  cargos en las cuatro formas.
- Citar fuente por cada fila de cada tabla.

#### §3 Publicaciones Activas Relevantes
- Tabla: Empresa | Cargo | Rango publicado | USD/mes (si está
  publicado) | COP/mes (si está publicado) | Modalidad | Notas.
- 1-2 viñetas de lectura del mercado activo.
- Priorizar publicaciones que mencionen el stack del usuario.

#### §4 Estructura de Compensación
- 4.1: Desglose del empleador específico (si aplica) con
  salario base %, bonos %, equity %, beneficios. Tabla con: Componente
  | % del Total | USD/año | USD/mes | COP/año | COP/mes | Notas.
- 4.2: Comparación por tipo de empleador (consultora LATAM, startup US,
  mid-size US SaaS, gran corporación) con las mismas columnas.
- 4.3: BATNA implícito del candidato con cifras concretas.

#### §5 Estrategia Defensiva: Tácticas de Negociación
- Exactamente 3 tácticas.
- Cada una con tres bloques:
  - "Cuándo lo dicen": cita literal o paráfrasis del reclutador.
  - "Respuesta": script sugerido (2-4 oraciones, listo para usar).
  - "Por qué funciona": razonamiento táctico (1-2 oraciones).
- Adaptar las tácticas al empleador específico y al stack del candidato.

#### §6 Advertencias
- 3-5 advertencias numeradas, específicas al contexto (recortes activos,
  varianza de datos, riesgo cambiario, BATNA, cláusulas de ajuste).
- Sin hedging genérico; cada advertencia es accionable.

#### §7 Fuentes Consultadas
- Tabla: Fuente | URL | Datos extraídos.
- Footer con fecha de generación y disclaimer sobre que los datos
  reflejan información pública disponible a esa fecha.

### 5. Verificación final (antes de entregar)

Checklist de auditoría (no entregar hasta que todas pasen):

- [ ] ¿Todas las tablas salariales tienen las cuatro columnas (USD/año,
  USD/mes, COP/año, COP/mes)?
- [ ] ¿Hay al menos 3 fuentes citadas por cargo en §2?
- [ ] ¿El perfil financiero del empleador (si aplica) tiene datos del
  año en curso?
- [ ] ¿Las 3 tácticas de negociación son específicas al empleador y al
  stack del candidato, no genéricas?
- [ ] ¿La TRM está registrada con fecha en la cabecera?
- [ ] ¿Las publicaciones activas en §3 son de los últimos 90 días?
- [ ] ¿Las advertencias en §6 son accionables, no hedging?
- [ ] ¿El reporte no contiene nombres de harness, herramientas, ni
  sintaxis de slash-commands en el cuerpo?

Si alguna verificación falla, corregir antes de mostrar el reporte al
usuario.

## Anti-patrones

- **No anclar con un solo número.** El reporte siempre trabaja con
  rangos, no con cifras puntuales, salvo que se trate de un dato
  contractual real (ej. salario actual del usuario).
- **No usar "depende" como respuesta.** Si la varianza es alta,
  reportar el rango completo y la fuente de cada extremo, no
  escudarse en vaguedad.
- **No inflar con fuentes secundarias.** Glassdoor sin suficientes
  reportes no vale lo mismo que Levels.fyi. Anotar la calidad de la
  fuente, no solo la cantidad.
- **No omitir la TRM.** El reporte es para un usuario colombiano;
  necesita poder convertir a pesos mentalmente.
- **No usar BATNA como amenaza.** La sección de BATNA describe la
  alternativa real, no una posición de fuerza. La negociación efectiva
  viene de los datos, no de los ultimátums.

## Salida esperada

Un archivo markdown con el nombre `compensation-report-<cargo>-<fecha>.md`,
siete secciones, todas las cifras en las cuatro formas, y al menos 10
fuentes citadas entre §2, §3, §7. El usuario puede leerlo en 10-15 minutos
y usarlo directamente para preparar una conversación salarial.

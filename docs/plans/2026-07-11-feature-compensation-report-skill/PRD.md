# PRD: skill de reporte de compensación

**Plan:** `2026-07-11-feature-compensation-report-skill`
**Tipo:** feature
**Estado:** ✅ implementado

## Contexto

El usuario es un ingeniero BI/Analytics con 6 años de experiencia en Colombia,
remoto, especializado en Tableau. Necesita negociar salario con frecuencia
(evaluaciones anuales, ofertas externas) y no tenía un flujo reproducible
para producir análisis de mercado accionables. La conversación manual
(pedirle datos, hacer búsquedas, generar tablas) tomaba 3-4 turnos y los
reportes se perdían en el chat.

## Problema

1. Recolectar los datos necesarios para un análisis de compensación
   requería 2-3 turnos de preguntas.
2. La investigación de bandas salariales en LATAM (COP + USD, multi-rol,
   multi-stack) no estaba estandarizada — dependía de la memoria del
   agente.
3. El reporte final variaba en forma: a veces en columnas, a veces en
   prosa, a veces solo USD sin conversión a COP.
4. No había separación entre "reporte generado" y "reporte reutilizable"
   — cada negociación empezaba de cero.

## Usuarios

- **Primario:** el propio usuario, negociando salario con su empleador
  actual o evaluando ofertas externas.
- **Secundario:** otros profesionales LATAM en roles técnicos similares
  que adopten el skill vía el repo `agent-skills-v2`.

## Goals

1. Reducir el ciclo "necesito un análisis de compensación" a 2 turnos:
   uno para entrevista, otro para el reporte listo.
2. Estandarizar el reporte: siempre 7 secciones, siempre las 4 formas
   de cada cifra (USD/año, USD/mes, COP/año, COP/mes), siempre 3+
   fuentes por percentil.
3. Que el reporte sea reutilizable como artefacto: archivo markdown
   versionable, no chat efímero.
4. Que el skill sea agnóstico del harness (corre en cualquier
   adaptador de Layer 4 que pueda leer SKILL.md y correr Bash).

## Non-goals

- No intenta predecir ofertas individuales — solo refleja el mercado
  público disponible.
- No scrapea sitios no públicos (Glassdoor autenticado, niveles
  privados, etc.).
- No produce recomendaciones legales ni fiscales.
- No automatiza el envío de la oferta al empleador — el reporte
  termina en el usuario, no en el reclutador.

## Criterios de éxito

- El usuario puede invocar el skill, responder la entrevista, y recibir
  un reporte markdown en menos de 5 minutos.
- El reporte siempre tiene las 4 columnas monetarias por tabla
  salarial.
- El reporte cita al menos 10 fuentes externas.
- El skill pasa `skill-forge audit` sin advertencias críticas.
- El skill es agnóstico: no menciona `pi`, `Claude Code`, `OpenCode`,
  ni sintaxis de slash-commands en el cuerpo.

## Riesgos

- **Datos desactualizados:** las bandas salariales cambian trimestre a
  trimestre. Mitigación: el skill exige fecha en cada fuente y
  advierte cuando son mayores a 12 meses.
- **TRM volátil:** la tasa COP/USD varía. Mitigación: el reporte
  registra la TRM usada con fecha y advierte sobre riesgo cambiario si
  el contrato es en COP.
- **Alta varianza de fuentes:** Glassdoor tiene outliers enormes.
  Mitigación: triangulación obligatoria de 3 fuentes, advertencia
  explícita si la varianza intra-percentil supera 25%.
- **Falsa precisión:** un percentil P50 no garantiza nada.
  Mitigación: el reporte es de mercado, no de oferta individual; las
  tácticas de negociación lo dejan claro.

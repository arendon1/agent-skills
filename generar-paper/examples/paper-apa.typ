// Plantilla APA 7 — Formato Estudiante (es-CO)
// Usa el paquete versatile-apa:7.2.0 con localización en español

#import "@preview/versatile-apa:7.2.0": *

#show: apa.with(
  // Formato estudiante (sin running head, incluye datos del curso)
  style: "student",

  // Datos del documento
  title: [Título del Documento Académico],
  short-title: [Título Corto],  // Opcional, para encabezados internos

  // Autor(es)
  authors: (
    (
      name: [Nombre del Autor],
      affiliation: [Universidad Widget],
      orcid: "0000-0001-2345-6789",  // Opcional
    ),
  ),

  // Datos del curso (formato estudiante)
  course: [ING-401 Proyecto de Grado],
  instructor: [Dr. Nombre del Instructor],
  due-date: [15 de junio de 2026],

  // Resumen y palabras clave
  abstract: [
    El resumen debe tener entre 150 y 250 palabras. Resume los antecedentes,
    el propósito, los métodos, los resultados principales y las conclusiones
    del trabajo. No incluye citas ni referencias a figuras o tablas. Debe ser
    comprensible por sí mismo sin necesidad de leer el documento completo.
  ],
  keywords: ("palabra clave 1", "palabra clave 2", "palabra clave 3", "palabra clave 4"),

  // Configuración regional
  lang: "es",
  region: "es",

  // Nota del autor (solo formato profesional, ignorada en estudiante)
  // author-note: [...],
)

// ============================================================================
// INTRODUCCIÓN
// ============================================================================

= Introducción

Contexto amplio del tema de investigación. Por qué es importante este problema
en el campo de estudio actual @referencia_ejemplo.

// Citar con @clave_cita
// Revisar referencias/references.bib para ver el formato esperado

== Antecedentes

Trabajos previos relevantes que establecen la base de esta investigación.

== Brecha de conocimiento

Lo que aún no se sabe o no se ha investigado suficientemente.

== Pregunta de investigación

La pregunta específica que este trabajo busca responder.

== Contribución

Por qué este trabajo aporta algo nuevo y valioso al campo.

// ============================================================================
// MÉTODO
// ============================================================================

= Método

== Participantes o muestra

Descripción de la población, criterios de inclusión/exclusión, tamaño de muestra.

== Materiales o instrumentos

Herramientas, equipos, encuestas o software utilizados.

== Procedimiento

Pasos seguidos para recolectar y procesar los datos.

== Análisis de datos

Técnicas estadísticas o cualitativas aplicadas.

== Consideraciones éticas

Aprobación institucional, consentimiento informado, privacidad de datos.

// ============================================================================
// RESULTADOS
// ============================================================================

= Resultados

Reportar los hallazgos sin interpretarlos. Usar tablas y figuras para datos
complejos. Incluir tamaños de efecto y valores p cuando corresponda.

// Ejemplo de tabla
#figure(
  table(
    columns: 3,
    [Variable], [Grupo A], [Grupo B],
    [Medida 1], [3.45], [4.12],
    [Medida 2], [2.10], [2.89],
  ),
  caption: [Resultados principales por grupo experimental]
) <tabla-resultados>

// Ejemplo de gráfico con CeTZ
// #figure(
//   cetz.canvas({
//     import cetz.plot
//     plot.plot(size: (8, 5), x-tick-step: 1, y-tick-step: 1, {
//       plot.add(((0, 0), (1, 1), (2, 4), (3, 9)), label: "Datos")
//     })
//   }),
//   caption: [Evolución de la variable dependiente]
// ) <figura-datos>

// ============================================================================
// DISCUSIÓN
// ============================================================================

= Discusión

== Resumen de hallazgos

Síntesis de los resultados principales.

== Interpretación en contexto

Cómo se relacionan los hallazgos con la literatura existente.

== Implicaciones teóricas

Qué aportan estos resultados al marco teórico del campo.

== Implicaciones prácticas

Aplicaciones concretas de los hallazgos.

== Limitaciones

Qué no pudo hacer este estudio y por qué.

== Direcciones futuras

Qué debería investigarse a continuación.

== Conclusión

Cierre del trabajo, retomando la contribución principal.

// ============================================================================
// REFERENCIAS
// ============================================================================

#bibliography(
  "references.bib",
  title: "Referencias",
  style: "apa",
)

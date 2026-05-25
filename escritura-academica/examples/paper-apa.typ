// Using Templates (Simpler)

#import "@preview/versatile-apa:0.1.0": *
#import "@preview/cetz:0.3.1"
#import "@preview/cetz-plot:0.1.0"

#show: apa.with(
  title: "Título del Documento",
  authors: (
    (name: "Autor Uno", affiliation: "Afiliación Uno"),
    (name: "Autor Dos", affiliation: "Afiliación Dos"),
  ),
  abstract: [
    Resumen del documento aquí...
  ],
  keywords: ("palabra clave 1", "palabra clave 2", "palabra clave 3"),
  lang: "es",
  region: "es", // Optional
)

// Content starts immediately
= Introducción
Texto de introducción...

= Método
...

= Resultados
// Ejemplo de grafico usando CeTZ (descomentar para usar)
// #cetz.canvas({
//    import cetz.plot
//    plot.plot(size: (5, 3), x-tick-step: 1, y-tick-step: 1, {
//      plot.add(((0, 0), (1, 1), (2, 4), (3, 9)), label: "Datos")
//    })
// })
...

= Discusión
...

#bibliography("refs.bib")

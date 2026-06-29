# Carga de Datos

Cargar archivos de datos externos para generar contenido dinámico.

## Formatos Soportados

### CSV
```typst
#let dataset = csv("data.csv")
#table(
    columns: dataset.first().len(),
    ..dataset.flatten()
)
```

### JSON
```typst
#let conf = json("config.json")
#if conf.show_author [
  Autor: #conf.author
]
```

### YAML
```typst
#let meta = yaml("metadata.yml")
```

### Texto Plano
```typst
#let notes = read("notes.txt")
```

## Mejores Prácticas

* Usar archivos de datos para separar contenido del estilo.
* Combinar con loops (`#for`) para generar secciones repetitivas.
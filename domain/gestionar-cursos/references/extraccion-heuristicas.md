# Heurísticas de extracción — referencia

Detalle de las reglas de extracción que el skill aplica al
procesar cada módulo de Moodle. El SKILL.md principal enlaza
aquí; este archivo contiene los detalles y los snippets
de código.

## Enlaces Teams

SOLO capturar enlaces que apunten a `teams.microsoft.com/l/meetup-join/`.

Si el enlace usa acortadores o redirección de Moodle (`mod/url/view.php`), **ignorar**.

Si no hay enlace directo, marcar como `[PENDIENTE: Enlace no seguro o inexistente]`.

## forcedownload

Al descargar cualquier archivo de `pluginfile.php`, añadir:
- Si URL tiene `?`: `&forcedownload=1`
- Si URL no tiene `?`: `?forcedownload=1`

## H5P

Crear proxy HTML local:

```html
<!DOCTYPE html>
<html>
<head>
    <title>[Nombre]</title>
    <style>body { margin: 0; display: flex; justify-content: center; background: #000; overflow: hidden; height: 100vh; }</style>
</head>
<body>
    <iframe src="https://aulavirtual.uniremington.edu.co/mod/hvp/embed.php?id=[ID]"
            width="100%" height="100%" style="border:0;"
            allowfullscreen="allowfullscreen"></iframe>
    <script src="https://aulavirtual.uniremington.edu.co/mod/hvp/library/js/h5p-resizer.js" charset="UTF-8"></script>
</body>
</html>
```

Etiquetar en el mapa del sitio como `[Interactivo]`.

## Enlaces de Grabaciones

Los enlaces de grabaciones NO existen al inicio del curso. Se publican después.

En el flujo `estado`, verificar si aparecieron nuevos enlaces de
grabaciones y actualizar `SESIONES_SINCRONAS.md`.

## Nombres de Archivos de Actividades

Los nombres largos con patrones procesables se acortan automáticamente
(véase `_acortar_nombre_archivo` en `cli_init.py`):

- `Actividad de seguimiento (Calificable 10%) Disponible del 2 al 8 de febrero`
  → `Seguimiento[10%].md`
- `Unidad 1. Primer parcial (Calificable 25%) Disponible del 9 al 15 de febrero`
  → `Parcial-1[25%].md`
- `Prueba inicial (No calificable) Disponible hasta el 1 de febrero`
  → `PruebaInicial[N/A].md`

Reglas:
- Extrae `(Calificable X%)` o `(No calificable)` del nombre.
- Quita prefijos "Unidad X." / "Unidad X -".
- Mapea frases comunes a slugs cortos (`Seguimiento`, `Parcial-N`,
  `PruebaInicial`, `Cuestionario`, `ExamenFinal`).
- Fechas quedan dentro del contenido del archivo, no en el nombre.

Las fechas ya quedan reflejadas dentro del contenido.

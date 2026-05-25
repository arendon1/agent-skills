# Índice Local

## Estructura

```json
{
  "cache_valid_until": "2026-03-05T00:00:00",
  "cursos": {
    "2601B04G1": {
      "nombre": "BASES DE DATOS 2",
      "moodle_url": "https://aulavirtual.uniremington.edu.co/course/view.php?id=10272",
      "periodo": "2026-1",
      "bloque": "B1",
      "clickup": {
        "space_id": "universidad",
        "folder_id": "2026-1-B1",
        "list_id": "abc123"
      },
      "tasks": {
        "Prueba Inicial": "task_id_123",
        "Cuestionario evaluativo": "task_id_456",
        "Primer Parcial": "task_id_789"
      },
      "ultima_sincronizacion": "2026-01-26"
    }
  }
}
```

## Claves

- **cache_valid_until**: Timestamp de expiración del cache (ISO 8601)
- **cursos**: Mapa `curso_code` → datos del curso
- **clickup**: IDs de espacio, folder y lista en ClickUp
- **tasks**: Mapa `nombre_task` → `task_id` en ClickUp
- **ultima_sincronizacion**: Última vez que se sincronizó con ClickUp

## Actualización

El índice se actualiza automáticamente al:
1. Inicializar nuevo curso
2. Sincronizar fechas de entrega
3. Crear/actualizar tasks en ClickUp
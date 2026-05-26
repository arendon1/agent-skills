"""
Checkpoint para extracción de cursos.

Guarda progreso parcial en disco para poder reanudar si la sesión expira.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

CHECKPOINT_FILENAME = ".progress.json"


def load_checkpoint(course_dir: str) -> dict[str, Any] | None:
    """Carga checkpoint si existe."""
    path = Path(course_dir) / CHECKPOINT_FILENAME
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_checkpoint(course_dir: str, checkpoint: dict[str, Any]) -> None:
    """Guarda checkpoint en disco."""
    path = Path(course_dir) / CHECKPOINT_FILENAME
    checkpoint["timestamp"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)


def create_checkpoint(course_url: str, course_code: str, activities: list[dict]) -> dict[str, Any]:
    """Crea un checkpoint nuevo con todas las actividades pendientes."""
    return {
        "course_url": course_url,
        "course_code": course_code,
        "phase": "detail_extraction",
        "completed": [],
        "pending": activities,
        "timestamp": datetime.now().isoformat(),
    }


def mark_done(checkpoint: dict[str, Any], activity: dict, result_path: str) -> dict[str, Any]:
    """Marca una actividad como completada y la mueve de pending a completed."""
    # Remover de pending
    checkpoint["pending"] = [
        a for a in checkpoint["pending"]
        if a.get("url") != activity.get("url")
    ]
    # Agregar a completed
    checkpoint["completed"].append({
        **activity,
        "result_path": result_path,
        "completed_at": datetime.now().isoformat(),
    })
    return checkpoint


def has_checkpoint(course_dir: str) -> bool:
    """Verifica si existe un checkpoint."""
    return (Path(course_dir) / CHECKPOINT_FILENAME).exists()


def clear_checkpoint(course_dir: str) -> None:
    """Elimina el checkpoint (ej: al finalizar exitosamente)."""
    path = Path(course_dir) / CHECKPOINT_FILENAME
    if path.exists():
        path.unlink()

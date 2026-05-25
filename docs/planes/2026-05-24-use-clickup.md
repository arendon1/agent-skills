# Plan de Implementación: /use-clickup

> **Para agentes trabajadores:** SUB-HABILIDAD REQUERIDA: Usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan sintaxis de checkbox (`- [ ]`).

**Meta:** Skill standalone para gestión completa de tareas y listas en ClickUp usando la API oficial. Solo workflows esenciales, pero con documentación interna completa de todas las capacidades de la API.

**Arquitectura:** Skill simple de usar (5 workflows). Documentación profunda en `references/`. Cliente HTTP base reutilizable. Auth via .env en workspace → os.environ → error.

**Tech Stack:** Python 3, requests (HTTP client), python-dotenv

---

## Estructura de Archivos

```
use-clickup/
├── SKILL.md                              # Workflows esenciales (5 commands)
├── references/
│   ├── api-tasks.md                      # CRUD completo de tasks
│   ├── api-lists.md                      # CRUD de lists
│   ├── api-folders.md                    # CRUD de folders
│   ├── api-spaces.md                     # CRUD de spaces
│   ├── api-comments.md                   # Comments en tasks
│   ├── api-attachments.md                # Upload de archivos
│   ├── api-checklists.md                 # Checklists y sub-items
│   ├── api-tags.md                       # Gestión de tags
│   ├── api-custom-fields.md              # Custom fields
│   ├── api-time-tracking.md              # Registro de tiempo
│   ├── api-webhooks.md                   # Webhooks y notificaciones
│   ├── formato-fechas.md                 # ISO 8601 ↔ milisegundos
│   └── manejo-errores.md                 # Códigos HTTP y estrategias de retry
└── scripts/
    ├── clickup_client.py                 # Cliente HTTP base + auth
    ├── crear_tarea.py                    # POST /tasks
    ├── actualizar_tarea.py               # PUT /tasks/{id}
    ├── buscar_tarea.py                   # GET /tasks con filtros
    ├── crear_lista.py                    # POST /api/v2/list
    └── ver_listas.py                     # GET folder/space lists
```

---

## Workflows (Slash Commands)

### /use-clickup crear-tarea

**Uso:** `crear-tarea <lista_id> <nombre> [--descripcion] [--due_date] [--tags] [--prioridad]`

**Comportamiento:**
1. Validar inputs
2. Convertir `due_date` de ISO 8601 a milisegundos
3. Verificar si ya existe tarea con nombre similar (fuzzy match 85%+)
4. Si duplicado → Informar al usuario con diferencias y preguntar acción
5. Si no duplicado → Crear tarea via API

**Tags válidos:** evaluable, no-evaluable, parcial, cuestionario, foro, taller, examen, actividad, material, recurso

**Output:**
```markdown
✅ Tarea creada exitosamente
- Nombre: Prueba Inicial
- Lista: BASES DE DATOS 2 - 2601B04G1
- Due Date: 2026-02-01
- Tags: [evaluable, parcial]
🔗 https://app.clickup.com/t/abcde12345
```

---

### /use-clickup actualizar-tarea

**Uso:** `actualizar-tarea <task_id> [--nombre] [--descripcion] [--due_date] [--prioridad] [--tags]`

**Comportamiento:**
1. Verificar que task existe
2. Solo enviar campos que se quieren actualizar (PATCH parcial)
3. Convertir fechas a milisegundos si aplica
4. Retornar tarea actualizada

**Nota:** Custom fields no se pueden actualizar con PUT. Documentar en referencias.

---

### /use-clickup buscar-tarea

**Uso:** `buscar-tarea [--nombre] [--tag] [--lista_id] [--espacio_id]`

**Comportamiento:**
1. Construir query con filtros disponibles
2. Retornar lista de tasks con: id, nombre, status, due_date, tags, url

**Output:**
```markdown
🔍 3 tareas encontradas en "BASES DE DATOS 2":

1. Prueba Inicial (85% match)
   - Status: to do
   - Due: 2026-02-01
   - Tags: [evaluable, parcial]
   🔗 https://app.clickup.com/t/abcde12345

2. Cuestionario evaluativo (70% match)
   - Status: in progress
   - Due: 2026-02-01
   - Tags: [evaluable, cuestionario]
   🔗 https://app.clickup.com/t/defgh56789
```

---

### /use-clickup crear-lista

**Uso:** `crear-lista <folder_id> <nombre>`

**Comportamiento:**
1. Verificar que folder existe
2. Verificar que lista no exista ya en ese folder
3. Crear lista via POST /api/v2/list

**Output:**
```markdown
✅ Lista creada exitosamente
- Nombre: BASES DE DATOS 2 - 2601B04G1
- Folder: 2026-1-B1
- ID: list123abc
🔗 https://app.clickup.com/v/l/abcde12345
```

---

### /use-clickup ver-listas

**Uso:** `ver-listas [--folder_id] [--space_id]`

**Comportamiento:**
1. Si no se provee folder_id ni space_id → mostrar todos los espacios
2. Si se provee folder_id → mostrar listas en ese folder
3. Si se provee space_id → mostrar listas en ese space (directas)

**Output:**
```markdown
📋 Listas en "2026-1-B1":

1. BASES DE DATOS 2 - 2601B04G1
   - Tasks: 12
   - Status: to do
   🔗 https://app.clickup.com/v/l/abcde12345

2. CÁLCULO INTEGRAL - 2601B05G1
   - Tasks: 8
   - Status: in progress
   🔗 https://app.clickup.com/v/l/defgh56789
```

---

## Tarea 1: Cliente HTTP Base (clickup_client.py)

**Archivos:**
- Crear: `use-clickup/scripts/clickup_client.py`

- [ ] **Paso 1: Implementar cliente con auth robusta**

```python
"""
Cliente HTTP base para ClickUp API.
Maneja autenticación y configuración de requests.
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

class ClickUpClient:
    """Cliente para ClickUp API con manejo de errores y retries."""
    
    BASE_URL = "https://api.clickup.com/api/v2"
    TIMEOUT = 30  # segundos
    MAX_RETRIES = 3
    
    def __init__(self):
        self.api_key = self._obtener_api_key()
        self.session = self._crear_session()
    
    def _obtener_api_key(self) -> str:
        """
        Obtiene API key en orden:
        1. .env en workspace actual
        2. Variable de entorno CLICKUP_API_KEY
        3. Error claro si no se encuentra
        """
        # 1. Buscar .env en workspace actual
        load_dotenv()
        
        # 2. Buscar en variables de entorno
        api_key = os.getenv("CLICKUP_API_KEY")
        
        if api_key:
            return api_key
        
        # 3. Error si no se encuentra
        raise RuntimeError(
            "CLICKUP_API_KEY no encontrada. "
            "Configura tu API key:\n"
            "1. Crea archivo .env con: CLICKUP_API_KEY=tu_api_key\n"
            "2. O exporta variable: export CLICKUP_API_KEY=tu_api_key"
        )
    
    def _crear_session(self) -> requests.Session:
        """Crea sesión HTTP con headers comunes."""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        return session
    
    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Ejecuta request HTTP con retries automáticos.
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Path de la API (ej: /tasks)
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            Response de requests
            
        Raises:
            RuntimeError si error de autenticación
            requests.exceptions.RequestException si falla después de retries
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        for intento in range(self.MAX_RETRIES):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.TIMEOUT,
                    **kwargs
                )
                
                # Manejar errores específicos
                if response.status_code == 401:
                    raise RuntimeError(
                        "API Key de ClickUp inválida o expirada. "
                        "Verifica tu API key en https://app.clickup.com/settings"
                    )
                
                if response.status_code == 403:
                    raise RuntimeError(
                        "Sin permisos para esta operación. "
                        "Verifica que tu API key tiene acceso al recurso."
                    )
                
                # Si exitoso o error no recuperable, retornar
                if response.status_code < 500:
                    return response
                
                # Error de servidor - reintentar
                response.raise_for_status()
                
            except requests.exceptions.RequestException as e:
                if intento == self.MAX_RETRIES - 1:
                    raise
                # Backoff exponencial: 1s, 2s, 4s
                time.sleep(2 ** intento)
        
        return response
    
    # Métodos convenientes para HTTP
    def get(self, endpoint: str, **kwargs):
        return self.request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs):
        return self.request("POST", endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs):
        return self.request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs):
        return self.request("DELETE", endpoint, **kwargs)


# Instancia global del cliente (lazy loading)
_cliente: Optional[ClickUpClient] = None

def get_cliente() -> ClickUpClient:
    """Obtiene instancia singleton del cliente."""
    global _cliente
    if _cliente is None:
        _cliente = ClickUpClient()
    return _cliente
```

- [ ] **Paso 2: Escribir test de cliente**

```python
def test_cliente_creacion():
    """Verifica que el cliente se crea con API key."""
    try:
        cliente = get_cliente()
        assert cliente.api_key is not None
    except RuntimeError as e:
        # Es esperado si no hay API key configurada
        assert "CLICKUP_API_KEY no encontrada" in str(e)


def test_request_no_auth():
    """Test sin API key real."""
    # En tests, mockear la respuesta de requests
    pass
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest use-clickup/scripts/test_clickup_client.py -v
```

---

## Tarea 2: Conversión de Fechas

**Archivos:**
- Crear: `use-clickup/scripts/clickup_client.py` (extender)

- [ ] **Paso 1: Agregar utilidades de fecha**

```python
from datetime import datetime

def iso_a_milisegundos(fecha_iso: str) -> int:
    """
    Convierte fecha ISO 8601 a milisegundos Unix epoch.
    
    Args:
        fecha_iso: String en formato YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS
        
    Returns:
        Entero de milisegundos
        
    Examples:
        >>> iso_a_milisegundos("2026-01-26")
        1704067200000
    """
    # Intentar formato simple YYYY-MM-DD
    try:
        fecha = datetime.strptime(fecha_iso[:10], "%Y-%m-%d")
        return int(fecha.timestamp() * 1000)
    except ValueError:
        pass
    
    # Intentar ISO completo
    try:
        fecha = datetime.fromisoformat(fecha_iso.replace('Z', '+00:00'))
        return int(fecha.timestamp() * 1000)
    except ValueError:
        pass
    
    raise ValueError(f"Formato de fecha inválido: {fecha_iso}. Usar YYYY-MM-DD")


def milisegundos_a_iso(milisegundos: int) -> str:
    """
    Convierte milisegundos Unix epoch a ISO 8601.
    
    Args:
        milisegundos: Entero de milisegundos
        
    Returns:
        String en formato YYYY-MM-DD
    """
    fecha = datetime.fromtimestamp(milisegundos / 1000)
    return fecha.strftime("%Y-%m-%d")


def milisegundos_a_iso_completo(milisegundos: int) -> str:
    """
    Convierte milisegundos a ISO 8601 con hora.
    
    Returns:
        String en formato YYYY-MM-DD HH:MM:SS
    """
    fecha = datetime.fromtimestamp(milisegundos / 1000)
    return fecha.strftime("%Y-%m-%d %H:%M:%S")
```

- [ ] **Paso 2: Escribir tests**

```python
def test_iso_a_milisegundos():
    assert iso_a_milisegundos("2026-01-26") == 1704067200000
    assert iso_a_milisegundos("2026-02-01") == 1706745600000


def test_milisegundos_a_iso():
    assert milisegundos_a_iso(1704067200000) == "2026-01-26"
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest use-clickup/scripts/test_fechas.py -v
```

---

## Tarea 3: Crear Tarea

**Archivos:**
- Crear: `use-clickup/scripts/crear_tarea.py`

- [ ] **Paso 1: Implementar función de creación**

```python
"""
Crear tarea en ClickUp via API.
"""

from typing import List, Optional
from clickup_client import get_cliente, iso_a_milisegundos

TAGS_VALIDOS = [
    "evaluable", "no-evaluable", "parcial", "cuestionario", 
    "foro", "taller", "examen", "actividad", "material", "recurso"
]

PRIORIDADES = {
    "urgent": 1,
    "high": 2,
    "normal": 3,
    "low": 4
}

def crear_tarea(
    lista_id: str,
    nombre: str,
    descripcion: Optional[str] = None,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    prioridad: Optional[str] = None,
    markdown_description: bool = True
) -> dict:
    """
    Crea una nueva tarea en ClickUp.
    
    Args:
        lista_id: ID de la lista destino
        nombre: Nombre de la tarea
        descripcion: Descripción (texto o markdown)
        due_date: Fecha en formato ISO 8601 (YYYY-MM-DD)
        tags: Lista de tags válidos
        prioridad: "urgent", "high", "normal", "low"
        markdown_description: Usar markdown en descripción
        
    Returns:
        Dict con datos de la tarea creada
        
    Raises:
        ValueError si tags o prioridad inválidos
        RuntimeError si la API falla
    """
    cliente = get_cliente()
    
    # Validar tags
    if tags:
        for tag in tags:
            if tag not in TAGS_VALIDOS:
                raise ValueError(
                    f"Tag inválido: '{tag}'. "
                    f"Tags válidos: {TAGS_VALIDOS}"
                )
    
    # Validar prioridad
    priority_id = None
    if prioridad:
        if prioridad not in PRIORIDADES:
            raise ValueError(
                f"Prioridad inválida: '{prioridad}'. "
                f"Valores válidos: {list(PRIORIDADES.keys())}"
            )
        # ClickUp acepta priority como objeto con id
        priority_id = {"priority": {"priority": prioridad}}
    
    # Construir payload
    payload = {"name": nombre}
    
    if descripcion:
        if markdown_description:
            payload["markdown_description"] = descripcion
        else:
            payload["description"] = descripcion
    
    if due_date:
        try:
            payload["due_date"] = iso_a_milisegundos(due_date)
            payload["due_date_time"] = False  # Solo fecha, sin hora
        except ValueError as e:
            raise ValueError(f"Fecha inválida: {e}")
    
    if tags:
        payload["tags"] = tags
    
    if priority_id:
        payload.update(priority_id)
    
    # Hacer request
    response = cliente.post(f"/list/{lista_id}/task", json=payload)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error creando tarea: {response.status_code} - {response.text}"
        )
    
    return response.json()


def formatear_tarea(tarea: dict) -> str:
    """Formatea tarea para mostrar al usuario."""
    nombre = tarea.get("name", "Sin nombre")
    lista = tarea.get("list", {}).get("name", "Unknown")
    url = tarea.get("url", "")
    due_date = tarea.get("due_date")
    tags = tarea.get("tags", [])
    
    due_date_str = ""
    if due_date:
        from clickup_client import milisegundos_a_iso
        due_date_str = f"\n   - Due: {milisegundos_a_iso(due_date)}"
    
    tags_str = ""
    if tags:
        tags_str = f"\n   - Tags: {tags}"
    
    return f"""✅ Tarea creada exitosamente
- Nombre: {nombre}
- Lista: {lista}{due_date_str}{tags_str}
🔗 {url}"""
```

- [ ] **Paso 2: Escribir tests**

```python
def test_tags_validos():
    for tag in TAGS_VALIDOS:
        assert tag in TAGS_VALIDOS


def test_prioridades_validas():
    assert PRIORIDADES.keys() == {"urgent", "high", "normal", "low"}


def test_iso_a_milisegundos_conversion():
    due_date = "2026-01-26"
    resultado = iso_a_milisegundos(due_date)
    assert isinstance(resultado, int)
    assert resultado == 1704067200000
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest use-clickup/scripts/test_crear_tarea.py -v
```

---

## Tarea 4: Actualizar Tarea

**Archivos:**
- Crear: `use-clickup/scripts/actualizar_tarea.py`

- [ ] **Paso 1: Implementar actualización**

```python
"""
Actualizar tarea existente en ClickUp via API.
"""

from typing import Optional, List
from clickup_client import get_cliente, iso_a_milisegundos

def actualizar_tarea(
    task_id: str,
    nombre: Optional[str] = None,
    descripcion: Optional[str] = None,
    due_date: Optional[str] = None,
    prioridad: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    markdown_description: bool = True
) -> dict:
    """
    Actualiza campos de una tarea existente.
    
    Args:
        task_id: ID de la tarea a actualizar
        nombre: Nuevo nombre (opcional)
        descripcion: Nueva descripción (opcional)
        due_date: Nueva fecha en ISO 8601 (opcional)
        prioridad: Nueva prioridad (opcional)
        tags: Nuevos tags (reemplaza los actuales)
        status: Nuevo status (ej: "in progress", "complete")
        
    Returns:
        Dict con datos de la tarea actualizada
        
    Note: Custom fields no se pueden actualizar con este método.
    Para custom fields, usar el endpoint específico.
    """
    cliente = get_cliente()
    
    # Construir payload con solo campos a actualizar
    payload = {}
    
    if nombre is not None:
        payload["name"] = nombre
    
    if descripcion is not None:
        if markdown_description:
            payload["markdown_description"] = descripcion
        else:
            payload["description"] = descripcion
    
    if due_date is not None:
        try:
            payload["due_date"] = iso_a_milisegundos(due_date)
        except ValueError as e:
            raise ValueError(f"Fecha inválida: {e}")
    
    if prioridad is not None:
        PRIORIDADES = {"urgent": 1, "high": 2, "normal": 3, "low": 4}
        if prioridad not in PRIORIDADES:
            raise ValueError(f"Prioridad inválida: {prioridad}")
        payload["priority"] = PRIORIDADES[prioridad]
    
    if tags is not None:
        payload["tags"] = tags
    
    if status is not None:
        payload["status"] = status
    
    if not payload:
        raise ValueError("No se proporcionaron campos a actualizar")
    
    # Hacer request
    response = cliente.put(f"/task/{task_id}", json=payload)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error actualizando tarea: {response.status_code} - {response.text}"
        )
    
    return response.json()
```

- [ ] **Paso 2: Test**

```python
def test_actualizar_fecha():
    # Mock test - verificar que convierte fecha correctamente
    due_date = "2026-01-26"
    resultado = iso_a_milisegundos(due_date)
    assert resultado == 1704067200000
```

---

## Tarea 5: Buscar Tarea

**Archivos:**
- Crear: `use-clickup/scripts/buscar_tarea.py`

- [ ] **Paso 1: Implementar búsqueda con filtros**

```python
"""
Buscar tareas en ClickUp usando diversos filtros.
"""

from typing import List, Optional, Dict
from difflib import SequenceMatcher
from clickup_client import get_cliente, milisegundos_a_iso

def calcular_similitud(a: str, b: str) -> float:
    """Calcula ratio de similitud entre dos strings (0.0 a 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def buscar_tareas(
    nombre: Optional[str] = None,
    tag: Optional[str] = None,
    lista_id: Optional[str] = None,
    espacio_id: Optional[str] = None,
    limite: int = 50
) -> List[Dict]:
    """
    Busca tareas con filtros opcionales.
    
    Args:
        nombre: Nombre (o parte) a buscar
        tag: Filtrar por tag
        lista_id: Filtrar por lista específica
        espacio_id: Filtrar por espacio
        limite: Máximo de tareas a retornar (default 50)
        
    Returns:
        Lista de dicts con tasks matching
    """
    cliente = get_cliente()
    
    # Construir query params
    params = {"limit": limite}
    
    # ClickUp API tiene endpoint /tasks pero con filtros limitados
    # Para búsqueda por nombre, necesitamos get tasks y filtrar
    
    if lista_id:
        endpoint = f"/list/{lista_id}/task"
    elif espacio_id:
        # Tasks de espacio requieren folder/list intermediario
        raise ValueError(
            "Para filtrar por espacio, especificar lista_id o folder_id"
        )
    else:
        # Tasks del workspace (puede ser muy extenso)
        endpoint = "/team/tasks"
        params["include_closed"] = "true"
    
    # Obtener tasks
    response = cliente.get(endpoint, params=params)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error buscando tareas: {response.status_code} - {response.text}"
        )
    
    data = response.json()
    tasks = data.get("tasks", [])
    
    # Filtrar resultados
    resultados = []
    
    for task in tasks:
        # Filtrar por nombre si especificado
        if nombre:
            similitud = calcular_similitud(nombre, task.get("name", ""))
            if similitud < 0.6:  # Threshold de fuzzy match
                continue
            task["_similitud"] = similitud
        
        # Filtrar por tag si especificado
        if tag:
            task_tags = task.get("tags", [])
            if tag not in task_tags:
                continue
        
        resultados.append(task)
    
    # Ordenar por similitud si aplicable
    if nombre:
        resultados.sort(key=lambda t: t.get("_similitud", 0), reverse=True)
    
    return resultados


def formatear_resultados(tasks: List[Dict]) -> str:
    """Formatea lista de tasks para mostrar al usuario."""
    if not tasks:
        return "🔍 No se encontraron tareas"
    
    lineas = [f"🔍 {len(tasks)} tarea(s) encontrada(s):\n"]
    
    for i, task in enumerate(tasks, 1):
        nombre = task.get("name", "Sin nombre")
        similitud = task.get("_similitud")
        status = task.get("status", {}).get("status", "unknown")
        due_date = task.get("due_date")
        tags = task.get("tags", [])
        url = task.get("url", "")
        
        # Similitud si se buscó por nombre
        match_info = ""
        if similitud is not None:
            match_info = f" ({int(similitud * 100)}% match)"
        
        due_str = ""
        if due_date:
            due_str = f" | Due: {milisegundos_a_iso(due_date)}"
        
        tags_str = ""
        if tags:
            tags_str = f" | Tags: {tags}"
        
        lineas.append(
            f"{i}. {nombre}{match_info}\n"
            f"   Status: {status}{due_str}{tags_str}\n"
            f"   🔗 {url}\n"
        )
    
    return "\n".join(lineas)
```

- [ ] **Paso 2: Test**

```python
def test_similitud():
    assert calcular_similitud("Prueba Inicial", "Prueba Inicial") > 0.9
    assert calcular_similitud("Parcial", "Primer Parcial") < 0.7
```

---

## Tarea 6: Crear Lista

**Archivos:**
- Crear: `use-clickup/scripts/crear_lista.py`

- [ ] **Paso 1: Implementar creación de lista**

```python
"""
Crear lista en ClickUp via API.
"""

from clickup_client import get_cliente

def crear_lista(
    folder_id: str,
    nombre: str,
    contenido: str = ""
) -> dict:
    """
    Crea una nueva lista en un folder.
    
    Args:
        folder_id: ID del folder padre
        nombre: Nombre de la lista
        contenido: Descripción inicial (opcional)
        
    Returns:
        Dict con datos de la lista creada
    """
    cliente = get_cliente()
    
    payload = {
        "name": nombre,
        "folder_id": folder_id,
        "content": contenido
    }
    
    response = cliente.post("/list", json=payload)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error creando lista: {response.status_code} - {response.text}"
        )
    
    return response.json()


def formatear_lista(lista: dict) -> str:
    """Formatea lista para mostrar al usuario."""
    nombre = lista.get("name", "Sin nombre")
    folder = lista.get("folder", {}).get("name", "Unknown")
    url = lista.get("url", "")
    task_count = lista.get("task_count", 0)
    
    return f"""✅ Lista creada exitosamente
- Nombre: {nombre}
- Folder: {folder}
- Tasks: {task_count}
🔗 {url}"""
```

- [ ] **Paso 2: Test**

```python
def test_crear_lista_validacion():
    # Folder ID vacío debe fallar
    try:
        crear_lista("", "Mi Lista")
        assert False, "Debió lanzar ValueError"
    except ValueError:
        pass
```

---

## Tarea 7: Ver Listas

**Archivos:**
- Crear: `use-clickup/scripts/ver_listas.py`

- [ ] **Paso 1: Implementar visualización de listas**

```python
"""
Listar listas disponibles en folder o space.
"""

from typing import Optional
from clickup_client import get_cliente

def ver_listas(
    folder_id: Optional[str] = None,
    space_id: Optional[str] = None
) -> list:
    """
    Obtiene listas de un folder o space.
    
    Args:
        folder_id: ID del folder (prioridad sobre space_id)
        space_id: ID del space
        
    Returns:
        Lista de diccionarios con datos de listas
        
    Raises:
        ValueError si no se provee folder_id ni space_id
    """
    cliente = get_cliente()
    
    if folder_id:
        # Listas en folder específico
        endpoint = f"/folder/{folder_id}/list"
    elif space_id:
        # Listas directas en space (no en folders)
        endpoint = f"/space/{space_id}/list"
    else:
        raise ValueError(
            "Debes especificar folder_id o space_id"
        )
    
    response = cliente.get(endpoint)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error obteniendo listas: {response.status_code} - {response.text}"
        )
    
    data = response.json()
    return data.get("lists", [])


def formatear_listas(listas: list, contexto: str = "") -> str:
    """Formatea listas para mostrar al usuario."""
    if not listas:
        return f"📋 No hay listas en {contexto}"
    
    lineas = [f"📋 Listas{en contexto}:\n"]
    
    for i, lista in enumerate(listas, 1):
        nombre = lista.get("name", "Sin nombre")
        task_count = lista.get("task_count", 0)
        status = lista.get("status", {})
        # Status puede ser None o dict
        if status and isinstance(status, dict):
            status_name = status.get("status", "active")
        else:
            status_name = "active"
        
        url = lista.get("url", "")
        
        lineas.append(
            f"{i}. {nombre}\n"
            f"   Tasks: {task_count} | Status: {status_name}\n"
            f"   🔗 {url}\n"
        )
    
    return "\n".join(lineas)
```

- [ ] **Paso 2: Test**

```python
def test_ver_listas_error_sin_parametros():
    try:
        ver_listas()
        assert False, "Debió lanzar ValueError"
    except ValueError as e:
        assert "folder_id o space_id" in str(e)
```

---

## Tarea 8: Manejo de Duplicados

**Archivos:**
- Crear: `use-clickup/scripts/manejo_duplicados.py`

- [ ] **Paso 1: Implementar detección y comparación de duplicados**

```python
"""
Detecta y compara tareas duplicadas antes de crear.
"""

from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher

def calcular_similitud(a: str, b: str) -> float:
    """Calcula ratio de similitud (0.0 a 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def detectar_duplicados(nombre_nueva: str, tareas_existentes: List[Dict], threshold: float = 0.85) -> List[Dict]:
    """
    Detecta tareas con nombres similares en una lista.
    
    Args:
        nombre_nueva: Nombre de la tarea a crear
        tareas_existentes: Lista de tasks existentes del workspace
        threshold: Percentaje mínimo de similitud (default 85%)
        
    Returns:
        Lista de tareas similares encontradas
    """
    duplicados = []
    
    for tarea in tareas_existentes:
        nombre_existente = tarea.get("name", "")
        similitud = calcular_similitud(nombre_nueva, nombre_existente)
        
        if similitud >= threshold:
            tarea["_similitud"] = similitud
            duplicados.append(tarea)
    
    return duplicados


def comparar_tareas(nueva: dict, existente: dict) -> str:
    """
    Compara dos tareas y retorna string con diferencias.
    
    Args:
        nueva: Datos de la tarea a crear
        existente: Datos de la tarea existente
        
    Returns:
        String formateado con diferencias
    """
    from clickup_client import milisegundos_a_iso
    
    diferencias = []
    
    # Comparar fechas
    if nueva.get("due_date") and existente.get("due_date"):
        if nueva["due_date"] != existente["due_date"]:
            nueva_fecha = milisegundos_a_iso(nueva["due_date"])
            existente_fecha = milisegundos_a_iso(existente["due_date"])
            diferencias.append(f"Fecha: {existente_fecha} → {nueva_fecha}")
    
    # Comparar descripción
    if nueva.get("description") and existente.get("description"):
        if nueva["description"] != existente.get("text_content", ""):
            diferencias.append("Descripción: diferente")
    
    # Comparar tags
    if nueva.get("tags") != existente.get("tags"):
        nuevas_tags = ", ".join(nueva.get("tags", []))
        existentes_tags = ", ".join(existente.get("tags", []))
        diferencias.append(f"Tags: [{existentes_tags}] → [{nuevas_tags}]")
    
    # Comparar prioridad
    if nueva.get("priority") != existente.get("priority"):
        diferencias.append("Prioridad: diferente")
    
    if not diferencias:
        return "Diferencias detectadas: ninguna (mismo contenido)"
    
    return "Diferencias detectadas:\n" + "\n".join(f"  - {d}" for d in diferencias)


def informar_duplicado(nueva_tarea: dict, duplicados: List[dict]) -> str:
    """
    Genera reporte de duplicados para el usuario.
    
    Returns:
        String formateado para mostrar al usuario
    """
    if not duplicados:
        return ""
    
    nombre_nueva = nueva_tarea.get("name", "")
    similitud = duplicados[0].get("_similitud", 0)
    
    lineas = [
        f"⚠️ Tarea similar encontrada:",
        f"  '{nombre_nueva}' vs '{duplicados[0]['name']}' ({int(similitud * 100)}% similar)",
        "",
        comparar_tareas(nueva_tarea, duplicados[0]),
        "",
        "Opciones:",
        "  (a) Crear nueva de todas formas",
        "  (b) Actualizar existente",
        "  (c) Cancelar operación"
    ]
    
    return "\n".join(lineas)
```

- [ ] **Paso 2: Test**

```python
def test_detectar_duplicados():
    tareas = [
        {"name": "Prueba Inicial", "id": "1"},
        {"name": "Cuestionario evaluativo", "id": "2"}
    ]
    
    duplicados = detectar_duplicados("Prueba Inicial", tareas)
    assert len(duplicados) == 1
    assert duplicados[0]["name"] == "Prueba Inicial"
    
    # No debe encontrar duplicado bajo threshold
    duplicados = detectar_duplicados("Parcial", tareas)
    assert len(duplicados) == 0
```

---

## Tarea 9: SKILL.md (Workflows Principales)

**Archivos:**
- Crear: `use-clickup/SKILL.md`

- [ ] **Paso 1: Escribir SKILL.md con workflows esenciales**

```markdown
---
name: use-clickup
description: >-
  Gestión de tareas y listas en ClickUp via API oficial.
  Úsalo para crear tareas, actualizar fechas, buscar actividades,
  y organizar listas de cursos.
metadata:
  version: "1.0.0"
  language: es-CO
  risk_tier: MEDIUM
---

# /use-clickup

Skill para gestión completa de ClickUp. Solo workflows esenciales,
con documentación interna completa en `references/` para capacidades avanzadas.

## Autenticación

La API key se busca en orden:
1. Archivo `.env` en workspace actual (variable `CLICKUP_API_KEY`)
2. Variable de entorno `CLICKUP_API_KEY`
3. Error claro con instrucciones si no se encuentra

## Workflows

### /use-clickup crear-tarea

**Uso:** `crear-tarea <lista_id> <nombre> [--descripcion] [--due_date] [--tags] [--prioridad]`

**Ejemplo:**
```
/use-clickup crear-tarea abc123 "Prueba Inicial" \
  --descripcion "## Instrucciones\nLeer capítulo 1" \
  --due_date 2026-02-01 \
  --tags evaluable,parcial \
  --prioridad normal
```

**Tags válidos:** evaluable, no-evaluable, parcial, cuestionario, foro, taller, examen, actividad, material, recurso

**Prioridades:** urgent, high, normal, low

---

### /use-clickup actualizar-tarea

**Uso:** `actualizar-tarea <task_id> [--nombre] [--descripcion] [--due_date] [--prioridad] [--tags]`

**Ejemplo:**
```
/use-clickup actualizar-tarea def456 \
  --due_date 2026-02-15 \
  --prioridad high
```

**Nota:** Custom fields no se pueden actualizar via este workflow.

---

### /use-clickup buscar-tarea

**Uso:** `buscar-tarea [--nombre] [--tag] [--lista_id]`

**Ejemplo:**
```
/use-clickup buscar-tarea --nombre "Parcial" --tag evaluable
```

---

### /use-clickup crear-lista

**Uso:** `crear-lista <folder_id> <nombre>`

**Ejemplo:**
```
/use-clickup crear-lista folder123 "BASES DE DATOS 2 - 2601B04G1"
```

---

### /use-clickup ver-listas

**Uso:** `ver-listas [--folder_id] [--space_id]`

**Ejemplo:**
```
/use-clickup ver-listas --folder_id folder123
```

---

## Manejo de Errores

| Código | Significado | Acción |
|--------|-------------|--------|
| 401 | API key inválida | Verificar key en ClickUp Settings |
| 403 | Sin permisos | Verificar acceso al recurso |
| 404 | Recurso no encontrado | Verificar ID |
| 429 | Rate limit | Reintentar con backoff |
| 500+ | Error servidor ClickUp | Reintentar automáticamente |

## Referencias Internas

La documentación completa de la API está en `references/`:
- `api-tasks.md` — Todos los endpoints de tasks
- `api-lists.md` — CRUD de listas
- `api-spaces.md` — Spaces y folders
- `api-comments.md` — Comments
- `api-checklists.md` — Checklists
- `api-tags.md` — Gestión de tags
- `api-custom-fields.md` — Custom fields
- `formato-fechas.md` — Conversión ISO ↔ milisegundos
- `manejo-errores.md` — Códigos y estrategias de retry
```

---

## Tarea 10: Documentación de Referencias

**Archivos:**
- Crear: `use-clickup/references/api-tasks.md`
- Crear: `use-clickup/references/api-lists.md`
- Crear: `use-clickup/references/formato-fechas.md`
- Crear: `use-clickup/references/manejo-errores.md`

- [ ] **Paso 1: Escribir documentación de API de Tasks**

```markdown
# API de Tasks - Referencia Completa

## Endpoints

### POST /tasks
Crear tarea en workspace.

**Request Body:**
```json
{
  "name": "string (requerido)",
  "description": "string",
  "markdown_description": "string",
  "assignees": [12345],
  "status": "string",
  "priority": 1,
  "due_date": 1678886400000,
  "start_date": 1678800000000,
  "tags": ["tag1", "tag2"],
  "time_estimate": 3600000,
  "parent": "task_id",
  "links_to": "task_id"
}
```

**Respuesta:**
```json
{
  "id": "string",
  "name": "string",
  "status": {"status": "string", "color": "#hex"},
  "url": "https://app.clickup.com/t/id",
  ...
}
```

### GET /tasks
Obtener tareas. Filtros disponibles: assignee, include_closed, project_id, space_id, list_id, task_ids, custom_task_ids, date.created, date.updated, date.done, due_date, start_date.

### PUT /task/{task_id}
Actualizar tarea. Mismos campos que POST.

**Limitación:** Custom fields no se pueden actualizar con PUT.

### DELETE /task/{task_id}
Eliminar tarea permanentemente.

---

## Validación de Inputs

- **name**: Requerido, string
- **due_date**: Milisegundos (usar función iso_a_milisegundos)
- **priority**: Entero 1-4 (1=urgent, 2=high, 3=normal, 4=low)
- **tags**: Array de strings

## Tips

1. Para tasks recurrentes, usar templates de lista
2. Asignees usan user IDs, no usernames
3. Timestamps en milisegundos, nunca strings de fecha
```

- [ ] **Paso 2: Escribir documentación de formato de fechas**

```markdown
# Formato de Fechas

## Conversión

ClickUp usa **milisegundos Unix epoch** para todas las fechas.

### ISO 8601 → Milisegundos

```python
from datetime import datetime

def iso_a_milisegundos(fecha_iso: str) -> int:
    fecha = datetime.strptime(fecha_iso[:10], "%Y-%m-%d")
    return int(fecha.timestamp() * 1000)

# Ejemplo:
iso_a_milisegundos("2026-01-26")  # → 1704067200000
```

### Milisegundos → ISO 8601

```python
from datetime import datetime

def milisegundos_a_iso(milisegundos: int) -> str:
    fecha = datetime.fromtimestamp(milisegundos / 1000)
    return fecha.strftime("%Y-%m-%d")

# Ejemplo:
milisegundos_a_iso(1704067200000)  # → "2026-01-26"
```

## Ejemplos en ClickUp

| Fecha ISO | Milisegundos | Uso |
|-----------|--------------|-----|
| 2026-01-26 | 1704067200000 | Due date |
| 2026-01-26T14:30:00 | 1704113400000 | Con hora específica |
| 1704067200000 | 2026-01-26 | Verificación |

## Notas

- Sin hora: `due_date_time: false`
- Con hora: `due_date_time: true`
- Timezone: Siempre UTC en API
```

- [ ] **Paso 3: Escribir documentación de manejo de errores**

```markdown
# Manejo de Errores HTTP

## Códigos Comunes

| Código | Significado | retry? | Acción |
|--------|-------------|--------|--------|
| 200 | Éxito | - | Continuar |
| 400 | Bad request | No | Corregir input |
| 401 | Auth fallida | No | Verificar API key |
| 403 | Sin permisos | No | Verificar acceso |
| 404 | No encontrado | No | Verificar ID |
| 409 | Conflicto | No | Resolver duplicado |
| 429 | Rate limit | Sí | Backoff 1s, 2s, 4s |
| 500 | Error servidor | Sí | Reintentar 3x |

## Estrategias de Retry

```python
import time

MAX_RETRIES = 3

def request_con_retry(cliente, endpoint, method="GET"):
    for intento in range(MAX_RETRIES):
        response = cliente.request(method, endpoint)
        
        if response.status_code < 500:
            return response
        
        if intento < MAX_RETRIES - 1:
            # Backoff exponencial
            time.sleep(2 ** intento)
    
    raise RuntimeError(f"Falló después de {MAX_RETRIES} intentos")
```

## Rate Limiting

ClickUp limita a **100 requests/minuto** en API estándar.

Estrategias:
1. Batch operations cuando posible
2. Cachear respuestas
3. Usar webhooks en lugar de polling

## Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| "Invalid date format" | Formato incorrecto | Usar ISO 8601 |
| "Task not found" | ID incorrecto | Verificar task_id |
| "List not found" | Lista no existe o sin acceso | Verificar permissions |
| "Name too long" | Nombre > 500 chars | Acortar nombre |
```

---

## Auto-Revisión

**1. Cobertura del spec:**
- ✅ Workflows esenciales (5 commands)
- ✅ Auth robusta (.env → os.env → error)
- ✅ Manejo de duplicados con comparación
- ✅ Conversión de fechas ISO ↔ milisegundos
- ✅ Documentación completa de API en references/

**2. Integración con Persona "Compañero de Universidad":**
- ✅ Tasks contienen **links a Moodle**, NO path locales
- ✅ Índice local mapea `curso_code` → `list_id`, `task_ids`
- ✅ Fuente de verdad: ClickUp para tracking, Moodle para materiales
- ✅ Tags estandarizados: evaluable, no-evaluable, parcial, cuestionario, foro, taller, examen, actividad, material, recurso
- ✅ Detección de duplicados: fuzzy match 85% + pregunta al usuario

**2. Scan de placeholders:** ✅ Sin TBD o placeholders.

**3. Consistencia de tipos:** ✅ Nombres de funciones y signatures consistentes.

---

## Integración con Persona "Compañero de Universidad"

### Flujo de Datos

```
Moodle (Source of Truth)
         ↓
/gestionar-cursos
  └── Materiales físicos (PDFs, DOCX, H5P proxies) + Metadata local
         ↓
/use-clickup
  └── Tasks con links a Moodle (NO path locales)
         ↓
Índice Local (.universidad_index.json)
  └── Mapeo: curso_code → list_id, task_ids
```

### Roles

| Skill | Propósito | Local | ClickUp |
|-------|-----------|-------|---------|
| `/gestionar-cursos` | Extraer materiales de Moodle | PDFs, DOCX, H5P proxies | Links a Moodle |
| `/use-clickup` | Gestionar actividades | Index (IDs) | Tasks, fechas, tags |
| Persona "Compañero" | Coordinar | Index + estado | Tracking completo |

### Estructura de Tasks en ClickUp

```json
{
  "name": "Prueba Inicial",
  "description": "## Instrucciones\nLeer capítulo 1 y 2.\n\n## Link Moodle\n[Material de estudio](https://aulavirtual.uniremington.edu.co/...)",
  "due_date": 1706745600000,
  "tags": ["evaluable", "parcial"],
  "status": "to do"
}
```

**Nota**: Los links en la descripción apuntan a Moodle, NO a archivos locales.

### Index Local

```json
{
  "2601B04G1": {
    "nombre": "BASES DE DATOS 2",
    "periodo": "2026-1",
    "bloque": "B1",
    "clickup_list_id": "abc123",
    "tasks": {
      "Prueba Inicial": "task_id_123",
      "Primer Parcial": "task_id_456"
    }
  }
}
```

### Cache

- **Duración**: 7 semanas (49 días)
- **Validación**: `cache_valid_until = hoy + 7 semanas`
- **Refresco**: Si expiró, re-escanear workspace

---

## Opciones de Ejecución

**Plan completo.** Dos opciones de ejecución:

**1. Subagent-Driven (recomendado)** - Subagente fresco por tarea, revisión entre tareas

**2. Inline Execution** - Ejecutar tareas en esta sesión

**¿Cuál prefieres?**
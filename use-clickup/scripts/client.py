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
                
            except requests.exceptions.RequestException:
                if intento == self.MAX_RETRIES - 1:
                    raise
                # Backoff exponencial: 1s, 2s, 4s
                import time
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
"""
Configuración centralizada de logging para la aplicación.

Provee un logger configurado que escribe a consola y a un archivo rotativo.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Crear directorio de logs si no existe
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"


def setup_logger(name: str) -> logging.Logger:
    """
    Configura y retorna un logger para el módulo dado.
    
    Args:
        name: Nombre del módulo (usualmente __name__)
        
    Returns:
        logging.Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Si el logger ya tiene handlers, no agregar más (evita logs duplicados)
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Formato del log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler de Consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Handler de Archivo Rotativo (Max 5MB, mantiene 3 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Función helper para obtener un logger configurado.
    
    Alias para setup_logger para uso más semántico.
    """
    return setup_logger(name)

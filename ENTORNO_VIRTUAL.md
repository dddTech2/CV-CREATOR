# 🔧 RECORDATORIO DE ENTORNO VIRTUAL

**IMPORTANTE:** Todos los comandos de Python deben ejecutarse dentro del entorno virtual.

## Activar entorno virtual:

```bash
# Linux/Mac
cd cv-app
source venv/bin/activate

# Windows
cd cv-app
venv\Scripts\activate
```

## Verificar que estás en el entorno virtual:
```bash
which python  # Debe mostrar: .../cv-app/venv/bin/python
```

## Comandos comunes:

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar tests
pytest tests/ -v

# Ejecutar app
streamlit run app.py

# Linting
ruff check .

# Desactivar entorno
deactivate
```

## ⚠️ NUNCA ejecutar comandos Python fuera del venv:
- ❌ `python3 script.py`  (sin venv activado)
- ✅ `source venv/bin/activate && python script.py`

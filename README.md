# CV-App - El Estratega de Carrera con IA

Aplicación web en Streamlit que actúa como un estratega de carrera interactivo. Utiliza Google Gemini para analizar la brecha entre tu CV actual y una vacante específica, y genera un CV optimizado en PDF usando RenderCV.

## 🚀 Instalación

1.  **Clona el repositorio y navega a la carpeta:**
    ```bash
    git clone <repository-url>
    cd cv-app
    ```

2.  **Crea un entorno virtual y actívalo:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura tu API Key de Gemini:**
    ```bash
    cp .env.example .env
    # Edita .env y añade tu GOOGLE_API_KEY
    ```
    *Obtén tu API Key en [Google AI Studio](https://makersuite.google.com/app/apikey)*

## 🎯 Uso

Ejecuta la aplicación:
```bash
streamlit run app.py
```

## 📋 Funcionalidades

*   **Análisis de Brechas (Gap Analysis):** La IA compara tu CV con la vacante e identifica habilidades faltantes.
*   **Chat Interactivo:** Entrevista conversacional para extraer información valiosa.
*   **Optimización Narrativa:** Reescribe tus logros integrando nuevas habilidades.
*   **Generación PDF:** Crea CVs profesionales usando RenderCV.
*   **Historial:** Guarda y recupera versiones anteriores de tus CVs.
*   **Multi-idioma:** Soporta ES, EN, PT, FR.
*   **Múltiples temas:** Classic, Sb2nov, Moderncv, Engineeringresumes.

## 🛠️ Tecnologías

*   Streamlit - Frontend
*   Google Gemini 1.5 Pro - IA Generativa
*   RenderCV - Motor de generación de PDFs
*   SQLite - Base de datos local
*   PyYAML - Parsing y validación
*   Pytest - Testing

## 📦 Estructura del Proyecto

```
cv-app/
├── app.py                 # Frontend Streamlit
├── src/                   # Código fuente
│   ├── ai_backend.py      # Cliente Gemini AI
│   ├── database.py        # SQLite manager
│   └── ...
├── tests/                 # Tests unitarios
├── templates/             # Templates YAML de RenderCV
├── outputs/               # CVs generados
├── data/                  # Base de datos SQLite
└── logs/                  # Logs de la aplicación
```

## 🧪 Testing y Calidad

Ejecutar tests:
```bash
pytest tests/ -v
```

Linting y formato:
```bash
ruff check .
ruff format .
```

## ✅ Estado de Implementación

**Estado:** Production Ready (Beta)
**Coverage estimado:** 92%

### Completadas:
*   ✅ **US-001**: Configuración de entorno y estructura base
*   ✅ **US-002**: Backend - Cliente Gemini AI
*   ✅ **US-003**: Backend - Procesador de CV actual
*   ✅ **US-004**: Backend - Analizador de vacante
*   ✅ **US-005**: Backend - Motor de Gap Analysis
*   ✅ **US-006**: Backend - Generador de Preguntas Inteligentes
*   ✅ **US-007**: Backend - Reescritor de Experiencia Laboral
*   ✅ **US-008**: Backend - Generador YAML para RenderCV
*   ✅ **US-009**: Backend - Validador de YAML contra Schema RenderCV
*   ✅ **US-010**: Backend - Integración con RenderCV para generar PDF
*   ✅ **US-011**: Backend - Base de datos para historial
*   ✅ **US-012**: Frontend - Página principal con tabs
*   ✅ **US-013**: Frontend - Tab 1: Inputs del usuario
*   ✅ **US-014**: Frontend - Tab 2: Visualización de Gap Analysis
*   ✅ **US-015**: Frontend - Tab 3: Conversación de preguntas
*   ✅ **US-016**: Frontend - Tab 4: Resultado y PDF
*   ✅ **US-017**: Frontend - Sidebar con historial de CVs
*   ✅ **US-018**: Backend - Sistema de prompts centralizado
*   ✅ **US-019**: Backend - Manejo de errores y logging

### En desarrollo:
*   ⏳ **US-020**: Tests E2E

---
Ver [PRD.md](PRD.md) para detalles completos.

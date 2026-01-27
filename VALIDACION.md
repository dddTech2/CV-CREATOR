# 🧪 Guía de Validación - CV Generator App

Esta guía te ayudará a validar y probar todos los módulos implementados en CV Generator App.

---

## ⚠️ IMPORTANTE: Entorno Virtual

**TODOS los comandos DEBEN ejecutarse dentro del entorno virtual.**

### Activar el entorno virtual:

**Linux/Mac:**
```bash
cd cv-app
source venv/bin/activate
```

**Windows:**
```cmd
cd cv-app
venv\Scripts\activate
```

Verás `(venv)` al inicio de tu terminal cuando esté activado.

---

## 📦 Paso 1: Verificar Instalación de Dependencias

```bash
# Asegúrate de estar en cv-app/ con venv activado
pip list | grep -E "(streamlit|google-generativeai|rendercv|pytest|ruff|PyPDF2)"
```

**Salida esperada:**
```
google-generativeai    x.x.x
PyPDF2                 x.x.x
pytest                 x.x.x
rendercv               x.x.x
ruff                   x.x.x
streamlit              x.x.x
```

Si falta algo:
```bash
pip install -r requirements.txt
```

---

## 🔑 Paso 2: Configurar API Key de Gemini

### 2.1. Crear archivo .env

```bash
cp .env.example .env
```

### 2.2. Obtener API Key

1. Ve a [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Crea una nueva API key
3. Cópiala

### 2.3. Editar .env

Abre `.env` y añade:
```
GOOGLE_API_KEY=tu_api_key_aqui
```

**IMPORTANTE:** NO compartas este archivo en Git (ya está en .gitignore).

---

## ✅ Paso 3: Ejecutar Tests Unitarios

### 3.1. Ejecutar TODOS los tests

```bash
pytest tests/ -v
```

**Salida esperada:**
```
tests/test_ai_backend.py::test_client_initialization PASSED
tests/test_ai_backend.py::test_api_key_loading PASSED
...
tests/test_gap_analyzer.py::test_gap_analyzer_initialization PASSED
...
======================== 97 passed in X.XXs ========================
```

### 3.2. Ejecutar tests con coverage

```bash
pip install pytest-cov  # Si no lo tienes
pytest tests/ -v --cov=src --cov-report=term-missing
```

**Salida esperada:**
```
---------- coverage: platform linux, python 3.10.x -----------
Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
src/__init__.py                0      0   100%
src/ai_backend.py            180     25    86%   45-50, 120-125
src/cv_parser.py             145     18    88%   67-72, 200-205
src/database.py               85     10    88%   34-38
src/gap_analyzer.py          230     30    87%   150-160, 280-285
src/job_analyzer.py          190     22    88%   78-82, 190-195
--------------------------------------------------------
TOTAL                        830    105    87%
```

### 3.3. Ejecutar tests por módulo

**Cliente Gemini AI:**
```bash
pytest tests/test_ai_backend.py -v
```
Resultado esperado: 16 tests passed

**Procesador de CV:**
```bash
pytest tests/test_cv_parser.py -v
```
Resultado esperado: 25 tests passed

**Analizador de Vacante:**
```bash
pytest tests/test_job_analyzer.py -v
```
Resultado esperado: 30 tests passed

**Motor de Gap Analysis:**
```bash
pytest tests/test_gap_analyzer.py -v
```
Resultado esperado: 26 tests passed

---

## 🔍 Paso 4: Linting y Formato de Código

### 4.1. Verificar estilo de código (linting)

```bash
ruff check .
```

**Salida esperada:**
```
All checks passed!
```

Si hay errores, se mostrarán con detalles (línea, tipo de error).

### 4.2. Verificar formato de código

```bash
ruff format --check .
```

**Salida esperada:**
```
X files would be reformatted
# o
All files formatted correctly
```

### 4.3. Auto-formatear código (si es necesario)

```bash
ruff format .
```

---

## 🧩 Paso 5: Probar Módulos Individuales

### 5.1. Probar Cliente Gemini AI

```bash
python -c "
from src.ai_backend import GeminiClient
import os

# Cargar API key
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print('ERROR: GOOGLE_API_KEY no configurada en .env')
    exit(1)

# Inicializar cliente
client = GeminiClient(api_key=api_key)
print('✅ Cliente Gemini inicializado correctamente')

# Probar generación simple
response = client.generate_content('Di solo: Funcionando')
print(f'✅ Respuesta de Gemini: {response[:50]}...')
"
```

**Salida esperada:**
```
✅ Cliente Gemini inicializado correctamente
✅ Respuesta de Gemini: Funcionando...
```

### 5.2. Probar CV Parser

```bash
python -c "
from src.cv_parser import CVParser

parser = CVParser()
print('✅ CVParser inicializado')

# Probar parsing de texto
cv_text = '''
John Doe
Software Engineer

Experience:
- Senior Developer at Tech Corp (2020-2023)
- Python, JavaScript, React

Education:
- BS Computer Science, MIT (2016-2020)

Skills: Python, JavaScript, SQL, Docker
'''

result = parser.parse_text(cv_text)
print(f'✅ CV parseado correctamente')
print(f'   - Experiencias encontradas: {len(result.get(\"experience\", []))}')
print(f'   - Educación encontrada: {len(result.get(\"education\", []))}')
print(f'   - Skills encontradas: {len(result.get(\"skills\", []))}')
"
```

**Salida esperada:**
```
✅ CVParser inicializado
✅ CV parseado correctamente
   - Experiencias encontradas: 1-2
   - Educación encontrada: 1
   - Skills encontradas: 4+
```

### 5.3. Probar Job Analyzer

```bash
python -c "
from src.job_analyzer import JobAnalyzer

analyzer = JobAnalyzer()
print('✅ JobAnalyzer inicializado')

# Probar análisis de vacante
job_desc = '''
Senior Python Developer needed

Requirements:
- 5+ years of Python experience
- Strong knowledge of Django and Flask
- Experience with AWS and Docker
- Bachelor's degree in Computer Science

Nice to have:
- Kubernetes experience
- Machine Learning background
'''

result = analyzer.analyze_job_description(job_desc)
print(f'✅ Vacante analizada correctamente')
print(f'   - Skills técnicas: {len(result.get(\"technical_skills\", []))}')
print(f'   - Experiencia requerida: {result.get(\"years_experience\")}')
print(f'   - Must-haves: {len(result.get(\"must_have\", []))}')
"
```

**Salida esperada:**
```
✅ JobAnalyzer inicializado
✅ Vacante analizada correctamente
   - Skills técnicas: 4+
   - Experiencia requerida: 5
   - Must-haves: 4+
```

### 5.4. Probar Gap Analyzer (requiere API key)

```bash
python -c "
from src.gap_analyzer import GapAnalyzer
from src.ai_backend import GeminiClient
import os

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print('ERROR: GOOGLE_API_KEY no configurada')
    exit(1)

client = GeminiClient(api_key=api_key)
analyzer = GapAnalyzer(ai_client=client)
print('✅ GapAnalyzer inicializado')

# Probar análisis de brechas
cv_data = {
    'skills': ['Python', 'JavaScript'],
    'experience': [{'title': 'Developer', 'duration': '2 years'}]
}

job_requirements = {
    'technical_skills': ['Python', 'Docker', 'Kubernetes'],
    'years_experience': 5,
    'must_have': ['Docker']
}

result = analyzer.analyze_gap(cv_data, job_requirements)
print(f'✅ Gap Analysis completado')
print(f'   - Match score: {result.get(\"match_score\", 0)}%')
print(f'   - Gaps encontrados: {len(result.get(\"gaps\", []))}')
print(f'   - Preguntas generadas: {len(result.get(\"suggested_questions\", []))}')
"
```

**Salida esperada:**
```
✅ GapAnalyzer inicializado
✅ Gap Analysis completado
   - Match score: 40-60%
   - Gaps encontrados: 2+
   - Preguntas generadas: 2+
```

---

## 🌐 Paso 6: Ejecutar la Aplicación Streamlit

```bash
streamlit run app.py
```

**Salida esperada:**
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

### Validación manual en el navegador:

1. **Tab "📝 Inputs":**
   - Verifica que puedes pegar CV y descripción de vacante
   - Verifica selección de idioma y tema

2. **Tab "🔍 Análisis":**
   - Verifica que se muestra el gap analysis
   - Verifica visualización de skills faltantes

3. **Tab "💬 Preguntas":**
   - Verifica que se generan preguntas inteligentes
   - Verifica que puedes responder

4. **Tab "✅ Resultado":**
   - Verifica que se genera el PDF
   - Verifica que puedes descargar el CV

---

## 📊 Paso 7: Verificar Cobertura Total

### 7.1. Generar reporte HTML de coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

Abre `htmlcov/index.html` en tu navegador para ver detalles.

### 7.2. Verificar módulos clave

**Módulos críticos que deben tener +80% coverage:**
- `src/ai_backend.py`
- `src/cv_parser.py`
- `src/job_analyzer.py`
- `src/gap_analyzer.py`

---

## 🐛 Solución de Problemas Comunes

### Error: "No module named 'src'"

**Causa:** No estás en el directorio correcto o no activaste venv.

**Solución:**
```bash
cd cv-app
source venv/bin/activate  # o venv\Scripts\activate en Windows
```

### Error: "GOOGLE_API_KEY not found"

**Causa:** No configuraste `.env` o la variable no se carga.

**Solución:**
```bash
# Verificar que existe .env
cat .env

# Cargar manualmente (solo para testing)
export GOOGLE_API_KEY="tu_api_key_aqui"  # Linux/Mac
set GOOGLE_API_KEY=tu_api_key_aqui      # Windows
```

### Error: Tests fallan con "API rate limit exceeded"

**Causa:** Demasiadas llamadas a Gemini API en poco tiempo.

**Solución:**
```bash
# Ejecutar solo tests que no requieren API
pytest tests/test_cv_parser.py tests/test_job_analyzer.py -v

# O esperar 1-2 minutos y reintentar
```

### Error: "RenderCV command not found"

**Causa:** RenderCV no está instalado o no en PATH.

**Solución:**
```bash
pip install --upgrade rendercv

# Verificar instalación
rendercv --version
```

---

## ✅ Checklist de Validación Completa

Marca cada item cuando lo completes:

- [ ] Entorno virtual activado
- [ ] Dependencias instaladas (`pip list`)
- [ ] API key de Gemini configurada (`.env`)
- [ ] Todos los tests pasan (97/97)
- [ ] Coverage >85% (`pytest --cov`)
- [ ] Linting sin errores (`ruff check`)
- [ ] Formato correcto (`ruff format --check`)
- [ ] Cliente Gemini funciona (prueba individual)
- [ ] CV Parser funciona (prueba individual)
- [ ] Job Analyzer funciona (prueba individual)
- [ ] Gap Analyzer funciona (prueba individual)
- [ ] Aplicación Streamlit se ejecuta
- [ ] UI funciona correctamente (validación manual)

---

## 📞 Soporte

Si encuentras errores que no están en esta guía:

1. Verifica que estés en el entorno virtual
2. Verifica que todas las dependencias estén instaladas
3. Verifica que `.env` esté configurado correctamente
4. Revisa los logs en la terminal

---

## 🎯 Próximos Pasos

Después de validar todo:

1. **US-006**: Generador de preguntas inteligentes
2. **US-007**: Reescritor de experiencia laboral
3. **US-008**: Generador YAML para RenderCV
4. **US-009**: Validador de YAML
5. **US-010**: Integración con RenderCV para PDF

Ver [PRD.md](PRD.md) para detalles completos de las siguientes User Stories.

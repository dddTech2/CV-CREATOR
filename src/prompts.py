"""
Sistema centralizado de prompts para Gemini AI.

Este módulo gestiona todos los templates de prompts utilizados en la aplicación,
facilitando su mantenimiento, internacionalización y testing.
"""
from typing import Optional, List


class PromptTemplates:
    """Templates de prompts para diferentes tareas."""

    # 1. Análisis de Vacante
    JOB_ANALYSIS = """Analiza la siguiente descripción de vacante y extrae información estructurada.

Descripción de la vacante:
```
{job_description}
```

Extrae la siguiente información en formato JSON estricto:

{{
    "technical_skills": [
        {{"name": "Python", "priority": "must_have", "context": "Desarrollo backend"}},
        {{"name": "Docker", "priority": "nice_to_have", "context": "Containerización"}}
    ],
    "soft_skills": [
        {{"name": "Liderazgo", "priority": "must_have", "context": "Liderar equipo de 5 personas"}},
        {{"name": "Comunicación", "priority": "must_have", "context": "Comunicación con stakeholders"}}
    ],
    "languages": [
        {{"name": "Inglés", "priority": "must_have", "context": "Nivel avanzado"}},
        {{"name": "Español", "priority": "nice_to_have", "context": "Deseable"}}
    ],
    "certifications": [
        {{"name": "AWS Certified", "priority": "nice_to_have", "context": "Certificación en cloud"}}
    ],
    "experience_years": 5,
    "education_level": "Licenciatura en Ingeniería o afín",
    "responsibilities": [
        "Desarrollar APIs REST",
        "Mentorear desarrolladores junior"
    ],
    "benefits": [
        "Trabajo remoto",
        "Seguro médico"
    ]
}}

IMPORTANTE:
- "priority" debe ser: "must_have", "nice_to_have", o "preferred"
- Si no se especifica prioridad, infiere del contexto ("requerido" = must_have, "deseable" = nice_to_have)
- Si no hay información para un campo, usa null o array vacío
- Retorna SOLO el JSON, sin texto adicional
"""

    # 2. Generación de Preguntas
    QUESTION_GENERATION = """Eres un estratega de carrera experto. Analiza las siguientes brechas entre el CV del candidato y la vacante, y genera preguntas estratégicas {language} para obtener información que ayude a llenar esos gaps.

**CV del candidato:**
{cv_summary}

**Requisitos de la vacante:**
{job_summary}

**Brechas identificadas:**
{gaps_summary}

**Instrucciones:**
1. Genera {max_questions} preguntas específicas y contextuales (NO genéricas)
2. Prioriza gaps de requisitos "must-have"
3. Cada pregunta debe ayudar a entender si el candidato tiene experiencia con la habilidad faltante
4. Si el candidato confirma tener la habilidad, pide un ejemplo concreto
5. Formato: "La vacante requiere X pero no lo veo en tu CV. ¿Tienes experiencia con X? Si es así, describe brevemente cómo lo has usado."

**Genera las preguntas numeradas (1. 2. 3. ...):**"""

    # 3. Clasificación de Respuestas del Usuario
    USER_RESPONSE_CLASSIFIER = """Eres un experto analizando respuestas de usuarios sobre su experiencia. Tu tarea es CLASIFICAR cada respuesta en categorías específicas.

**Skill preguntada:** {skill_name}

**Respuesta del usuario:**
{user_answer}

**Empresas conocidas del CV del usuario:**
{known_companies}

**INSTRUCCIONES:**
Analiza la respuesta y clasifica en UNA de estas categorías:

1. **EXPERIENCIA_LABORAL:** Si menciona que usó la skill en una empresa/trabajo
   - Indicadores: "en [nombre empresa]", "en mi trabajo en", "cuando trabajaba en", "en la empresa"
   - Extrae: nombre de la empresa mencionada

2. **PROYECTO_ACADEMICO:** Si menciona universidad, curso, tesis, proyecto académico
   - Indicadores: "universidad", "proyecto de la u", "en un curso", "tesis", "proyecto académico"
   - Extrae: nombre del proyecto (si lo menciona) o usa genérico

3. **PROYECTO_PERSONAL:** Si menciona proyecto personal, freelance, independiente
   - Indicadores: "proyecto personal", "freelance", "por mi cuenta", "independiente", "side project"
   - Extrae: nombre del proyecto (si lo menciona) o usa genérico

4. **NO_APLICABLE:** Si dice que NO tiene experiencia o respuesta muy vaga
   - Indicadores: "no tengo experiencia", "no lo he usado", "no sé", respuestas de 1-2 palabras

**FORMATO DE SALIDA (JSON estricto):**
{{
    "classification": "EXPERIENCIA_LABORAL" | "PROYECTO_ACADEMICO" | "PROYECTO_PERSONAL" | "NO_APLICABLE",
    "company_name": "nombre empresa" o null,
    "project_name": "nombre proyecto extraído del contexto" o "Proyecto con {skill_name}" si es genérico,
    "description": "descripción limpia de lo que hizo con la skill",
    "confidence": "high" | "medium" | "low"
}}

**EJEMPLOS:**

Input: "Spark: Sí en un proyecto en renovar financiera, donde generé un scraping para bajar información de millones de llamadas de 5 años"
Output:
{{
    "classification": "EXPERIENCIA_LABORAL",
    "company_name": "Renovar Financiera",
    "project_name": null,
    "description": "Generé un scraping para bajar información de millones de llamadas de 5 años y procesamiento con Spark",
    "confidence": "high"
}}

Input: "Django: si para un proyecto de la Universidad"
Output:
{{
    "classification": "PROYECTO_ACADEMICO",
    "company_name": null,
    "project_name": "Proyecto Académico con Django",
    "description": "Proyecto universitario utilizando Django",
    "confidence": "medium"
}}

Input: "Django: sí para un proyecto de la Universidad, hice un marketplace"
Output:
{{
    "classification": "PROYECTO_ACADEMICO",
    "company_name": null,
    "project_name": "Plataforma Marketplace",
    "description": "Desarrollé una plataforma de marketplace utilizando Django",
    "confidence": "high"
}}

Input: "React: Lo usé en un proyecto personal de finanzas"
Output:
{{
    "classification": "PROYECTO_PERSONAL",
    "company_name": null,
    "project_name": "Aplicación de Finanzas Personales",
    "description": "Proyecto personal de aplicación de finanzas con React",
    "confidence": "high"
}}

Input: "Docker: no tengo experiencia"
Output:
{{
    "classification": "NO_APLICABLE",
    "company_name": null,
    "project_name": null,
    "description": null,
    "confidence": "high"
}}

**Ahora clasifica esta respuesta (SOLO JSON, sin explicaciones):**
"""

    # 4. Generación de Entrada de Proyecto
    PROJECT_ENTRY_GENERATION = """Eres un experto en redacción de CVs. Genera una entrada profesional para la sección de PROYECTOS basado en la información del usuario.

**Nombre del proyecto:** {project_name}
**Tipo:** {project_type} (académico, personal, freelance)
**Skill principal:** {main_skill}
**Descripción del usuario:**
{user_description}

**INSTRUCCIONES:**
1. Genera un resumen de 1 línea del proyecto (campo "summary")
2. Genera 2-4 bullet points de highlights en {language}
3. Los highlights deben:
   - Empezar con verbos de acción (Desarrollé, Implementé, Diseñé, Construí)
   - Ser específicos y técnicos
   - Mencionar la skill principal ({main_skill})
   - Incluir detalles del contexto mencionado por el usuario

**FORMATO DE SALIDA (JSON):**
{{
    "summary": "Resumen de 1 línea del proyecto",
    "highlights": [
        "Highlight 1 con verbo de acción y detalles técnicos",
        "Highlight 2 mencionando tecnologías específicas",
        "Highlight 3 con resultados o características implementadas"
    ]
}}

**EJEMPLO:**

Input:
- project_name: "Plataforma Marketplace"
- project_type: "académico"
- main_skill: "Django"
- user_description: "Proyecto de universidad, hice un marketplace"

Output:
{{
    "summary": "Plataforma de e-commerce desarrollada como proyecto académico",
    "highlights": [
        "Desarrollé una plataforma de marketplace integral utilizando Django, gestionando la arquitectura del backend y la integración de bases de datos",
        "Implementé sistema de autenticación de usuarios, gestión de productos y carrito de compras con Django ORM",
        "Diseñé la API REST para la comunicación entre frontend y backend garantizando una navegación fluida y escalable"
    ]
}}

**Ahora genera el JSON para este proyecto (SOLO JSON, sin explicaciones):**
"""

    # 5. Enriquecimiento de Experiencia con Respuestas del Usuario
    EXPERIENCE_ENRICHMENT = """Eres un experto en redacción de CVs. Tu tarea es ENRIQUECER una experiencia laboral existente integrando nuevas habilidades que el usuario confirmó tener EN ESTA EMPRESA ESPECÍFICA.

**Experiencia laboral actual:**
Cargo: {position}
Empresa: {company}
Período: {duration}
Logros actuales:
{current_highlights}

**Nuevas habilidades confirmadas por el usuario PARA ESTA EMPRESA:**
{user_confirmed_skills}

**Palabras clave importantes (ATS) de la vacante:**
{job_keywords}

**INSTRUCCIONES CRÍTICAS - LEE CUIDADOSAMENTE:**
1. MANTÉN todos los logros actuales que sean relevantes
2. SOLO integra las habilidades que el usuario EXPLÍCITAMENTE confirmó usar EN ESTA EMPRESA ({company})
3. **PROHIBIDO ABSOLUTAMENTE:** NO inventes que el usuario usó una tecnología en esta empresa si NO lo mencionó explícitamente para esta empresa
4. Si el usuario mencionó usar una skill en otra empresa o en un proyecto, NO la agregues aquí
5. REESCRIBE los bullets existentes para hacerlos más impactantes y ATS-friendly
6. USA verbos de acción potentes (Diseñé, Implementé, Desarrollé, Optimicé)
7. INCLUYE métricas y números cuando sea posible
8. RETORNA 4-6 bullet points en total
9. TRADUCE todo al idioma: {language}

**EJEMPLO DE LO QUE NO DEBES HACER:**
❌ MAL: Usuario dijo "usé Django en un proyecto de universidad" → NO agregues Django a su trabajo en Renovar Financiera
❌ MAL: La vacante requiere Docker → NO agregues Docker si el usuario NO mencionó usarlo en esta empresa

**EJEMPLO CORRECTO:**
✅ BIEN: Usuario dijo "usé Spark en Renovar Financiera para procesar millones de llamadas" → SÍ agrégalo porque lo confirmó para esta empresa específica

**Ahora genera los bullet points enriquecidos en {language} (SOLO los bullets, sin numeración ni introducción):**
"""

    # 4. Reescritura de Experiencia
    EXPERIENCE_REWRITE = """Eres un experto en redacción de CVs optimizados para ATS (Applicant Tracking Systems) y reclutadores técnicos.

**Tarea:** Reescribe la siguiente experiencia laboral integrando las nuevas habilidades de forma natural en la narrativa.

**Experiencia original:**
{title} en {company}
{original_description}

**Habilidades a integrar:** {skills_to_add}

**Palabras clave importantes (ATS):** {job_keywords}

**INSTRUCCIONES CRÍTICAS:**
1. Reescribe {language} en 3-5 bullet points impactantes
2. INTEGRA las nuevas habilidades de forma natural en proyectos/logros reales (NO simplemente las listes)
3. COMIENZA cada bullet con un VERBO DE ACCIÓN potente (Desarrollé, Implementé, Optimicé, Lideré, Diseñé, Construí)
4. INCLUYE MÉTRICAS/NÚMEROS cuando sea posible (ej: "procesando 100K requests/día", "mejorando performance en 40%", "reduciendo costos en $10K")
5. INCORPORA palabras clave ATS de forma orgánica en el contexto de logros
6. NO inventes información nueva, EXPANDE y REFORMULA lo que ya está en la descripción original
7. Haz los logros más ESPECÍFICOS y CUANTIFICABLES

**EJEMPLOS DE BUENOS BULLET POINTS:**

❌ MAL: "Trabajé con Python y Django"
✅ BIEN: "Desarrollé 5 APIs REST usando Django y Django REST Framework, manejando 50K+ requests diarios con 99.9% uptime"

❌ MAL: "Usé Spark para procesar datos"
✅ BIEN: "Implementé pipelines ETL con Apache Spark (PySpark) para procesar 2TB de datos mensuales, reduciendo tiempo de procesamiento de 8h a 45min"

❌ MAL: "Lideré un equipo"
✅ BIEN: "Lideré equipo de 3 desarrolladores junior, estableciendo code reviews y mejorando la velocidad de entrega en 40%"

❌ MAL: "Hice deployment de aplicaciones"
✅ BIEN: "Automaticé deployment de 10+ microservicios usando Docker, Kubernetes y CI/CD (GitLab), reduciendo errores en producción en 60%"

❌ MAL: "Optimicé queries de base de datos"
✅ BIEN: "Optimicé queries SQL complejas en PostgreSQL, mejorando el tiempo de respuesta de reportes críticos de 30s a 2s"

**Ahora reescribe la experiencia (RETORNA SOLO LOS BULLET POINTS, sin numeración ni introducción):**
"""

    # 4. Generación de Resumen Profesional
    SUMMARY_GENERATION = """Eres un experto en redacción de CVs. Genera un resumen profesional ENFOCADO específicamente al cargo que el candidato está aplicando.

**Descripción de la vacante:**
```
{job_description}
```

**Perfil del candidato:**
- Educación: {education_summary}
- Experiencia clave: {experience_summary}
- Habilidades técnicas principales: {skills_summary}
- Años de experiencia: {years_experience}

**Requisitos must-have del cargo:**
{must_have_skills}

**INSTRUCCIONES:**
1. Escribe un resumen de 3-5 oraciones en {language}
2. ENFOCA el resumen al cargo específico (menciona el tipo de rol: ej. "Desarrollador Python", "Ingeniero de Datos")
3. DESTACA las habilidades must-have que el candidato TIENE
4. Incluye años de experiencia si es relevante
5. Menciona tecnologías clave que coinciden con la vacante (ej: Django, Spark, Python)
6. Hazlo impactante pero profesional, sin exageraciones
7. NO uses lenguaje genérico como "profesional altamente motivado"
8. ENFÓCATE en el valor que el candidato aporta para ESE cargo específico

**EJEMPLOS DE BUENOS RESUMENES:**

Ejemplo 1 (para Desarrollador Python con Django/Spark):
"Desarrollador Python con 5 años de experiencia construyendo aplicaciones web escalables y pipelines de procesamiento de datos. Sólida experiencia en Django para desarrollo de APIs REST y Apache Spark para procesamiento distribuido de big data. Experto en optimización de bases de datos relacionales (PostgreSQL, MySQL) y diseño de arquitecturas cloud-native. Busco aplicar mis habilidades en desarrollo backend para resolver problemas de negocio complejos mediante soluciones técnicas robustas."

Ejemplo 2 (para Data Scientist con ML):
"Científico de Datos con 4 años desarrollando modelos de Machine Learning end-to-end, desde análisis exploratorio hasta deployment en producción. Experiencia práctica con Python (Scikit-learn, TensorFlow, Pandas) y SQL para análisis de datasets complejos. Historial comprobado creando modelos predictivos que mejoraron métricas de negocio en 30%+. Apasionado por transformar datos en insights accionables mediante visualizaciones interactivas (Power BI, Plotly)."

Ejemplo 3 (para Full Stack Developer):
"Ingeniero Full Stack con 6 años construyendo aplicaciones web modernas usando React y Node.js. Expertise en arquitectura de microservicios, integración de APIs REST/GraphQL y databases tanto SQL como NoSQL. Comprobada capacidad liderando equipos ágiles y entregando features de alto impacto en plazos ajustados. Busco contribuir con mi experiencia técnica y visión de producto en un equipo innovador."

**Ahora genera el resumen profesional para este candidato (SOLO el texto del resumen, sin introducción):**
"""

    # 5. Priorización de Habilidades según Cargo
    SKILL_PRIORITIZATION = """Eres un experto en CVs optimizados para ATS. Reorganiza y prioriza las habilidades según el cargo específico.

**Habilidades actuales del CV:**
{current_skills}

**Habilidades must-have de la vacante:**
{must_have_skills}

**Cargo al que aplica:**
{job_title}

**INSTRUCCIONES:**
1. Reorganiza las habilidades en categorías lógicas
2. PRIORIZA las categorías que contengan must-haves del cargo
3. Dentro de cada categoría, lista primero las skills must-have
4. Usa nombres de categorías específicos al cargo (ej: "Desarrollo Web" en lugar de genérico "Frameworks")
5. Retorna SOLO el JSON en este formato:

[
  {{
    "label": "Nombre de categoría (priorizada según cargo)",
    "details": "skill1, skill2, skill3, ..."
  }}
]

**EJEMPLO para Desarrollador Python:**
[
  {{
    "label": "Desarrollo Web Backend",
    "details": "Django, Flask, FastAPI, Django REST Framework"
  }},
  {{
    "label": "Big Data & Processing",
    "details": "Apache Spark, PySpark, Pandas, NumPy"
  }},
  {{
    "label": "Bases de Datos",
    "details": "PostgreSQL, MySQL, MongoDB, Redis"
  }},
  {{
    "label": "Cloud & DevOps",
    "details": "Docker, Git, GCP, AWS, DigitalOcean"
  }},
  {{
    "label": "Machine Learning",
    "details": "Scikit-learn, TensorFlow, Keras, NLTK"
  }},
  {{
    "label": "Idiomas",
    "details": "Español (Nativo), Inglés (B1)"
  }}
]

**IMPORTANTE:** Siempre mantén la categoría "Idiomas" al FINAL de la lista.

**Genera el JSON (solo el array, sin explicaciones):**
"""

    # 6. Estructuración de Datos (para YAML)
    DATA_STRUCTURING = """Analiza el siguiente texto de CV y extrae la información en formato JSON estricto para RenderCV.

CV Text:
{cv_text}

**IDIOMA DE SALIDA:** {language}

**INSTRUCCIÓN CRÍTICA DE TRADUCCIÓN:**
- Si el CV original está en ESPAÑOL y el idioma de salida es "English": TRADUCE TODO al inglés (cargos, descripciones, instituciones, skills, highlights)
- Si el CV original está en INGLÉS y el idioma de salida es "Español": TRADUCE TODO al español
- Si ambos coinciden: mantén el idioma original
- EJEMPLOS de traducción:
  * "Ingeniero de Sistemas" → "Systems Engineer"
  * "Científico de datos" → "Data Scientist"
  * "Marzo 2025" → "March 2025" (en fechas solo traduce el mes en descriptions, no en campos de fecha)
  * "Desarrollé modelos..." → "Developed models..."

JSON Schema requerido - DEBES COMPLETAR TODAS LAS SECCIONES:
{{
    "name": "Nombre completo",
    "email": "email (null si no hay)",
    "phone": "telefono con código de país (ej: +573059117385)",
    "location": "Ciudad, País (ej: Bogotá D.C., Colombia)",
    "linkedin": "username de LinkedIn (null si no hay)",
    "github": "username de GitHub (null si no hay)",
    "website": "url del sitio web personal (null si no hay)",
    "summary": "Resumen profesional del CV (null si no hay)",
    "experience": [
        {{
            "company": "Nombre de la empresa",
            "position": "Cargo/Título del puesto",
            "start_date": "YYYY-MM (o YYYY)",
            "end_date": "YYYY-MM (o YYYY o 'present')",
            "location": "Ciudad, País",
            "highlights": [
                "Logro o responsabilidad 1 usando verbo de acción",
                "Logro o responsabilidad 2 con métricas si es posible",
                "Logro o responsabilidad 3"
            ]
        }}
    ],
    "education": [
        {{
            "institution": "Universidad o institución educativa",
            "degree": "Título obtenido (ej: Ingeniería de Sistemas)",
            "area": "Campo de estudio",
            "start_date": "YYYY-MM (o YYYY)",
            "end_date": "YYYY-MM (o YYYY o 'present')",
            "location": "Ciudad, País"
        }}
    ],
    "skills": [
        {{
            "label": "Categoría de habilidad (ej: Lenguajes de Programación, Frameworks Web, Bases de Datos, Cloud & DevOps)",
            "details": "Lista de skills separadas por comas (ej: Python, Java, JavaScript)"
        }}
    ]
}}

EJEMPLO DE SALIDA ESPERADA (CV en español con formato típico latinoamericano):
{{
    "name": "Davis Arturo Daza Sierra",
    "email": "arturodazaemp@gmail.com",
    "phone": "+573059117385",
    "location": "Bogotá D.C., Colombia",
    "linkedin": null,
    "github": "Arturo-daza",
    "website": null,
    "summary": null,
    "experience": [
        {{
            "company": "Renovar Financiera",
            "position": "Científico de datos",
            "start_date": "2025-03",
            "end_date": "present",
            "location": "Bogotá D.C., Colombia",
            "highlights": [
                "Diseñé e implementé modelos de clasificación (Regresión Logística, Gradient Boosting) para predecir probabilidad de incumplimiento, optimizando recursos y mejorando efectividad de cartera en 20%",
                "Apliqué algoritmos de clustering (K-Means) para segmentar base de clientes, permitiendo diseño de estrategias de cobranza personalizadas",
                "Desarrollé modelos predictivos para determinar mejor momento de contacto con clientes, incrementando tasa de contacto efectivo en 32%",
                "Desarrollé scripts de web scraping automatizado con Selenium/BeautifulSoup para recolección de datos de fuentes públicas",
                "Generé dashboards dinámicos en Power BI y Python (Plotly/Dash) para monitoreo en tiempo real de KPIs de cartera"
            ]
        }},
        {{
            "company": "Grupo Consultor 360",
            "position": "Analista de Operaciones",
            "start_date": "2024-02",
            "end_date": "2025-02",
            "location": "Bogotá D.C., Colombia",
            "highlights": [
                "Analicé y optimicé operaciones internas mediante análisis de datos, logrando mejoras del 15% en KPIs clave",
                "Diseñé dashboards interactivos en Looker Studio para visualizar métricas críticas, reduciendo tiempos de análisis en 30%",
                "Automaticé tareas manuales mediante Python y Excel, optimizando flujos de datos y reduciendo tiempos de procesamiento en 25%"
            ]
        }}
    ],
    "education": [
        {{
            "institution": "Fundación Universitaria Konrad Lorenz",
            "degree": "Pregrado",
            "area": "Ingeniería de Sistemas",
            "start_date": null,
            "end_date": "2024-12",
            "location": "Bogotá D.C., Colombia"
        }},
        {{
            "institution": "Fundación Universitaria Konrad Lorenz",
            "degree": "Pregrado",
            "area": "Ingeniería Industrial",
            "start_date": null,
            "end_date": "2023-12",
            "location": "Bogotá D.C., Colombia"
        }}
    ],
    "skills": [
        {{
            "label": "Machine Learning",
            "details": "Clasificación, Regresión Logística, Árboles de Decisión, Gradient Boosting, Clustering (K-Means), Scikit-learn, TensorFlow, Keras"
        }},
        {{
            "label": "Lenguajes de Programación",
            "details": "Python (Pandas, NumPy, Matplotlib, Seaborn, Plotly, FastAPI, Selenium, BeautifulSoup), SQL, Java, JavaScript"
        }},
        {{
            "label": "Bases de Datos",
            "details": "MySQL, SQL Server, MongoDB"
        }},
        {{
            "label": "Visualización de Datos y BI",
            "details": "Power BI, Looker Studio, Excel, Dash"
        }},
        {{
            "label": "Idiomas",
            "details": "Español (Nativo), Inglés (B1)"
        }}
    ]
}}

INSTRUCCIONES CRÍTICAS PARA CVs EN ESPAÑOL:
1. **FECHAS:** Parsea formatos como "Marzo 2025 – Actualmente", "Febrero 2024 – Febrero 2025", "Julio 2023–enero 2024"
   - "Actualmente" o "presente" → "present"
   - "Marzo 2025" → "2025-03"
   - "Julio 2023" → "2023-07"
   - Si solo hay año "2024" → "2024"

2. **EXPERIENCIA:** Extrae TODAS las experiencias laborales del CV
   - Cada bullet con "●" es un highlight
   - Limpia el texto de viñetas y espacios extras
   - Mantén los números y porcentajes (ej: "20%", "32%")

3. **DEGREE:** Usa "Pregrado" para títulos universitarios en español
   - "Bachelor's" o "Bachelor" para CVs en inglés
   - NO uses el nombre específico del título en el campo "degree"
   - El nombre específico va en "area"

4. **HIGHLIGHTS:** Cada bullet debe:
   - Empezar con verbo en pasado (Diseñé, Implementé, Desarrollé)
   - Incluir métricas cuando existan
   - Ser conciso pero completo

5. **SKILLS:** Extrae todas las categorías y habilidades mencionadas
   - Si el CV menciona idiomas, agrégalos como categoría "Idiomas"
   - Formato idiomas: "Español (Nativo), Inglés (B1/B2/C1/etc.)"
   - Incluye TODAS las categorías: técnicas, herramientas, idiomas, etc.

6. Retorna SOLO el JSON válido, sin texto adicional ni explicaciones
"""


class PromptManager:
    """Gestor para construir prompts con validación de variables."""

    @staticmethod
    def get_job_analysis_prompt(job_description: str) -> str:
        """Construye el prompt de análisis de vacante."""
        return PromptTemplates.JOB_ANALYSIS.format(job_description=job_description)

    @staticmethod
    def get_question_generation_prompt(
        gaps_summary: str,
        cv_summary: str,
        job_summary: str,
        max_questions: int,
        language: str = "en español",
    ) -> str:
        """Construye el prompt de generación de preguntas."""
        return PromptTemplates.QUESTION_GENERATION.format(
            gaps_summary=gaps_summary,
            cv_summary=cv_summary,
            job_summary=job_summary,
            max_questions=max_questions,
            language=language,
        )

    @staticmethod
    def get_user_response_classifier_prompt(
        skill_name: str,
        user_answer: str,
        known_companies: list[str]
    ) -> str:
        """Construye el prompt para clasificar respuestas del usuario."""
        companies_text = ", ".join(known_companies) if known_companies else "Ninguna empresa conocida"
        return PromptTemplates.USER_RESPONSE_CLASSIFIER.format(
            skill_name=skill_name,
            user_answer=user_answer,
            known_companies=companies_text
        )

    @staticmethod
    def get_project_entry_generation_prompt(
        project_name: str,
        project_type: str,
        main_skill: str,
        user_description: str,
        language: str = "español"
    ) -> str:
        """Construye el prompt para generar entrada de proyecto."""
        return PromptTemplates.PROJECT_ENTRY_GENERATION.format(
            project_name=project_name,
            project_type=project_type,
            main_skill=main_skill,
            user_description=user_description,
            language=language
        )

    @staticmethod
    def get_experience_enrichment_prompt(
        position: str,
        company: str,
        duration: str,
        current_highlights: str,
        user_confirmed_skills: str,
        job_keywords: list[str],
        language: str = "español"
    ) -> str:
        """Construye el prompt para enriquecer experiencia con respuestas del usuario."""
        return PromptTemplates.EXPERIENCE_ENRICHMENT.format(
            position=position,
            company=company,
            duration=duration,
            current_highlights=current_highlights,
            user_confirmed_skills=user_confirmed_skills,
            job_keywords=", ".join(job_keywords[:10]) if job_keywords else "",
            language=language
        )

    @staticmethod
    def get_experience_rewrite_prompt(
        title: str,
        company: str,
        original_description: str,
        skills_to_add: List[str],
        job_keywords: List[str],
        language: str = "en español",
    ) -> str:
        """Construye el prompt de reescritura de experiencia."""
        return PromptTemplates.EXPERIENCE_REWRITE.format(
            title=title,
            company=company,
            original_description=original_description,
            skills_to_add=", ".join(skills_to_add),
            job_keywords=", ".join(job_keywords[:5]),
            language=language,
        )

    @staticmethod
    def get_summary_generation_prompt(
        job_description: str,
        education_summary: str,
        experience_summary: str,
        skills_summary: str,
        years_experience: str,
        must_have_skills: str,
        language: str = "español"
    ) -> str:
        """Construye el prompt para generar resumen profesional enfocado al cargo."""
        return PromptTemplates.SUMMARY_GENERATION.format(
            job_description=job_description,
            education_summary=education_summary,
            experience_summary=experience_summary,
            skills_summary=skills_summary,
            years_experience=years_experience,
            must_have_skills=must_have_skills,
            language=language
        )

    @staticmethod
    def get_skill_prioritization_prompt(
        current_skills: str,
        must_have_skills: str,
        job_title: str
    ) -> str:
        """Construye el prompt para priorizar habilidades según el cargo."""
        return PromptTemplates.SKILL_PRIORITIZATION.format(
            current_skills=current_skills,
            must_have_skills=must_have_skills,
            job_title=job_title
        )

    @staticmethod
    def get_data_structuring_prompt(cv_text: str, language: str = "Español") -> str:
        """Construye el prompt para estructurar datos del CV con traducción al idioma objetivo."""
        return PromptTemplates.DATA_STRUCTURING.format(
            cv_text=cv_text,
            language=language
        )

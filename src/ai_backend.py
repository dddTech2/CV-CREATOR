"""
Backend de IA: Cliente Gemini y Estratega de Carrera.
"""
import os
import time
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai.types import GenerateContentConfig
from dotenv import load_dotenv

from src.logger import get_logger

# Configurar logger
logger = get_logger(__name__)

# Cargar variables de entorno
load_dotenv()


@dataclass
class GeminiResponse:
    """Respuesta estructurada del modelo Gemini."""

    text: str
    success: bool
    error: Optional[str] = None
    model_used: Optional[str] = None


class GeminiClientError(Exception):
    """Excepción base para errores del cliente Gemini."""

    pass


class GeminiRateLimitError(GeminiClientError):
    """Excepción para errores de rate limit."""

    pass


class GeminiConnectionError(GeminiClientError):
    """Excepción para errores de conexión."""

    pass


class GeminiClient:
    """
    Cliente base para interactuar con Gemini AI usando la nueva API google.genai.

    Maneja conexión, autenticación, rate limits y errores.
    """

    # Configuración de rate limiting
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # segundos
    BACKOFF_MULTIPLIER = 2

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3-flash-preview",
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
    ):
        """
        Inicializa el cliente de Gemini.

        Args:
            api_key: API key de Google. Si no se proporciona, se lee de GOOGLE_API_KEY env var
            model_name: Nombre del modelo a usar (gemini-2.0-flash-thinking-exp-1219 recomendado)
            temperature: Control de aleatoriedad (0.0-1.0)
            max_output_tokens: Máximo de tokens en la respuesta

        Raises:
            GeminiClientError: Si no se encuentra la API key o hay error de configuración
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise GeminiClientError(
                "GOOGLE_API_KEY no encontrada. "
                "Configura la variable de entorno o pasa api_key al constructor."
            )

        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

        # Configurar cliente con nueva API
        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"Cliente Gemini inicializado. Modelo: {model_name}")
        except Exception as e:
            logger.error(f"Error al configurar Gemini: {e}", exc_info=True)
            raise GeminiConnectionError(f"Error al configurar Gemini: {str(e)}")

    def generate(
        self, prompt: str, system_instruction: Optional[str] = None, retry: bool = True
    ) -> GeminiResponse:
        """
        Genera contenido usando Gemini con manejo de errores y retry logic.

        Args:
            prompt: Prompt para el modelo
            system_instruction: Instrucción de sistema opcional
            retry: Si debe reintentar en caso de rate limit

        Returns:
            GeminiResponse con el resultado
        """
        # Construir el contenido
        contents = []
        if system_instruction:
            contents.append(system_instruction + "\n\n")
        contents.append(prompt)

        full_prompt = "".join(contents)

        last_error = None

        for attempt in range(self.MAX_RETRIES if retry else 1):
            try:
                logger.debug(f"Generando contenido (intento {attempt+1})")
                
                # Configuración de generación
                config = GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_output_tokens,
                )

                # Generar contenido con nueva API
                response = self.client.models.generate_content(
                    model=self.model_name, contents=full_prompt, config=config
                )

                # Extraer texto de la respuesta
                if not response or not response.text:
                    logger.warning("Respuesta vacía del modelo")
                    return GeminiResponse(
                        text="", success=False, error="Respuesta vacía del modelo"
                    )

                logger.info("Contenido generado exitosamente")
                return GeminiResponse(
                    text=response.text, success=True, model_used=self.model_name
                )

            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"Error en intento {attempt+1}: {e}")

                # Detectar rate limit
                if "quota" in error_msg or "rate" in error_msg or "429" in error_msg:
                    last_error = GeminiRateLimitError(f"Rate limit excedido: {str(e)}")

                    if retry and attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_DELAY * (self.BACKOFF_MULTIPLIER**attempt)
                        logger.info(f"Rate limit. Esperando {delay}s...")
                        time.sleep(delay)
                        continue

                # Otros errores de conexión
                elif "connection" in error_msg or "timeout" in error_msg:
                    last_error = GeminiConnectionError(
                        f"Error de conexión: {str(e)}"
                    )

                    if retry and attempt < self.MAX_RETRIES - 1:
                        logger.info(f"Error de conexión. Reintentando en {self.RETRY_DELAY}s...")
                        time.sleep(self.RETRY_DELAY)
                        continue

                # Error general
                else:
                    last_error = GeminiClientError(f"Error en Gemini: {str(e)}")
                    logger.error(f"Error no recuperable: {e}", exc_info=True)

                # Si no reintentar, salir del loop
                if not retry:
                    break

        # Si llegamos aquí, todos los reintentos fallaron
        logger.error("Todos los intentos de generación fallaron")
        return GeminiResponse(text="", success=False, error=str(last_error))

    def generate_content(self, prompt: str) -> str:
        """
        Alias de generate() que retorna solo el texto para compatibilidad.

        Args:
            prompt: Prompt para el modelo

        Returns:
            Texto generado o string vacío si falla
        """
        response = self.generate(prompt)
        return response.text if response.success else ""

    def test_connection(self) -> bool:
        """
        Prueba la conexión con Gemini.

        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            response = self.generate("Test", retry=False)
            return response.success
        except Exception:
            return False


class CareerStrategist:
    """
    Estratega de carrera impulsado por Gemini.

    Implementa la lógica del protocolo de Gap Analysis para generación de CVs.
    """

    def __init__(self, client: Optional[GeminiClient] = None):
        """
        Inicializa el estratega de carrera.

        Args:
            client: Cliente de Gemini opcional. Si no se proporciona, crea uno nuevo.
        """
        self.client = client or GeminiClient()

    def _build_system_prompt(self, yaml_template: str) -> str:
        """Construye el prompt del sistema con el template YAML."""
        return f"""Eres un **Estratega de Carrera Senior** y experto en **RenderCV**. 
Tu objetivo es crear la hoja de vida perfecta en formato YAML, pero tu prioridad es 
asegurarte de que el usuario demuestre su máxima compatibilidad con la vacante.

En el siguiente template YAML: Este es tu mapa estricto. Debes respetar esta jerarquía 
y nombres de variables (keys) para que el código funcione.

```yaml
{yaml_template}
```

**PROTOCOLO DE INTERACCIÓN OBLIGATORIO (PASO A PASO):**

**PASO 1: ANÁLISIS DE BRECHAS (GAP ANALYSIS)**

Cuando el usuario te entregue: [CV Actual] + [Descripción de Vacante] + [Idioma], 
**NO GENERES EL YAML TODAVÍA**.

Debes realizar un análisis comparativo:
1. Identifica las habilidades técnicas y blandas críticas ("Must-haves") de la vacante.
2. Cruza esto con el CV del usuario.
3. Detecta qué habilidades pide la vacante que **NO** aparecen explícitamente en el CV del usuario.

**TU RESPUESTA AL PASO 1 (La Entrevista):**

Responde al usuario con una lista de preguntas directas sobre esas habilidades faltantes.

*Ejemplo:* "He analizado la vacante. Veo que piden 'Docker' y 'Liderazgo de equipos', 
pero no lo mencionas en tu CV actual. ¿Tienes experiencia con estas herramientas? 
Si es así, dime brevemente cómo las has usado."

**PASO 2: REDACCIÓN Y GENERACIÓN (Solo tras la respuesta del usuario)**

Una vez el usuario confirme qué conocimientos sí tiene (y cuáles no), procede a generar el código YAML.

**Instrucciones de Reescritura (La Magia):**

Con la nueva información confirmada por el usuario:
1. **Perfil/Summary:** Redacta un perfil profesional potente que integre las palabras clave 
   de la vacante y las habilidades recién confirmadas.
2. **Experiencia Laboral:** REESCRIBE los logros (bullet points) existentes.
   * *Objetivo:* No solo agregues las nuevas habilidades en una lista. 
     **Intégralas en la narrativa de los trabajos pasados.**
   * *Ejemplo:* Si el usuario confirmó que sabe SQL, cambia "Hice reportes" por 
     "Optimicé la generación de reportes mediante consultas complejas en SQL...".
3. **Filtrado:** Si el usuario admitió NO tener una habilidad, no la inventes.

**SALIDA FINAL:**

Entrega únicamente el bloque de código YAML válido basado en el template proporcionado. 
El YAML debe estar envuelto en marcadores para facilitar su extracción:

```yaml
# Tu YAML aquí
```

IMPORTANTE: Genera el YAML en el idioma especificado por el usuario.
"""

    def analyze_gap(
        self, cv_text: str, job_description: str, language: str = "es"
    ) -> GeminiResponse:
        """
        Paso 1: Análisis de brechas entre CV y vacante.

        Args:
            cv_text: CV actual del usuario
            job_description: Descripción de la vacante
            language: Idioma objetivo (es, en, pt, fr)

        Returns:
            GeminiResponse con las preguntas sobre habilidades faltantes
        """
        # Template simplificado para el análisis inicial
        simple_template = "cv:\\n  name: John Doe\\n  # ... estructura básica"

        system_prompt = self._build_system_prompt(simple_template)

        user_prompt = f"""
**Idioma objetivo:** {language}

**Mi CV Actual:**
{cv_text}

**Descripción de la Vacante:**
{job_description}

Por favor, realiza el PASO 1: Análisis de Brechas. Identifica qué habilidades pide la 
vacante que no aparecen en mi CV y hazme preguntas específicas sobre ellas.
"""

        return self.client.generate(user_prompt, system_instruction=system_prompt)

    def generate_yaml(
        self,
        cv_text: str,
        job_description: str,
        user_answers: str,
        language: str,
        yaml_template: str,
    ) -> GeminiResponse:
        """
        Paso 2: Generación del YAML optimizado.

        Args:
            cv_text: CV original del usuario
            job_description: Descripción de la vacante
            user_answers: Respuestas del usuario a las preguntas de la IA
            language: Idioma objetivo
            yaml_template: Template YAML completo a seguir

        Returns:
            GeminiResponse con el YAML generado
        """
        system_prompt = self._build_system_prompt(yaml_template)

        user_prompt = f"""
**Idioma objetivo:** {language}

**Mi CV Actual:**
{cv_text}

**Descripción de la Vacante:**
{job_description}

**Mis Respuestas a tus Preguntas:**
{user_answers}

Ahora procede con el PASO 2: Genera el YAML completo optimizado integrando mis respuestas 
en la narrativa de mi experiencia laboral. Recuerda respetar el template proporcionado.
"""

        response = self.client.generate(user_prompt, system_instruction=system_prompt)

        if response.success:
            # Extraer el YAML de la respuesta
            response.text = self._extract_yaml(response.text)

        return response

    def _extract_yaml(self, text: str) -> str:
        """
        Extrae el bloque YAML de la respuesta de la IA.

        Args:
            text: Texto completo de la respuesta

        Returns:
            Contenido YAML limpio
        """
        # Buscar bloques de código YAML
        if "```yaml" in text:
            start = text.find("```yaml") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        else:
            # Si no hay marcadores, devolver todo
            return text.strip()

    def continue_conversation(
        self, conversation_history: list[dict[str, str]], yaml_template: str
    ) -> GeminiResponse:
        """
        Continúa una conversación existente con el contexto completo.

        Args:
            conversation_history: Lista de mensajes [{"role": "user"/"model", "text": "..."}]
            yaml_template: Template YAML para el contexto

        Returns:
            GeminiResponse con la respuesta de la IA
        """
        system_prompt = self._build_system_prompt(yaml_template)

        # Construir el historial de chat
        full_prompt = system_prompt + "\\n\\n"
        for msg in conversation_history:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            full_prompt += f"{role}: {msg['text']}\\n\\n"

        return self.client.generate(full_prompt, retry=True)

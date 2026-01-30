"""
Módulo AI Proxy: Asistente inteligente para entrevistas y postulaciones.
"""
from src.ai_backend import GeminiClient
from src.database import CVDatabase
from src.prompts import PromptManager
from src.logger import get_logger

logger = get_logger(__name__)

class InterviewProxy:
    """Actúa como proxy del usuario para responder preguntas de entrevista."""

    def __init__(self, ai_client: GeminiClient, db: CVDatabase):
        self.ai_client = ai_client
        self.db = db

    def answer_question(self, 
                       question: str, 
                       cv_text: str, 
                       job_description: str, 
                       user_name: str = "Candidato",
                       tone: str = "Profesional") -> str:
        """
        Genera una respuesta a una pregunta de entrevista utilizando el contexto del usuario.
        
        Args:
            question: La pregunta a responder.
            cv_text: El texto del CV del usuario.
            job_description: La descripción de la vacante.
            user_name: Nombre del usuario (para el prompt).
            tone: Tono deseado (Profesional, Entusiasta, Conciso, etc.).
            
        Returns:
            La respuesta generada por la IA.
        """
        try:
            # 1. Obtener contexto de memoria de skills (información confirmada por el usuario)
            skill_memory = self.db.get_all_skill_answers()
            skill_context_str = ""
            if skill_memory:
                skill_context_str = "\n".join([f"- **{k.title()}:** {v}" for k,v in skill_memory.items()])
            else:
                skill_context_str = "No hay detalles específicos de habilidades confirmadas previamente."
            
            # 2. Construir prompt
            prompt = PromptManager.get_interview_answer_prompt(
                user_name=user_name,
                cv_context=cv_text,
                skill_memory_context=skill_context_str,
                job_description=job_description,
                question=question,
                tone=tone
            )
            
            logger.info(f"Generando respuesta de entrevista para: '{question[:30]}...' (Tono: {tone})")
            
            # 3. Generar respuesta
            response = self.ai_client.generate(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generando respuesta de entrevista: {e}", exc_info=True)
            raise

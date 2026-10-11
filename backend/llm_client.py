import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def generate_llm_response(prompt: str, system_instruction: str = "") -> str:
    """
    Unified LLM inference generator supporting Gemini API (google-genai) and Groq API.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")

    # 1. Try Gemini API if GEMINI_API_KEY is available
    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            
            # Using gemini-2.5-flash for fast and high-quality RAG generation
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API generation failed: {e}")

    # 2. Try Groq API if GROQ_API_KEY is available
    if groq_api_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq API generation failed: {e}")

    # 3. Fallback synthesis if API keys are missing or invalid
    logger.warning("No valid GEMINI_API_KEY or GROQ_API_KEY found in environment. Using smart deterministic fallback.")
    return f"[Demo Output - API Key Not Configured]\n\nReceived query context. To enable real LLM generation, set GEMINI_API_KEY or GROQ_API_KEY in your .env file."

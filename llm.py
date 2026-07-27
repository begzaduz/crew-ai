import time
import logging

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from config import GEMINI_KEY, GEMINI_MODEL

log = logging.getLogger(__name__)
gemini_client = genai.Client(api_key=GEMINI_KEY)


# ── Gemini API — kvota tejash uchun retry o'chirilgan ─────
def groq_call(system_prompt: str, user_prompt: str,
              temperature: float = 0.4, max_tokens: int = 700) -> str:
    """
    Gemini ga so'rov.
    RPD (kunlik) limit juda kichik bo'lgani uchun 429/RESOURCE_EXHAUSTED
    kelsa DARHOL xato ko'taradi — qayta urinish yo'q. Qayta urinish RPD
    tugagan holatda befoyda, faqat vaqtni yo'qotadi va process'ni bloklaydi.
    Faqat vaqtinchalik server xatosida (5xx) 1 marta 15s dan keyin
    qayta urinadi, chunki bu kvotaga aloqasi yo'q, tarmoq/server muammosi.
    Funksiya nomi 'groq_call' saqlanib qoldi — workflow'lar shu nomni
    chaqiradi, ularga tegmaslik uchun.
    """
    try:
        resp = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return (resp.text or '').strip()

    except ClientError as e:
        is_rate_limit = '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e)
        if is_rate_limit:
            log.error('[Gemini] Kvota tugadi (429) — qayta urinilmaydi, kvota tejaldi.')
        else:
            log.error(f'[Gemini] Client xato: {e}')
        raise

    except ServerError as e:
        log.warning('[Gemini] Server xato. 15s kutib 1 marta qayta urinamiz...')
        time.sleep(15)
        try:
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return (resp.text or '').strip()
        except Exception as e2:
            log.error(f'[Gemini] Server xato — qayta urinishdan keyin ham: {e2}')
            raise

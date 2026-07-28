import logging

from agents.llm import groq_call

log = logging.getLogger(__name__)


def run(context: dict) -> dict:
    """
    context ichida kutiladi:
      context["article"]["title"]
      context["outputs"]["draft"] — Writer natijasi
      context["config"]["editor_prompt"] = system prompt matni

    context["outputs"]["edited"] ga natijani yozadi (APPROVED bo'lsa draft,
    FIXED bo'lsa tuzatilgan versiya).
    """
    article = context["article"]
    draft = context["outputs"]["draft"]
    prompt = context["config"]["editor_prompt"]

    result = groq_call(
        prompt,
        f"Review this Uzbek post about: {article['title']}\n\nPOST:\n{draft}",
        temperature=0.2, max_tokens=700,
    )

    if 'APPROVED' in result:
        log.info('[Editor] ✓ Tasdiqlandi')
        context["outputs"]["edited"] = draft
    elif 'FIXED:' in result:
        fixed = result.split('FIXED:')[-1].strip()
        log.info('[Editor] ✓ Tuzatildi')
        context["outputs"]["edited"] = fixed
    else:
        log.warning(f'[Editor] Natija noaniq: {result[:80]}')
        context["outputs"]["edited"] = draft

    return context

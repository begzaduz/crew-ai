import logging

from agents.llm import groq_call

log = logging.getLogger(__name__)


def run(context: dict) -> dict:
    """
    context ichida kutiladi:
      context["article"]["title"]
      context["outputs"]["facts"] — Researcher natijasi
      context["config"]["writer_prompt"] = system prompt matni

    context["outputs"]["draft"] ga natijani yozadi.
    """
    article = context["article"]
    facts = context["outputs"]["facts"]
    prompt = context["config"]["writer_prompt"]

    result = groq_call(
        prompt,
        f"Yangilik yoz:\n\nSARLAVHA: {article['title']}\nFAKTLAR:\n{facts}\n\nFaqat postni yoz:",
        temperature=0.5, max_tokens=600,
    )
    log.info(f'[Writer] ✓ {len(result)} belgi')

    context["outputs"]["draft"] = result
    return context

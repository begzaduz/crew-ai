import logging

from agents.llm import groq_call
from feeds import fetch_article_text

log = logging.getLogger(__name__)


def run(context: dict) -> dict:
    """
    context ichida kutiladi:
      context["article"] = {"title": ..., "description": ..., "url": ...}
      context["config"]["researcher_prompt"] = system prompt matni

    context["outputs"]["facts"] ga natijani yozadi.
    """
    article = context["article"]
    prompt = context["config"]["researcher_prompt"]

    content = fetch_article_text(article.get('url')) or ''
    if len(content) < 100:
        content = f"{article['title']}\n{article.get('description', '')}"

    result = groq_call(
        prompt,
        f"Analyze this Premier League news:\n\nHEADLINE: {article['title']}\nCONTENT: {content[:1200]}",
        temperature=0.2, max_tokens=300,
    )
    log.info(f'[Researcher] ✓ {article["title"][:50]}')

    context["outputs"]["facts"] = result
    return context

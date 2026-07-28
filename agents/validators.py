import re


def validate_post(post: str) -> tuple[bool, str]:
    if len(post.strip()) < 50:
        return False, 'Post juda qisqa (< 50 belgi)'
    if len(post) > 1000:
        return False, f'Post juda uzun ({len(post)} belgi, max 1000)'
    markdown_patterns = [r'\*\*', r'__', r'\[.+\]\(.+\)', r'^#{1,6} ']
    for pat in markdown_patterns:
        if re.search(pat, post, re.MULTILINE):
            return False, f'Markdown belgisi topildi: {pat}'
    return True, ''


def ensure_channel_tag(post: str, tag: str = '@Inglizfutbol') -> str:
    if tag not in post:
        post = post.rstrip() + f'\n\n{tag}'
    return post

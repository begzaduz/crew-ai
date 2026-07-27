from workflows.rss_news import RSSNewsWorkflow

# Har workflow bir marta instantiate qilinadi (state saqlamaydi,
# har run() chaqiruvida yangi context yaratiladi — shuning uchun
# qayta ishlatish xavfsiz).
_WORKFLOWS = {
    "rss_news": RSSNewsWorkflow(),
    # Kelajakda:
    # "social_media": SocialMediaWorkflow(),
    # "blog": BlogWorkflow(),
}


def get_workflow(name: str):
    if name not in _WORKFLOWS:
        raise ValueError(f"Noma'lum workflow: {name!r}. Mavjudlar: {list(_WORKFLOWS)}")
    return _WORKFLOWS[name]

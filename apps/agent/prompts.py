"""User-defined "insights" system prompt.

Edit INSIGHTS_SYSTEM_PROMPT to change what the daily digest prioritizes, how it
reads, and what it skips. Nothing else in the pipeline needs to change when you
tune this — it's the single knob for "the user's vision" mentioned in the plan.
"""

from apps.models.article import Article

INSIGHTS_SYSTEM_PROMPT = """\
أنت تنسّق ملخصًا يوميًا شخصيًا لشخص يتابع أخبار وتعلّم الذكاء الاصطناعي، \
التعلم الآلي، وعلوم الحاسب — من فيديوهات يوتيوب تعليمية، مقالات مدونات تقنية، \
وأوراق arXiv جديدة يتابعها.

اكتب دائمًا بالعربية الفصحى، حتى لو كان المصدر الأصلي بالإنجليزية بالكامل — \
لخّص وترجم في خطوة واحدة. لا تستخدم كلمات إنجليزية إلا للمصطلحات التقنية أو \
الأسماء التجارية التي ليس لها مقابل عربي شائع (مثل GPT، API، arXiv).

رتّب الأولوية كالتالي:
1. الشروحات والدروس التي تعلّم تقنية معيّنة بوضوح.
2. أوراق arXiv الجديدة بفكرة أو نتيجة جديدة فعليًا (تجاهل التحسينات الطفيفة إلا \
   إذا كان الملخص واضحًا جدًا حول الجديد فيها).
3. المحتوى العملي/التطبيقي (شرح كود، أمثلة فعلية).
4. مقالات الرأي/التحليل المفيدة لفهم موضوع معيّن، إذا كانت جوهرية.

النبرة: واضحة وتعليمية، مثل زميل دراسة مطّلع — افترض أن القارئ يريد فعلًا \
تعلّم المادة، مو مجرد تصفح العناوين. فضّل الدقة على الإثارة، واشرح المصطلحات \
غير الواضحة بجملة قصيرة بدل تجاهلها.

تجاهل: المحتوى الممول، منشورات الإعلانات المحضة بدون قيمة تعليمية، وأي شيء \
ليس جديدًا أو توضيحيًا فعليًا.
"""


def build_item_summary_prompt(title: str, content: str) -> str:
    """User-turn content for summarizing a single article/video."""
    body = content.strip() if content else "(لا يوجد محتوى إضافي — لخّص بناءً على العنوان فقط)"
    return f"العنوان: {title}\n\nالمحتوى:\n{body}\n\nاكتب ملخصًا من جملة إلى جملتين لهذا العنصر، بالعربية."


def build_digest_prompt(articles_by_source: dict[str, list[Article]]) -> str:
    """User-turn content for assembling the full daily digest from per-item summaries."""
    lines: list[str] = ["ابنِ ملخص اليوم من العناصر التالية، مجمّعة حسب المصدر.", ""]
    for source_name, articles in articles_by_source.items():
        lines.append(f"## {source_name}")
        for article in articles:
            summary = article.summary or article.title
            lines.append(f"- {article.title}\n  الرابط: {article.url}\n  الملخص: {summary}")
        lines.append("")
    lines.append(
        "أنتج ملخصًا يوميًا قصيرًا بصيغة HTML، بالعربية الفصحى بالكامل: سطر مقدمة "
        "مختصر، ثم لكل مصدر عنوان فرعي وقائمة نقطية بالعناصر — كل نقطة مقتطف "
        "قصير (جملة إلى جملتين) متبوع برابط للمصدر الأصلي (استخدم الرابط "
        "المعطى حرفيًا داخل وسم <a href>)."
    )
    return "\n".join(lines)

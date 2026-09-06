"""RAG chat system prompt + user-turn prompt builder. Kept separate from
apps/agent/prompts.py (the digest "insights" prompt) since they steer two
different features — edit this one to change how the chat assistant answers.
"""

from apps.rag.retrieval import RetrievedChunk

RAG_SYSTEM_PROMPT = """\
أنت مساعد دراسي تجيب على أسئلة عن مكتبة محتوى شخصية بالذكاء الاصطناعي/التعلم \
الآلي/علوم الحاسب (فيديوهات يوتيوب تعليمية، مقالات مدونات تقنية، وأوراق \
arXiv) تم فهرستها مسبقًا.

القواعد:
1. أجب فقط باستخدام المصادر المرقّمة المعطاة بالبرومبت — لا تستخدم معرفة \
   خارجية لسد الفجوات.
2. استشهد بكل معلومة برقم مصدرها بين قوسين، مثل [1]، [2].
3. إذا لم تكن المصادر كافية للإجابة، قل ذلك صراحة بدل التخمين.
4. أجب دائمًا بالعربية الفصحى، حتى لو كانت المصادر بالإنجليزية بالكامل.
5. كن مختصرًا وتقنيًا — افترض أن القارئ يعرف الأساسيات ويريد الإجابة \
   المحددة، مو شرحًا كاملاً من الصفر.
"""


def build_rag_prompt(question: str, retrieved: list[RetrievedChunk]) -> str:
    lines = [f"السؤال: {question}", "", "المصادر:"]
    for i, r in enumerate(retrieved, start=1):
        lines.append(f"[{i}] {r.article.title} ({r.article.url})\n{r.chunk.content}\n")
    lines.append(
        "أجب على السؤال باستخدام المصادر أعلاه فقط. استشهد بالمصادر داخل النص "
        "مثل [1]. إذا كانت المصادر لا تجيب على السؤال، قل إنك لا تعرف."
    )
    return "\n".join(lines)

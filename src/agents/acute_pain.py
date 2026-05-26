"""Health complaint detector — deterministic routing shortcut to FAQ.

Why this exists (post-rewrite 2026-05-26):
    Earlier this module had a hardcoded ``_RELIEF_MAP`` that mapped each
    symptom to a specific acupoint, with location + press instructions.
    That was wrong — all of that data already lives in the KB cards
    (``tcm_acupressure_pain.json``, ``tcm_acupressure_energy_stress.json``,
    etc.), reachable via FAQ's vector search + ``AcupointImageMap``'s
    auto image/video attachment.

    Hardcoding the acupoint content in Python:
      - duplicated knowledge that the clinic team curates in KB cards
      - meant the Writer was told one thing while FAQ surfaced another
      - blocked clinic content edits from taking effect

Current scope: ONLY symptom detection. Returns a short symptom name or
None. The Planner uses this to route pain mentions deterministically to
FAQ + CASUAL — the actual KB lookup, acupoint info, and image attach
all happen downstream as designed.

If the LLM Planner (gpt-4o) reliably routes pain → FAQ on its own, this
fast-path is redundant. We keep it as a deterministic safety net for
the most common keywords, at zero cost.
"""

from __future__ import annotations


# Health-complaint keywords. Hits route deterministically to FAQ + CASUAL.
# Bilingual (Traditional / Simplified) where forms differ. Generic terms
# only — no urgency intensifiers; the LLM Planner handles nuance.
#
# NOT included here (handled by dedicated rules elsewhere in the planner):
#   - Skin conditions (皮膚痕 / 暗瘡 / 濕疹) → ointment pitch (Sales)
#   - Tongue / 4-MCQ symptom intake on first-touch → Constitution flow
_COMPLAINT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("頭痛",      ("頭痛", "頭好痛", "偏頭痛", "頭脹", "头痛", "头疼", "偏头痛")),
    ("經痛",      ("經痛", "M痛", "生理痛", "經期痛", "经痛", "经期痛", "月經痛", "月经痛")),
    ("失眠",      ("失眠", "瞓唔著", "唔瞓得", "夜晚醒", "睡不着", "睡不好", "睡眠差")),
    ("肩頸痛",    ("肩頸痛", "膊頭痛", "頸痛", "頸梗", "肩膀痛", "肩颈痛", "颈痛")),
    ("腰痛",      ("腰痛", "腰酸", "腰好痛", "閃到腰", "腰疼", "腰酸背痛")),
    ("眼睛疲勞",  ("眼攰", "眼乾", "眼花", "眼酸", "眼睛累")),
    ("鼻塞",      ("鼻塞", "鼻唔通", "流鼻水")),
    ("頭暈",      ("頭暈", "暈眩", "天旋地轉", "头晕")),
    ("心煩胸悶",  ("心煩", "胸悶", "焗住", "唞唔到氣", "心翳")),
    ("疲勞",      ("好攰", "好累", "無精神", "无精神", "精神差", "成日攰")),
)


def detect_health_complaint(text: str) -> str | None:
    """Return a canonical symptom name if the message contains a known
    health complaint, else None.

    The Planner routes hits to FAQ + CASUAL so KB vector search can
    surface the matching acupressure / food-therapy / treatment card.
    The acupoint image and video attach automatically downstream — we
    do NOT hardcode acupoint info here.
    """
    if not text:
        return None
    for canonical, variants in _COMPLAINT_KEYWORDS:
        if any(v in text for v in variants):
            return canonical
    return None

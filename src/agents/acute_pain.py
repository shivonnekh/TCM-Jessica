"""Acute pain detector — maps urgent symptoms to immediate-relief acupoints.

When a user expresses acute distress ("我頭好痛", "經痛勁", "頂唔順"),
Jessica routes immediately to FAQ + CASUAL with the relevant 30-second
self-relief acupoint in `notes_for_writer`. The Writer leads with
empathy + the acupoint instruction so the user can act NOW.

Gating: requires both an acute-language signal ("好痛", "好辛苦",
"頂唔順", "勁", "好慘", emoji 😭/🥲/😣) AND a symptom keyword. Plain
"頭痛" without urgency falls through to standard FAQ flow.

All acupoints referenced here exist in `data/acupoints/index.json`,
so FAQ agent's existing image-attach pipeline will auto-include the
acupoint photo / video.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcuteRelief:
    """Detected acute pain + the recommended immediate-relief acupoint."""

    symptom_zh: str                      # "頭痛" / "經痛" / ...
    primary_acupoint_zh: str             # 合谷穴 (must exist in acupoint index)
    location_zh: str                     # where on the body
    press_instruction_zh: str            # how to press, 30-sec protocol
    tcm_rationale_zh: str                # why this point relieves this symptom
    backup_acupoint_zh: str = ""         # optional secondary point


# Acute-language signals — at least one MUST be in the message to fire.
_ACUTE_TOKENS = (
    "好痛", "好辛苦", "頂唔順", "受唔到", "好慘", "好難受",
    "勁痛", "勁", "好頂", "辛苦死", "痛到", "唔識點算",
    "幫吓我", "點算", "突然", "天旋地轉", "受不了",
    # Emojis carry urgency on WhatsApp
    "😭", "🥲", "😣", "😖", "🤕", "😵",
)


# Symptom keyword → relief mapping. All acupoint names match
# data/acupoints/index.json so images / videos auto-attach.
_RELIEF_MAP: tuple[tuple[tuple[str, ...], AcuteRelief], ...] = (
    # 頭痛 / 偏頭痛
    (
        ("頭痛", "頭好痛", "偏頭痛", "頭脹痛", "後尾枕痛", "前額痛"),
        AcuteRelief(
            symptom_zh="頭痛",
            primary_acupoint_zh="合谷穴",
            location_zh="虎口位 — 大拇指同食指之間嘅凹位",
            press_instruction_zh="用對側手嘅拇指打圈按壓 30 秒，配合深呼吸，痛側按耐啲",
            tcm_rationale_zh="合谷係手陽明大腸經要穴，主治頭面口齒一切痛症 — 1 分鐘內通常會輕咗",
            backup_acupoint_zh="風池穴",
        ),
    ),
    # 經痛
    (
        ("經痛", "M痛", "生理痛", "經期痛", "下腹痛", "肚痛"),
        AcuteRelief(
            symptom_zh="經痛",
            primary_acupoint_zh="三陰交穴",
            location_zh="腳內踝向上 3 吋（自己 4 隻手指闊度）嘅位置",
            press_instruction_zh="坐低，用拇指按壓 1 分鐘，輕度發酸係正常",
            tcm_rationale_zh="三陰交係肝脾腎三經交會，係調經止痛嘅黃金穴位",
            backup_acupoint_zh="地機穴",
        ),
    ),
    # 失眠 / 瞓唔著
    (
        ("失眠", "瞓唔著", "唔瞓得", "夜晚醒"),
        AcuteRelief(
            symptom_zh="失眠",
            primary_acupoint_zh="內關穴",
            location_zh="手腕橫紋向上 2 吋（3 隻手指闊度）嘅中央",
            press_instruction_zh="瞓覺前用拇指按壓 1 分鐘，左右手交替",
            tcm_rationale_zh="內關係手厥陰心包經，主治寧心安神 — 配合深呼吸特別有效",
        ),
    ),
    # 心煩 / 胸悶
    (
        ("心煩", "胸悶", "焗住", "唞唔到氣", "心翳"),
        AcuteRelief(
            symptom_zh="心煩胸悶",
            primary_acupoint_zh="膻中穴",
            location_zh="兩個乳頭中間嘅胸骨位",
            press_instruction_zh="用中指打圈按壓 30 秒，配合慢慢深呼吸",
            tcm_rationale_zh="膻中係氣會，主理一身之氣 — 胸悶氣鬱嘅即時舒緩穴",
            backup_acupoint_zh="內關穴",
        ),
    ),
    # 肩頸痛
    (
        ("肩頸痛", "膊頭痛", "頸痛", "頸梗", "肩膀痛"),
        AcuteRelief(
            symptom_zh="肩頸痛",
            primary_acupoint_zh="風池穴",
            location_zh="後頸髮際線兩側嘅凹陷位（耳後對落少少）",
            press_instruction_zh="用拇指向上斜入推按 1 分鐘，會酸但通到頭頂",
            tcm_rationale_zh="風池主治頭頸僵硬、上實下虛 — 打工仔頂頸最常用",
            backup_acupoint_zh="肩外俞穴",
        ),
    ),
    # 鼻塞
    (
        ("鼻塞", "鼻唔通", "塞住", "流鼻水"),
        AcuteRelief(
            symptom_zh="鼻塞",
            primary_acupoint_zh="迎香穴",
            location_zh="鼻翼兩側嘅凹陷處（笑紋上邊）",
            press_instruction_zh="用食指打圈按壓 30 秒，會即刻有通氣感",
            tcm_rationale_zh="迎香係手陽明大腸經，主通鼻竅 — 名副其實「迎接香氣」",
        ),
    ),
    # 腰痛
    (
        ("腰痛", "腰酸", "腰好痛", "閃到腰"),
        AcuteRelief(
            symptom_zh="腰痛",
            primary_acupoint_zh="命門穴",
            location_zh="後腰正中央，平肚臍嘅水平線位置",
            press_instruction_zh="用熱手掌搓熱呢個位置 1 分鐘，再用拇指按壓",
            tcm_rationale_zh="命門係督脈要穴，主腎陽 — 腰為腎之府，按命門即補腎強腰",
            backup_acupoint_zh="承山穴",
        ),
    ),
    # 眼攰
    (
        ("眼攰", "眼乾", "眼花", "眼酸"),
        AcuteRelief(
            symptom_zh="眼睛疲勞",
            primary_acupoint_zh="四白穴",
            location_zh="瞳孔向下約一指闊度嘅顴骨凹位",
            press_instruction_zh="閉眼用食指打圈按壓 30 秒，左右同步",
            tcm_rationale_zh="四白係足陽明胃經，主目疾 — 對住電腦太耐必按",
            backup_acupoint_zh="陽白穴",
        ),
    ),
    # 高血壓 / 眩暈
    (
        ("頭暈", "暈眩", "天旋地轉", "血壓高"),
        AcuteRelief(
            symptom_zh="頭暈眩",
            primary_acupoint_zh="太衝穴",
            location_zh="腳背上，第 1、2 趾骨交界嘅凹陷位",
            press_instruction_zh="用拇指由下向上推按 1 分鐘，會酸脹",
            tcm_rationale_zh="太衝係肝經原穴，平肝降逆 — 肝陽上亢嘅頭暈用呢個",
        ),
    ),
)


def detect_acute_pain(text: str) -> AcuteRelief | None:
    """Return an AcuteRelief if the message expresses acute distress + a known
    symptom. Returns None for non-urgent mentions (e.g. plain "頭痛" without
    intensifiers).
    """
    if not text:
        return None

    # Gate 1: must contain at least one acute-language signal
    has_acute_signal = any(tok in text for tok in _ACUTE_TOKENS)
    if not has_acute_signal:
        return None

    # Gate 2: must match a known symptom
    for keywords, relief in _RELIEF_MAP:
        if any(kw in text for kw in keywords):
            return relief

    return None

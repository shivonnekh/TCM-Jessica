"""Final Writer Agent — composes 1 final reply from all specialist outputs.

The Writer is the SOLE producer of user-facing text. Every specialist
returns structured intent; the Writer turns it into HK Cantonese bubbles.

Why a separate Writer (CLAUDE.md §3.6):
- Single Jessica voice — 5 specialists writing copy = 5 voices.
- HK 廣東話口語 polish lives here, once.
- Bubble-split rhythm tuning belongs in one place.
- Tone calibration based on CRM status happens here.
- Conflict resolution when 2 specialists disagree happens here.

The Writer is FORBIDDEN to invent medical / product / pricing /
appointment facts. It can only RE-NARRATE what specialists provided
in `payload`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.llm import LLMClient

from src.agents.base import (
    PlannerDecision,
    SpecialistName,
    SpecialistOutput,
    WriterOutput,
)
from src.crm.models import User, UserStatus

logger = logging.getLogger("agents.writer")

DEFAULT_MODEL = "gpt-4o-mini"
MAX_BUBBLES = 5


# Conflict resolution — when specialists disagree (e.g. FAQ "no_match"
# + Sales has products), Writer leans on the HIGHER-priority specialist
# for the primary message. Lower-priority info becomes a side mention
# only if it doesn't contradict the primary.
SPECIALIST_PRIORITY: list[SpecialistName] = [
    SpecialistName.CONSTITUTION,  # in-flow diagnostic — highest priority
    SpecialistName.APPOINTMENT,   # active booking — concrete action
    SpecialistName.SALES,         # pitch — drives revenue
    SpecialistName.FAQ,           # educational — informational
    SpecialistName.GREETING,      # filler — never override above
]


# Tone calibration — what voice to use based on user.status.
_TONE_MATRIX: dict[UserStatus, str] = {
    UserStatus.NEW: "warm + 自我介紹型 — 第一次見面，建立親切感",
    UserStatus.QUALIFIED: "好奇 + engaging — 引導用戶講多啲自己情況",
    UserStatus.CONSTITUTION_DONE: "confident + caring — 已經了解佢，建議自然",
    UserStatus.BOOKED: "reassuring + prep — 提預約細節，俾佢安心",
    UserStatus.BOUGHT: "感激 + follow-up — 關心使用效果",
    UserStatus.CHURNED: "好輕、零壓力、純關心 — 唔好 push pitch",
    UserStatus.OPTED_OUT: "(should not be reached)",
}


_SYSTEM = """你係 Jessica — 心宜中醫嘅 WhatsApp AI teammate。

身份:
- 唔係醫師，唔做診斷
- 溫柔、人情味、有少少俏皮，HK 廣東話口語
- 永遠用「我」，唔好用「Jessica」自稱 (除非有 new_user_intro flag)
- 唔好用書面語、唔好用普通話詞 (「您」「我們」「請」「嗎」)
- 用「你」「我哋」「啦」「嘞」「啊」「㗎」

你嘅工作:
讀 specialist 比你嘅 structured intent，組合成自然嘅 WhatsApp 對話。
每個 bubble 應該短而 punchy，就好似真人發 WhatsApp 咁。

══════════════════════════════
Bubble 長度規矩 (重要):
- 目標每個 bubble: 20-60 字 (短、punchy)
- Max 80 字。超過就要 split 做 2 個 bubble
- 一 turn 最多 5 個 bubble (短嘅 bubble 可以多啲，長嘅就少啲)
- 用 emoji 但克制 — 1-2 個 / bubble，唔好串連

好例子 (自然 WhatsApp 節奏):
✓ "Hello！我係 Jessica 啊 🌿"
✓ "你嘅體質係氣虛質"
✓ "意思係氣力比較弱，容易攰"
✓ "推介你飲花旗蔘湯，調補返"

差例子 (太長太書面):
✗ "你好，我係 Jessica，心宜中醫嘅 AI 助手。根據你嘅體質評估結果，你屬於氣虛體質，建議你飲用我們嘅花旗蔘湯來調補。"

══════════════════════════════
Conflict resolution (當 2 個 specialist 講唔同嘢):
優先級 (高 → 低):
  1. constitution  — 體質診斷係 in-flow
  2. appointment   — 預約係 concrete action
  3. sales         — 產品推介
  4. faq           — 教育/知識
  5. greeting      — filler

低優先級嘅 specialist 內容 → 變副線 / 略提 / drop。
例如: faq 返 no_match + sales 有產品 → focus sales，faq 略提。

══════════════════════════════
Tone calibration (根據 user.status):
{tone_matrix}

══════════════════════════════
══════════════════════════════
絕對唔可以做嘅事 (HALLUCINATION BAN):
1. 絕對唔可以講「你係 X 質」(X = 氣虛 / 濕熱 / 陰虛 / 痰濕 etc.)
   除非 constitution specialist 嘅 payload.phase == "declaring"
   並且 payload.constitution 有值。如果冇 constitution payload 或者
   phase != "declaring"，**永遠唔可以提體質名**。
2. 用戶皮膚痕、攰、痛唔等於某種體質。要等真嘅 4-MCQ 完成。
3. 用戶問「我係咩體質」/ 「點知我係濕熱」 → 答「要做下評估先知。
   可以發張脷相俾我，再答 4 條題」— 唔可以猜。
4. 絕對唔可以提付費產品名 / 價錢 (例「抗病毒湯 $88」、「茶樹綠豆濕敏膏 $90」)，
   除非當前 turn 嘅 sales specialist output payload 有提供。「Care Plus 自家
   出 10 款湯水 + 3 款藥膏」呢個 general fact OK，但具體邊一款 + 邊個價錢必
   須來自 sales payload。如果今 turn 只有 FAQ payload，唔好喺 reply 入面講
   產品名 + 價錢。

═════════════════════════════
公司事實 (Jessica 必須記住，絕對唔可以否認):
- 心宜中醫 Care Plus 自己出 10 款預製湯水 ($48 - $120)
- 心宜中醫 自己出 3 款藥膏
- 全部產品由 Care Plus 心宜中醫 自家配方 / 自家做嘅，唔係市售
- 用戶問「係咪你哋自己出?」→ 答「係，全部我哋自家配方 + 製作」

⛔ 絕對唔可以畀 WhatsApp 號碼 / 「WhatsApp +852 5241 7448」之類嘅 link
   俾用戶 — 用戶已經喺呢個 WhatsApp 對話度同 Jessica 講嘢，叫佢去
   同一個號碼係 nonsense。

用戶問「邊度買 / 點訂 / 點落單」應該答：
- 「想要邊款？同我講你嘅選擇 + 收件地址，我會幫你 forward 比診所同事跟進」
- 或者「揀好咗講聲我聽，我幫你記低」
- 唔好叫佢「WhatsApp 我哋」/ 「揾客服」 — 你就係客服。

══════════════════════════════
規矩 (絕對唔可以違反):
- 絕對唔可以作 specialist 冇講嘅嘢 (個別產品名、價錢、用戶體質、地址、診金)
- 一般中醫食療常識、煲湯點煮、養生 tips → 可以用 LLM 知識答 (唔受限於
  specialist payload)。但「邊一款湯水/藥膏」「幾錢」「邊個診所」「邊個體質」
  必須 grounded。
- 絕對唔可以基於 FAQ knowledge cards 推測用戶體質。Cards 講「X 體質會有
  XXX 症狀」唔代表用戶就係 X 體質 — 反向推理係 banned。
- 絕對唔可以講 specialist payload 嘅 writer_must_not_say 入面嘅話。
- 用戶問「點買 / 我要 / 怎麼賣」+ Sales payload 有 products_to_pitch →
  **逐款列出名 + 價錢 + 圖** (每款 1 bubble + media_to_send 加 image_url)。
  絕對唔好淨係講「我哋有 N 款」然後叫客 WhatsApp 客服問 — 要實際 show。
  例: 「市售產品」、「冇新產品」、「唔係我哋自己做」全部係 banned。
- Sales payload intent="no_match" 時，唔代表「冇產品」— 只係冇新產品
  可推。用 order_channel 俾用戶聯絡渠道就 OK。
- 媒體 (圖片) 由 media_to_send 處理：
  * media_to_send 嘅 url 必須完全一字不變抄自 specialist payload 已經
    有嘅 URL field。可用嚟源:
      - greeting.intro_media[i].url            ← 洪醫師肖像
      - constitution.free_recipes[i].image_url ← 體質 declare 食譜照
      - sales.products_to_pitch[i].image_url   ← Sales pitch
      - faq.named_recipes[i].image_url         ← 「咩湯水」嘅食譜照
      - faq.acupoint_images[i].image_url       ← 穴位定位圖
  * 每個 media_to_send entry: {{"url": "<verbatim URL>", "after_bubble_idx": 0}}
  * 唔識 / payload 入面冇 URL → media_to_send 留 []
  * 唔可以作 URL、唔可以寫 'data/media/...' 等相對路徑
  * 用戶問穴位按摩 → 必須附返 faq.acupoint_images 入面嘅圖 (每個穴位
    一張圖，每張對應一個提到嗰個穴位嘅 bubble)。

- 食譜 / 湯水 推介 必須用真名 (specialist payload 入面嘅 title) +
  附返 image_url。絕對唔可以講「我哋有 128 款食譜但而家發唔到」或者
  「中醫湯水指南」呢類抽象嘢 — 一定要列實際食譜名 (例「健脾安神—太子參
  淮蓮紅棗粥」)。

⛔ 絕對唔可以喺 bubbles 入面寫:
  - Markdown image syntax `![alt](url)` — WhatsApp 唔渲染 markdown，
    用戶會睇到一條長 URL 嘅文字
  - 任何 https://tcm-jessica.onrender.com/... URL — 圖片連結
    應該淨係放喺 media_to_send，bubble 嘅 text 只應該係純文字描述
  - 食譜外部連結例如 healthy-food.hk → 同樣放 media_to_send，
    bubble 只講食譜名 + 一句描述
  例: 錯 → "1️⃣ 茶樹綠豆濕敏膏 ![](https://tcm-jessica.onrender.com/...)"
      啱 → bubble: "1️⃣ 茶樹綠豆濕敏膏 $90 — 輕度痕癢、蚊咬"
            media_to_send: [{{"url": "https://tcm-jessica.../ointment_chashu_lvdou.jpg",
                              "after_bubble_idx": 1}}]
- 用戶第一次見面 (greeting.intent_flags 包含 "new_user_intro") →
  * Bubble 1 一定要包含「我係 Jessica」自我介紹
  * greeting.intro_bubbles 可以直接抄做 bubbles (盡量唔改字)
  * greeting.intro_media 入面每張圖都要放入 media_to_send

輸出 JSON (純 JSON，唔好 markdown):
{{
  "bubbles": ["...", "..."],
  "media_to_send": [{{"url": "...", "after_bubble_idx": 0}}]
}}
"""


def _build_system_prompt() -> str:
    tone_lines = "\n".join(
        f"- status={status.value}: {voice}"
        for status, voice in _TONE_MATRIX.items()
        if status != UserStatus.OPTED_OUT
    )
    return _SYSTEM.format(tone_matrix=tone_lines)


class WriterAgent:
    def __init__(
        self,
        client: LLMClient,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 700,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._system = _build_system_prompt()

    async def compose(
        self,
        user: User,
        user_message: str,
        planner_decision: PlannerDecision,
        specialist_outputs: list[SpecialistOutput],
    ) -> tuple[WriterOutput, dict[str, Any]]:
        # FAST PATH: solo Greeting with official_intro=True → render
        # the bubbles + media VERBATIM. No LLM ad-libbing on the
        # signature first-touch intro (brand consistency).
        if (
            len(specialist_outputs) == 1
            and specialist_outputs[0].specialist == SpecialistName.GREETING
            and specialist_outputs[0].payload.get("official_intro") is True
        ):
            payload = specialist_outputs[0].payload
            bubbles = list(payload.get("intro_bubbles") or [])
            media = list(payload.get("intro_media") or [])
            if bubbles:
                output = WriterOutput(
                    bubbles=bubbles[:MAX_BUBBLES],
                    media_to_send=[
                        {
                            "url": m["url"],
                            "after_bubble_idx": str(m.get("after_bubble_idx", 0)),
                        }
                        for m in media
                        if m.get("url")
                    ],
                )
                return output, {
                    "model": "no_llm_official_intro",
                    "input_tokens": 0,
                    "output_tokens": 0,
                }

        # Sort specialist outputs by priority so the prompt presents
        # high-priority info first — gives the LLM an anchor for
        # conflict resolution.
        ordered = sorted(
            specialist_outputs,
            key=lambda o: _priority_rank(o.specialist),
        )

        prompt = _build_prompt(
            user=user,
            user_message=user_message,
            planner_decision=planner_decision,
            specialist_outputs=ordered,
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=self._system,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        try:
            data = _extract_json(raw)
            bubbles = [b.strip() for b in data.get("bubbles", []) if b.strip()]
            if not bubbles:
                raise ValueError("empty bubbles")
            output = WriterOutput(
                bubbles=bubbles[:MAX_BUBBLES],
                media_to_send=data.get("media_to_send", []),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("writer JSON parse failed (%s); raw=%r", exc, raw)
            output = WriterOutput(
                bubbles=["唔好意思啊，我而家有啲問題，等陣再試多次 🙏"],
                media_to_send=[],
            )

        usage = {
            "model": self._model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return output, usage


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _priority_rank(name: SpecialistName) -> int:
    try:
        return SPECIALIST_PRIORITY.index(name)
    except ValueError:
        return len(SPECIALIST_PRIORITY)  # unknown → lowest


def _build_prompt(
    *,
    user: User,
    user_message: str,
    planner_decision: PlannerDecision,
    specialist_outputs: list[SpecialistOutput],
) -> str:
    specialists_dump = "\n\n".join(
        f"=== Specialist: {o.specialist.value} (priority {_priority_rank(o.specialist) + 1}) ===\n"
        f"payload: {json.dumps(o.payload, ensure_ascii=False, indent=2)}"
        + (f"\ncards_used: {o.cards_used}" if o.cards_used else "")
        + (f"\ntools: {[t.get('name') for t in o.tools_called]}" if o.tools_called else "")
        for o in specialist_outputs
    )

    history_lines = []
    for m in user.conversation_history[-4:]:
        who = "用戶" if m.role == "user" else "Jessica"
        history_lines.append(f"- {who}: {m.content[:80]}")
    history_txt = "\n".join(history_lines) or "(冇歷史)"

    proactive_hint_line = (
        f"\nProactive hint: {planner_decision.proactive_hint}"
        if planner_decision.proactive_hint
        else ""
    )
    notes_line = (
        f"\nPlanner notes: {planner_decision.notes_for_writer}"
        if planner_decision.notes_for_writer
        else ""
    )

    return f"""用戶 CRM:
- phone: {user.phone}
- name: {user.name or "(未知)"}
- status: {user.status.value}
- 體質: {user.constitution.value}
- 已 pitch: {user.products_pitched or "(無)"}
- 已預約: {len(user.appointments)} 個

最近對話:
{history_txt}

用戶今次訊息: 「{user_message}」

Planner 路由:
- specialists: {[s.value for s in planner_decision.specialists]}
- mode: {planner_decision.mode}
- 原因: {planner_decision.reasoning}{notes_line}{proactive_hint_line}

Specialist intent (按 priority 由高到低):

{specialists_dump}

組合成 1-5 個短 bubble。記得 tone 跟住 user.status，bubble 短而 punchy。輸出 JSON。"""


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON: {text[:200]!r}")
    return json.loads(text[start : end + 1])

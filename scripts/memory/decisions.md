
## 2026-05-21 11:03 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:10 — TCM-Jessica

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）


## 2026-05-21 11:14 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:18 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:19 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:21 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:27 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:28 — TCM-Jessica

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）
- 然后告诉我，我就运行。它会用你的 Default profile（shivonnekhoo@gmail.com）直接打开，WhatsApp Web 应该已经登录了，不用扫码。
- Chrome 不允许对 Default profile 直接做 remote debugging。换个方式 — 用 subprocess 先启动 Chrome（带 debug port），然后 Playwright 连进去：
- WhatsApp Web 通了！但搜索找不到联系人。可能是选择器问题或联系人没存。让我 debug 看看搜索结果：
- 找到了！selector 用 `cell-frame-container` 不是 `listitem`。直接修：


## 2026-05-21 11:34 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:35 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:45 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 11:45 — TCM-Jessica

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）
- 然后告诉我，我就运行。它会用你的 Default profile（shivonnekhoo@gmail.com）直接打开，WhatsApp Web 应该已经登录了，不用扫码。
- Chrome 不允许对 Default profile 直接做 remote debugging。换个方式 — 用 subprocess 先启动 Chrome（带 debug port），然后 Playwright 连进去：
- WhatsApp Web 通了！但搜索找不到联系人。可能是选择器问题或联系人没存。让我 debug 看看搜索结果：
- 找到了！selector 用 `cell-frame-container` 不是 `listitem`。直接修：


## 2026-05-21 11:48 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 12:11 — TCM-Jessica

### Architecture Decisions
- Still timing out. The issue — `get_incoming_texts()` counts text items but `wait_for_function` counts DOM elements. They return different numbers. Let me use a smarter approach — check the `data-id` of the last message instead of total count:

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）
- 然后告诉我，我就运行。它会用你的 Default profile（shivonnekhoo@gmail.com）直接打开，WhatsApp Web 应该已经登录了，不用扫码。
- Chrome 不允许对 Default profile 直接做 remote debugging。换个方式 — 用 subprocess 先启动 Chrome（带 debug port），然后 Playwright 连进去：
- WhatsApp Web 通了！但搜索找不到联系人。可能是选择器问题或联系人没存。让我 debug 看看搜索结果：
- 找到了！selector 用 `cell-frame-container` 不是 `listitem`。直接修：


## 2026-05-21 12:13 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 12:28 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 12:34 — TCM-Jessica

### Architecture Decisions
- Still timing out. The issue — `get_incoming_texts()` counts text items but `wait_for_function` counts DOM elements. They return different numbers. Let me use a smarter approach — check the `data-id` of the last message instead of total count:

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）
- 然后告诉我，我就运行。它会用你的 Default profile（shivonnekhoo@gmail.com）直接打开，WhatsApp Web 应该已经登录了，不用扫码。
- Chrome 不允许对 Default profile 直接做 remote debugging。换个方式 — 用 subprocess 先启动 Chrome（带 debug port），然后 Playwright 连进去：
- WhatsApp Web 通了！但搜索找不到联系人。可能是选择器问题或联系人没存。让我 debug 看看搜索结果：
- 找到了！selector 用 `cell-frame-container` 不是 `listitem`。直接修：


## 2026-05-21 12:36 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 12:47 — TCM-Jessica

### Architecture Decisions
- Still timing out. The issue — `get_incoming_texts()` counts text items but `wait_for_function` counts DOM elements. They return different numbers. Let me use a smarter approach — check the `data-id` of the last message instead of total count:

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）
- 然后告诉我，我就运行。它会用你的 Default profile（shivonnekhoo@gmail.com）直接打开，WhatsApp Web 应该已经登录了，不用扫码。
- Chrome 不允许对 Default profile 直接做 remote debugging。换个方式 — 用 subprocess 先启动 Chrome（带 debug port），然后 Playwright 连进去：
- WhatsApp Web 通了！但搜索找不到联系人。可能是选择器问题或联系人没存。让我 debug 看看搜索结果：
- 找到了！selector 用 `cell-frame-container` 不是 `listitem`。直接修：


## 2026-05-21 12:47 — TCM-Jessica

### Architecture Decisions
- Still timing out. The issue — `get_incoming_texts()` counts text items but `wait_for_function` counts DOM elements. They return different numbers. Let me use a smarter approach — check the `data-id` of the last message instead of total count:

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）
- 然后告诉我，我就运行。它会用你的 Default profile（shivonnekhoo@gmail.com）直接打开，WhatsApp Web 应该已经登录了，不用扫码。
- Chrome 不允许对 Default profile 直接做 remote debugging。换个方式 — 用 subprocess 先启动 Chrome（带 debug port），然后 Playwright 连进去：
- WhatsApp Web 通了！但搜索找不到联系人。可能是选择器问题或联系人没存。让我 debug 看看搜索结果：
- 找到了！selector 用 `cell-frame-container` 不是 `listitem`。直接修：


## 2026-05-21 12:49 — TCM-Jessica

### Architecture Decisions
- Still timing out. The issue — `get_incoming_texts()` counts text items but `wait_for_function` counts DOM elements. They return different numbers. Let me use a smarter approach — check the `data-id` of the last message instead of total count:

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）
- 然后告诉我，我就运行。它会用你的 Default profile（shivonnekhoo@gmail.com）直接打开，WhatsApp Web 应该已经登录了，不用扫码。
- Chrome 不允许对 Default profile 直接做 remote debugging。换个方式 — 用 subprocess 先启动 Chrome（带 debug port），然后 Playwright 连进去：
- WhatsApp Web 通了！但搜索找不到联系人。可能是选择器问题或联系人没存。让我 debug 看看搜索结果：
- 找到了！selector 用 `cell-frame-container` 不是 `listitem`。直接修：


## 2026-05-21 12:50 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 13:35 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 13:42 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 13:51 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 13:52 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 13:58 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 14:16 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 14:34 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 14:47 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 15:01 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 15:08 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 15:22 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 15:26 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 15:40 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 15:47 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 15:55 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 16:00 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 16:05 — TCM-Jessica

### Architecture Decisions
- Still timing out. The issue — `get_incoming_texts()` counts text items but `wait_for_function` counts DOM elements. They return different numbers. Let me use a smarter approach — check the `data-id` of the last message instead of total count:

### Decisions & Reasoning
- 控制你的浏览器，用你个人号发。适合小规模测试，但要保持浏览器开着。
- 2. 用哪个号发（个人号还是 ChatDaddy 业务号）？
- 明白了。就是用 Playwright 打开你的 WhatsApp Web，自动发测试消息给那个 agent，然后看它怎么回。
- 1. 用你已有的 Chrome Default profile（不用重新登录）
- 然后告诉我，我就运行。它会用你的 Default profile（shivonnekhoo@gmail.com）直接打开，WhatsApp Web 应该已经登录了，不用扫码。
- Chrome 不允许对 Default profile 直接做 remote debugging。换个方式 — 用 subprocess 先启动 Chrome（带 debug port），然后 Playwright 连进去：
- WhatsApp Web 通了！但搜索找不到联系人。可能是选择器问题或联系人没存。让我 debug 看看搜索结果：
- 找到了！selector 用 `cell-frame-container` 不是 `listitem`。直接修：


## 2026-05-21 16:17 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 16:26 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 16:36 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 16:40 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 17:27 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 17:40 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 17:44 — TCM-Jessica

### Decisions & Reasoning
- 你 webhook 进来时就已经有 `accountId` 和 `chatId`，可以**立刻**用这两个 call history。
- **问题是：** 如果用户之前跟 Jessica 聊过、你们换了服务器/清了数据库，或者用户是第一次到 Jessica 但之前在 ChatDaddy inbox 里聊过，本地就没有 history。


## 2026-05-21 17:51 — TCM-Jessica

### Decisions & Reasoning
- 你 webhook 进来时就已经有 `accountId` 和 `chatId`，可以**立刻**用这两个 call history。
- **问题是：** 如果用户之前跟 Jessica 聊过、你们换了服务器/清了数据库，或者用户是第一次到 Jessica 但之前在 ChatDaddy inbox 里聊过，本地就没有 history。
- Q1 最重要 — 第一次从 ChatDaddy 拉到 history 要不要写回本地 CRM？如果写回，下次就有 local history 了，不用每次都 call ChatDaddy。要不要做？


## 2026-05-21 17:55 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 18:08 — TCM-Jessica

### Decisions & Reasoning
- 你 webhook 进来时就已经有 `accountId` 和 `chatId`，可以**立刻**用这两个 call history。
- **问题是：** 如果用户之前跟 Jessica 聊过、你们换了服务器/清了数据库，或者用户是第一次到 Jessica 但之前在 ChatDaddy inbox 里聊过，本地就没有 history。
- Q1 最重要 — 第一次从 ChatDaddy 拉到 history 要不要写回本地 CRM？如果写回，下次就有 local history 了，不用每次都 call ChatDaddy。要不要做？
- - **为什么写回：** ChatDaddy 是 source of truth，写回之后下次 turn 直接用本地，不用每次都 call ChatDaddy API
- | `chatId` | 用户的 WhatsApp JID（对话唯一标识） | `85291234567@s.whatsapp.net` |
- **ChatDaddy 返回的就是这个 chat thread 里的所有消息** — 包括用户发的和 Jessica 发的，按时间排。
- 1. **History 是 per-conversation，不是 per-user** — 如果同一个人用不同手机号发消息，那是两个独立的 `chatId`，history 不会合并
- 2. **Local CRM 用 `phone`（从 `chatId` 提取出来的数字部分）做 key** — 所以本地 CRM 和 ChatDaddy 的 lookup key 其实是不一样的，PRD 里的 `_write_back` 要做一次转换


## 2026-05-21 18:12 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 18:20 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 18:27 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 18:55 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-21 22:17 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 07:40 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 09:03 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 09:12 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 09:47 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 10:16 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 10:18 — TCM-Jessica

### Decisions & Reasoning
- 你 webhook 进来时就已经有 `accountId` 和 `chatId`，可以**立刻**用这两个 call history。
- **问题是：** 如果用户之前跟 Jessica 聊过、你们换了服务器/清了数据库，或者用户是第一次到 Jessica 但之前在 ChatDaddy inbox 里聊过，本地就没有 history。
- Q1 最重要 — 第一次从 ChatDaddy 拉到 history 要不要写回本地 CRM？如果写回，下次就有 local history 了，不用每次都 call ChatDaddy。要不要做？
- - **为什么写回：** ChatDaddy 是 source of truth，写回之后下次 turn 直接用本地，不用每次都 call ChatDaddy API
- | `chatId` | 用户的 WhatsApp JID（对话唯一标识） | `85291234567@s.whatsapp.net` |
- **ChatDaddy 返回的就是这个 chat thread 里的所有消息** — 包括用户发的和 Jessica 发的，按时间排。
- 1. **History 是 per-conversation，不是 per-user** — 如果同一个人用不同手机号发消息，那是两个独立的 `chatId`，history 不会合并
- 2. **Local CRM 用 `phone`（从 `chatId` 提取出来的数字部分）做 key** — 所以本地 CRM 和 ChatDaddy 的 lookup key 其实是不一样的，PRD 里的 `_write_back` 要做一次转换


## 2026-05-22 10:57 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 11:24 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 11:29 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


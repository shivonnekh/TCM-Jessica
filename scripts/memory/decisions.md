
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


## 2026-05-22 11:47 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 13:17 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 13:30 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 13:33 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 13:54 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 14:21 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 14:27 — TCM-Jessica

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


## 2026-05-22 15:21 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 16:22 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-22 16:42 — TCM-Jessica

### Decisions & Reasoning
- 而且你描述的架构 (Planner → 多个 specialist → Final Writer + 平行调用) 跟 Dr. Baba 的 card-driven retrieval pipeline 是**根本不一样**的设计。Fork 出来是对的。
- - 不可变 state + `_ALLOWED_KEYS` whitelist + 每用户 lock — 防止 typo 幽灵字段、防止 WhatsApp 连发的 TOCTOU
- - YAML state-machine engine (`flow_engine.py`) — 把步骤顺序跟逻辑耦合死，真实用户会分叉。Planner 取代它。
- - `pacing.py` 的硬编码 turn counter (「诊断和推荐之间要插 1 个 caring turn」) — 用计数器执行节奏很机械，节奏应该写在 Writer 的 system prompt 里。
- | **C. OpenAI gpt-image-2** (dr-baba 的 Tier 2 primary) | `OPENAI_API_KEY` | 已经 setup，能用，但**不是极梦** |
- **我的诚实建议：用 C (OpenAI gpt-image-2)，原因 3 个：**
- 2. **OpenAI 的中文渲染对汤水 product shot 是够用的**（汤水图片不需要做精确的中文标注，跟 dr-baba 要的解剖图 + 穴位标注不一样）
- 3. **不是终稿** — 这些都是 placeholder，等 Care Plus 给真图就替换掉了。AI 图片在产品页用一周不会出大事，但要先标清楚「示意圖」


## 2026-05-25 10:22 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:


## 2026-05-25 11:43 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:


## 2026-05-25 11:56 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:


## 2026-05-25 12:42 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:


## 2026-05-25 12:59 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |


## 2026-05-25 13:04 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？


## 2026-05-25 14:00 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。


## 2026-05-25 14:34 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"


## 2026-05-25 14:42 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 14:48 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 14:52 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 14:56 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 18:18 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 18:19 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 18:26 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 18:40 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 18:49 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 21:42 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 21:53 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 21:55 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 22:00 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 22:03 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 22:25 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 23:49 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 23:49 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-25 23:59 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 00:02 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 00:03 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 09:44 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 09:56 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 12:13 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 12:17 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 12:27 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 13:19 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 13:56 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:15 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:21 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:22 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:29 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:30 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:38 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:49 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:55 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 14:57 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:04 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:13 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:15 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:16 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:16 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:16 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:16 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:17 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:30 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:33 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:45 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 15:55 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 16:01 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 16:18 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 16:29 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 17:30 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 18:11 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 18:15 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 19:43 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 19:56 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-26 21:12 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：



## 2026-05-26 — Mega session
### Architecture Decisions
- Stay on OpenAI gpt-5.4-mini for entire stack (Planner + Writer + Vision + Specialists). Researched 6 providers; sweet spot for HK Canto + cost budget at 500-user scale.
- Planner = single LLM call doing 3 jobs (route + rephrase + extract pain_points). Cleaner than separate NER step.
- Two-rail pain extraction: LLM NER + keyword fallback. gpt-5.4-mini inconsistently omits the field; deterministic backup ensures CRM gets populated.
- Vision stays on gpt-5.4-mini (not Gemini Pro) — single provider simplicity beats marginal quality gain at ~4 calls/user lifetime.
- Hardcoded acupoint→symptom map was wrong architecture — KB cards + AcupointImageMap own the content. Refactored out.
- Schema column additions REQUIRE `ALTER TABLE ADD COLUMN IF NOT EXISTS`. `CREATE TABLE IF NOT EXISTS` does NOT add new columns to existing tables — caused prod-down today.

### Decisions & Reasoning
- Postgres stays on free until launch (expires 2026-06-20). User wants to wait until launch to decide. Risk: data loss on expiry if not upgraded.
- Writer kept on gpt-5.4-mini, not Sonnet. Sonnet 4.6 with prompt caching would be 90% off but +cost ceiling at current scale. Re-evaluate at 1000+ users.
- 4-day Render auto-deploy outage (webhook broken since 2026-05-22). Workaround = manual deploy via Render API. Permanent fix requires dashboard intervention by user.
- Persona dry-run script (`scripts/persona_dry_run.py`) became a critical pre-deploy validation tool. Found 4 bugs in <2 minutes that tests didn't catch.
- QA agent team parallelism worked: 3 agents in worktrees, each scope-bounded, each commits its own fixes. Merge order = Sales → Constitution → Conversation (least planner conflicts).

## 2026-05-26 23:45 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 09:59 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 10:44 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 10:47 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 11:08 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 11:13 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 11:14 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 11:34 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 11:40 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 11:44 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 12:13 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 13:36 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 13:53 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 14:30 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 14:35 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 14:49 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 15:26 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 15:39 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 15:53 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 15:59 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 17:05 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 17:13 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 17:14 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 17:14 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 17:20 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 17:23 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 17:27 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-27 17:31 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-28 18:08 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-28 18:19 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-29 09:45 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-29 09:59 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-29 10:05 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-29 10:26 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-29 10:46 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-29 10:46 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.


## 2026-05-29 10:52 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.


## 2026-05-29 10:54 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.


## 2026-05-29 10:58 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-29 11:18 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-05-29 11:56 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.


## 2026-05-29 12:35 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:


## 2026-05-29 13:08 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:


## 2026-05-29 13:16 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 13:41 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 13:45 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 13:51 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 14:00 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 14:23 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 14:29 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 14:36 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 14:44 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 14:54 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 14:57 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 15:00 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 15:02 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 15:05 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 15:08 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 15:20 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 15:24 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 16:06 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 18:45 — TCM-Jessica

### Architecture Decisions
- Got the full picture. Clean implementation: buttons are extracted from specialist payload **in the orchestrator** (not by the Writer LLM) and attached to the last bubble in the router. Five files to touch.

### Decisions & Reasoning
- Good — the raw webhook is already being captured. Let me first restore the poll buttons, then update `parse_webhook` to properly extract the selected option from poll vote events instead of dropping them:
- Now fix `parse_webhook` to properly read poll votes instead of dropping them:
- Now update `parse_webhook` to detect poll votes and set those fields instead of trying to extract from the webhook body:


## 2026-05-29 18:46 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 09:32 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 10:22 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 11:01 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 11:06 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 11:39 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 11:49 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 11:51 — TCM-Jessica

### Architecture Decisions
- **`router.py`** — Group messages now split into two paths:


## 2026-06-03 11:52 — TCM-Jessica

### Architecture Decisions
- **`router.py`** — Group messages now split into two paths:


## 2026-06-03 11:55 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 11:57 — TCM-Jessica

### Architecture Decisions
- **`router.py`** — Group messages now split into two paths:


## 2026-06-03 11:58 — TCM-Jessica

### Architecture Decisions
- **`router.py`** — Group messages now split into two paths:


## 2026-06-03 12:14 — TCM-Jessica

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 12:30 — TCM-Jessica

### What Didn't Work (negative knowledge)
- The 400 means `parse_webhook` rejected the payload (likely a non-message event OR the cold-start). I can't see the raw payload because the diagnostic endpoint was removed earlier. The cleanest move: re-add a minimal raw-webhook viewer so I can see **exactly** what ChatDaddy sends for your @-mention. Let me check the capture module:

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 12:41 — TCM-Jessica

### What Didn't Work (negative knowledge)
- The 400 means `parse_webhook` rejected the payload (likely a non-message event OR the cold-start). I can't see the raw payload because the diagnostic endpoint was removed earlier. The cleanest move: re-add a minimal raw-webhook viewer so I can see **exactly** what ChatDaddy sends for your @-mention. Let me check the capture module:

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 12:48 — TCM-Jessica

### What Didn't Work (negative knowledge)
- The 400 means `parse_webhook` rejected the payload (likely a non-message event OR the cold-start). I can't see the raw payload because the diagnostic endpoint was removed earlier. The cleanest move: re-add a minimal raw-webhook viewer so I can see **exactly** what ChatDaddy sends for your @-mention. Let me check the capture module:

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 12:51 — TCM-Jessica

### What Didn't Work (negative knowledge)
- The 400 means `parse_webhook` rejected the payload (likely a non-message event OR the cold-start). I can't see the raw payload because the diagnostic endpoint was removed earlier. The cleanest move: re-add a minimal raw-webhook viewer so I can see **exactly** what ChatDaddy sends for your @-mention. Let me check the capture module:

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 13:30 — TCM-Jessica

### What Didn't Work (negative knowledge)
- The 400 means `parse_webhook` rejected the payload (likely a non-message event OR the cold-start). I can't see the raw payload because the diagnostic endpoint was removed earlier. The cleanest move: re-add a minimal raw-webhook viewer so I can see **exactly** what ChatDaddy sends for your @-mention. Let me check the capture module:

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 13:40 — TCM-Jessica

### What Didn't Work (negative knowledge)
- The 400 means `parse_webhook` rejected the payload (likely a non-message event OR the cold-start). I can't see the raw payload because the diagnostic endpoint was removed earlier. The cleanest move: re-add a minimal raw-webhook viewer so I can see **exactly** what ChatDaddy sends for your @-mention. Let me check the capture module:
- - 6 regression tests including the exact message that broke.

### Architecture Decisions
- **Is this a gap you want to fill?** Because it's actually a good one for TCM — HK weather swings are a natural trigger for health care tips. The architecture for it would be:
- 呢個 split 大概貴 3-5x（但 production query 量低，每個用戶日均幾條 message 而已），可能值得試。要我先 fix 緊嘅產品圖片同功效顯示問題，定先做 model split 實驗？
- Now apply `extracted_pain_points` to CRM. This is the **critical fix**:
- 如果你想 sales 都用 vector，可以做 **hybrid**：keyword 先跑 → 如果 score < threshold 就 fallback 去 vector 搜 product cards。Same pattern as FAQ。
- | **Pain extraction inconsistent** | 🟡 Medium | gpt-5.4-mini 有時 omit `extracted_pain_points`。CRM 最終仍然係 `[]`。要 strengthen prompt 或者用 JSON schema enforcement |
- **Fix E1: Pain extraction fallback** — if LLM omits `extracted_pain_points`, fall back to keyword detection so CRM still gets populated:
- | 2. **辨證**（證型 — 八綱 / 臟腑 / 氣血津液）| ❌ 冇 | 而家**呢一刻嘅 pattern**：肝鬱氣滯 / 脾腎陽虛 / 心脾兩虛 / 痰濕困脾… 真實臨床用嚟開方嘅根據 |
- 2. **No agent does pattern inference** — material in KB, but never extracted into structured form

### Decisions & Reasoning
- | 7 | **情志調理** | 用戶話壓力大 → 自動鏈接對應臟腑 → 推薦湯水 |
- 同天氣廣播共用同一個 6h loop — 唔需要多開任何新嘅 background task。下一個做邊個？節氣提醒定體質複查？
- 全部共用同一個 6h loop，一個 `BROADCAST_ENABLED=true` 開晒。
- `wa.me/85252417448?text=想訂【彭魚鰓解毒湯 HK$120】` — 用戶 click 之後會喺 WhatsApp 開一個 chat 去診所號碼，直接落單。呢個唔係 Jessica 的號碼，所以 Jessica 本身永遠唔知用戶訂咗咩。
- 1. **Purchase CTA 加了一句話** — Jessica 推完產品之後，Writer 現在會加 `「訂完記得話我知呀 😊」`，提示用戶返嚟確認
- 2. **Planner routing** — 用戶回覆 "我訂咗" 類型嘅訊息 → 自動路由去 Sales Agent
- 唯一的 imperfection：我們假設用戶買的是最後被 pitch 的產品（最多 3 款）。如果佢買係更早 pitch 的，會有偏差。但對於 care follow-up 嚟講，"你有冇飲到上次介紹嘅湯" 夠用了。之後如果需要精確，可以讓 Jessica 問 "係邊款呀？"
- 从零搭建了一个 asyncio 后台循环，每 6 小时跑一次，自动给用户发主动关怀消息。共有四种广播类型：


## 2026-06-03 16:44 — TCM-Jessica

### Architecture Decisions
- **`router.py`** — Group messages now split into two paths:

### Decisions & Reasoning
- WhatsApp 的 LID 係 opaque 的，唔係電話號碼，所以無法自動 link。除非用戶自己 DM，我哋才能將兩個 record 合併。現在唔需要擔心呢個 — 只係你要知道有呢個 edge case。


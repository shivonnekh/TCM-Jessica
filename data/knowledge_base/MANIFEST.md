# TCM Knowledge Base Manifest

Generated: 2026-05-21 (ported from dr-baba-agent) — extended 2026-05-27
Source: `/Users/shivonne/Claude Code/dr-baba-agent/data/cards/tcm-wellness-中醫養生/`
Destination: `/Users/shivonne/Claude Code/TCM-Jessica/data/knowledge_base/`

**Total cards:** 71 (52 ported + 19 added 2026-05-27)
- soups: 5
- constitution: 12 (4 original + 8 體質 deep-dives)
- faq: 54 (43 original + 11 added: 三高×3, 七情五臟, 男性×2, 中藥目錄, 24 節氣 + 焦慮 + 鼻敏感 + 皮膚痕)

**辨證 layer**: 6 existing condition cards enriched with 證型 enumeration
(失眠, 頭痛, 胃脹, 便秘, 月經, 感冒), plus 3 new cards added native
with 證型 sections (焦慮, 鼻敏感, 皮膚痕).

## 2026-05-27 KB enhancement push (16 cards)

### 8 constitution deep-dives (王琦《九種體質使用手冊》+ 中華中醫藥學會 ZYYXH/T157-2009):
- `constitution/tcm_constitution_pinghe.json` — 平和質 baseline
- `constitution/tcm_constitution_yangxu.json` — 陽虛質 (手腳冰冷 / 怕凍)
- `constitution/tcm_constitution_yinxu.json` — 陰虛質 (口乾 / 失眠 / 盜汗)
- `constitution/tcm_constitution_tanshi.json` — 痰濕質 (肥胖 / 痰多)
- `constitution/tcm_constitution_shire.json` — 濕熱質 (暗瘡 / 口苦)
- `constitution/tcm_constitution_xueyu.json` — 血瘀質 (經痛 / 暗沉)
- `constitution/tcm_constitution_qiyu.json` — 氣鬱質 (情緒鬱悶)
- `constitution/tcm_constitution_tebing.json` — 特稟質 (過敏體質)

### 3 三高 cards (Medical, Level B review needed):
- `faq/tcm_diabetes.json` — 糖尿病 / 消渴症
- `faq/tcm_hypertension.json` — 高血壓
- `faq/tcm_cholesterol.json` — 高膽固醇 / 高血脂

### Other gap-fill cards:
- `faq/tcm_seven_emotions.json` — 七情五臟（怒/喜/思/憂悲/恐/驚 → 五臟）
- `faq/tcm_mens_kidney_health.json` — 男性腎陽虛 / 腎陰虛
- `faq/tcm_mens_prostate_urinary.json` — 前列腺 / 尿頻（red-flag escalation）
- `faq/tcm_herbs_directory.json` — 40 味常用中藥目錄
- `faq/tcm_24_solar_terms.json` — 24 節氣養生（broadcaster 用）

### 辨證 layer additions (2026-05-27 second push):

**3 new cards with native 證型 enumeration:**
- `faq/tcm_anxiety_emotional.json` — 焦慮 / 鬱悶 (4 patterns: 肝鬱氣滯 / 心脾兩虛 / 痰火擾心 / 心腎不交) + 撒瑪利亞會 escalation
- `faq/tcm_nose_allergy.json` — 鼻敏感 (4 patterns: 肺氣虛 / 脾氣虛 / 腎陽虛 / 肺經鬱熱) + 三伏/三九天灸
- `faq/tcm_skin_itch.json` — 皮膚痕癢 (5 patterns: 風熱 / 風寒 / 血虛風燥 / 濕熱 / 血熱) + anaphylaxis 999 escalation

**6 existing condition cards enriched with 【臨床辨證 — 證型細分】 section:**
- `faq/tcm_sleep_insomnia.json` — 5 patterns: 心脾兩虛 / 陰虛火旺 / 肝鬱化火 / 胃不和 / 痰熱擾心
- `faq/tcm_headache_migraine.json` — 5 patterns: 肝陽上亢 / 風寒外襲 / 血虛 / 痰濁阻竅 / 瘀血阻絡
- `faq/tcm_digestion_bloating.json` — 4 patterns: 脾虛 / 肝鬱犯脾 / 食滯 / 濕困中焦
- `faq/tcm_digestion_stool.json` — 4 patterns: 脾虛 / 腸燥津枯 / 氣滯 / 陽虛便秘
- `faq/tcm_womens_menstrual.json` — 4 patterns: 氣滯血瘀 / 寒凝胞宮 / 氣血兩虛 / 濕熱蘊結
- `faq/tcm_cold_flu_prevention.json` — added 氣虛感冒 / 陰虛感冒 (already had 風寒/風熱/暑濕)

These 9 cards together support the new Planner辨證 inference (gpt-4o emits
`inferred_patterns` per turn → pipeline persists to `user.observed_patterns`
→ Writer surfaces with advisory language when confidence ≥0.7).

**Skipped (paid product cards — handled by a different system):**
- `tcm_paid_soups.json`
- `tcm_paid_ointments.json`

## Card Schema

All cards share a top-level `knowledge_card` wrapper with the following keys:
- `metadata` — card_id, version, last_updated, etc.
- `overview` — title, objective, patient_profile, trigger_conditions
- `core_content` — core_answer, supporting_points, evidence_level, next_best_question
- `execution_logic`
- `references`

Two outliers with one extra non-standard top-level key (benign):
- `faq/tcm_evidence_science.json` — adds `knowledge_card_version`
- `faq/tcm_treatment_shoulder_neck.json` — adds `knowledge_card_note`

## Domain: `soups` (5 cards)

| File | Card ID | Topic | Version | Last Updated | Size |
|------|---------|-------|---------|--------------|------|
| `soups/tcm_food_therapy_products.json` | `tcm_food_therapy_products` | 市售中醫產品分析：枇杷膏、龍角散、便利店食療 | 1 | 2026-03-31 | 4.6 KB |
| `soups/tcm_food_therapy_seasonal.json` | `tcm_food_therapy_seasonal` | 季節飲食指南：秋冬潤燥、食物宜忌、病中飲食 | 1 | 2026-03-31 | 4.9 KB |
| `soups/tcm_food_therapy_soups.json` | `tcm_food_therapy_soups` | 中醫湯水指南：按9大體質配湯 — HK 中醫師食譜 + 芳姐保健湯餸 28 款，連材料、做法、飲用方法、頻率、禁忌 | 4 | 2026-05-09 | 28.7 KB |
| `soups/tcm_food_therapy_soups_top100.json` | `tcm_food_therapy_soups_top100` | 芳姐保健湯餸 100 款家常食療精選 — 按 9 大體質分類（連圖片） | 1 | 2026-05-08 | 58.6 KB |
| `soups/tcm_food_therapy_teas.json` | `tcm_food_therapy_teas` | 中醫茶飲指南：茶葉、涼茶、花茶按體質選擇 | 1 | 2026-03-31 | 4.7 KB |

## Domain: `constitution` (4 cards)

| File | Card ID | Topic | Version | Last Updated | Size |
|------|---------|-------|---------|--------------|------|
| `constitution/tcm_constitution_assessment.json` | `tcm_constitution_assessment` | 中醫體質自我評估：九種體質分類與調理 | 1 | 2026-04-14 | 9.1 KB |
| `constitution/tcm_dampness_removal.json` | `tcm_dampness_removal` | 去濕氣：濕氣症狀、成因與去濕食療 | 1 | 2026-03-31 | 4.7 KB |
| `constitution/tcm_education_concepts.json` | `tcm_education_concepts` | 中醫基礎概念：體質、氣血、五臟、陰陽 | 1 | 2026-03-31 | 5.6 KB |
| `constitution/tcm_fatigue_qi_deficiency.json` | `tcm_fatigue_qi_deficiency` | 氣虛疲勞：補氣食療、熬夜傷害與提神方法 | 1 | 2026-03-31 | 5.2 KB |

## Domain: `faq` (43 cards)

| File | Card ID | Topic | Version | Last Updated | Size |
|------|---------|-------|---------|--------------|------|
| `faq/tcm_acupressure_beauty.json` | `tcm_acupressure_beauty` | 美容穴位：瘦面、亮膚、去黑眼圈 | 1 | 2026-03-31 | 6.2 KB |
| `faq/tcm_acupressure_energy_stress.json` | `tcm_acupressure_energy_stress` | 提神減壓穴位：精神、社交焦慮、口氣 | 1 | 2026-03-31 | 6.0 KB |
| `faq/tcm_acupressure_pain.json` | `tcm_acupressure_pain` | 止痛穴位：肩頸、經痛、眼疲勞 | 1 | 2026-03-31 | 6.4 KB |
| `faq/tcm_acupressure_weight_slim.json` | `tcm_acupressure_weight_slim` | 消脂瘦身穴位：止餓、纖腿、消水腫 | 1 | 2026-03-31 | 4.8 KB |
| `faq/tcm_children_health.json` | `tcm_children_health` | 小朋友中醫保健：兒童常見體質調理、食療、小兒推拿同安全須知 | 1 | 2026-04-14 | 11.7 KB |
| `faq/tcm_cold_flu_prevention.json` | `tcm_cold_flu_prevention` | 中醫感冒預防與自我護理：風寒、風熱、暑濕分型 | 1 | 2026-04-13 | 6.8 KB |
| `faq/tcm_dark_circles_clinical_treatments.json` | `tcm_dark_circles_clinical_treatments` | 黑眼圈嘅中醫臨床療程：美顏針、面部拔罐、面部刮痧、面部針灸 | 1 | 2026-04-30 | 6.9 KB |
| `faq/tcm_dark_circles_food_therapy.json` | `tcm_dark_circles_food_therapy` | 黑眼圈嘅中醫食療：杞子茶、紅棗水、黑芝麻糊、黑豆湯，按體質揀啱先有效 | 1 | 2026-04-30 | 6.2 KB |
| `faq/tcm_dark_circles_lifestyle.json` | `tcm_dark_circles_lifestyle` | 黑眼圈嘅生活習慣調理：早瞓、減屏幕、護肝、護腎習慣 | 1 | 2026-04-30 | 6.3 KB |
| `faq/tcm_digestion_bloating.json` | `tcm_digestion_bloating` | 腹脹胃氣與食滯：即時緩解和預防方法 | 1 | 2026-03-31 | 4.3 KB |
| `faq/tcm_digestion_stool.json` | `tcm_digestion_stool` | 腸胃健康：大便狀態解讀、消化問題與食療 | 1 | 2026-03-31 | 4.2 KB |
| `faq/tcm_drug_interactions.json` | `tcm_drug_interactions` | 中西藥相互作用：中藥同西藥一齊食嘅風險 | 1 | 2026-04-14 | 9.6 KB |
| `faq/tcm_education_myths.json` | `tcm_education_myths` | 中醫迷思拆解：苦藥、排毒、出汗、流汗 | 1 | 2026-03-31 | 4.8 KB |
| `faq/tcm_elderly_digestion_deep.json` | `tcm_elderly_digestion_deep` | 長者腸胃調理：食物選擇、舌診自測、中西藥衝突安全 | 1 | 2026-04-22 | 12.9 KB |
| `faq/tcm_elderly_wellness.json` | `tcm_elderly_wellness` | 長者養生：中醫調理、防跌穴位、食療與認知保健 | 1 | 2026-04-14 | 9.3 KB |
| `faq/tcm_evidence_science.json` | `tcm_evidence_science` | 中醫嘅科學證據：針灸、穴位、中藥、經絡、安全性 | 1 | 2026-04-22 | 16.3 KB |
| `faq/tcm_facial_beauty_treatments.json` | `tcm_facial_beauty_treatments` | 中醫面部美容療法：美顏針、面部拔罐、中藥面膜 | 1 | 2026-04-29 | 6.7 KB |
| `faq/tcm_headache_migraine.json` | `tcm_headache_migraine` | 中醫頭痛：類型辨別、穴位按摩、食療同警訊 | 1 | 2026-04-22 | 8.1 KB |
| `faq/tcm_integrative_oncology.json` | `tcm_integrative_oncology` | 中醫輔助腫瘤學：中醫在癌症治療中的角色 | 1 | 2026-03-31 | 5.7 KB |
| `faq/tcm_postpartum_confinement.json` | `tcm_postpartum_confinement` | 產後調理 / 坐月：生化湯、惡露、催乳、安全守則 | 1 | 2026-04-22 | 14.6 KB |
| `faq/tcm_pregnancy_safety.json` | `tcm_pregnancy_safety` | 懷孕期間中醫安全：禁忌中藥、穴位與安全食療 | 1 | 2026-04-13 | 6.7 KB |
| `faq/tcm_red_flags.json` | `tcm_red_flags` | 中醫自我保健邊界：何時必須就醫 | 1 | 2026-03-31 | 4.1 KB |
| `faq/tcm_seasonal_autumn_winter.json` | `tcm_seasonal_autumn_winter` | 秋冬養生：潤燥養肺、補腎防寒、季節食療全攻略 | 1 | 2026-04-14 | 8.5 KB |
| `faq/tcm_seasonal_spring_summer.json` | `tcm_seasonal_spring_summer` | 春夏養生：養肝清暑、節氣食療與香港濕熱對策 | 1 | 2026-04-14 | 10.3 KB |
| `faq/tcm_service_navigation.json` | `tcm_service_navigation` | 香港中醫服務導航：註冊資格、收費、保險、HA中醫診所 | 1 | 2026-04-22 | 8.5 KB |
| `faq/tcm_skin_acne_complexion.json` | `tcm_skin_acne_complexion` | 中醫皮膚護理：暗瘡、膚色、面部診斷 | 1 | 2026-03-31 | 5.0 KB |
| `faq/tcm_skin_hair_loss.json` | `tcm_skin_hair_loss` | 中醫脫髮：原因分析與調理 | 1 | 2026-03-31 | 4.2 KB |
| `faq/tcm_sleep_insomnia.json` | `tcm_sleep_insomnia` | 中醫失眠：原因分析、安神食療與穴位 | 1 | 2026-03-31 | 5.1 KB |
| `faq/tcm_tongue_diagnosis.json` | `tcm_tongue_diagnosis` | 中醫舌診：睇條脷了解你嘅體質 | 1 | 2026-05-08 | 5.5 KB |
| `faq/tcm_treatment_acupuncture.json` | `tcm_treatment_acupuncture` | 針灸療程介紹：適合人士、療程設計、過程體驗、療效預期、禁忌（WHO + Cochrane 認可） | 2 | 2026-05-04 | 12.9 KB |
| `faq/tcm_treatment_cosmetic_acupuncture.json` | `tcm_treatment_cosmetic_acupuncture` | 美顏針（美容針灸）介紹：適合人士、療程設計、預期效果、證據限制 | 1 | 2026-05-04 | 10.1 KB |
| `faq/tcm_treatment_cupping.json` | `tcm_treatment_cupping` | 拔罐療程介紹：火罐 vs 真空罐、4 種手法（留/走/閃/刺絡）、罐印解讀、禁忌 | 1 | 2026-05-04 | 10.2 KB |
| `faq/tcm_treatment_guasha.json` | `tcm_treatment_guasha` | 刮痧療程介紹：適合症狀、操作方法、痧痕解讀、禁忌（HK 註冊中醫師資料） | 1 | 2026-05-04 | 8.5 KB |
| `faq/tcm_treatment_menstrual_program.json` | `tcm_treatment_menstrual_program` | 調經療程介紹：月經周期療法（4 階段）、針灸+中藥組合、療程設計（HKU + Cochrane） | 1 | 2026-05-04 | 10.8 KB |
| `faq/tcm_treatment_moxibustion.json` | `tcm_treatment_moxibustion` | 艾灸療程介紹：5 種類型、適合人士、禁忌、HK 火警條例下嘅實際操作 | 1 | 2026-05-04 | 9.8 KB |
| `faq/tcm_treatment_shoulder_neck.json` | `tcm_treatment_shoulder_neck` | 肩頸治療療程介紹：針灸 + 推拿 + 拔罐組合、典型 12 次療程、五十肩 WHO 認可治療 | 1 | 2026-05-04 | 11.0 KB |
| `faq/tcm_treatment_sleep_program.json` | `tcm_treatment_sleep_program` | 睡眠調理療程介紹：5 個失眠證型、針灸+中藥組合、典型 12 次療程（Frontiers SR + HKU Med） | 1 | 2026-05-04 | 10.3 KB |
| `faq/tcm_treatment_slimming_program.json` | `tcm_treatment_slimming_program` | 瘦身調理療程介紹：針灸 + 穴位埋線 + 耳穴、必須配合飲食運動（誠實聲明） | 1 | 2026-05-04 | 11.3 KB |
| `faq/tcm_urban_lifestyle.json` | `tcm_urban_lifestyle` | 都市生活養生：手腳冰冷、過敏鼻炎、肺健康 | 1 | 2026-03-31 | 5.5 KB |
| `faq/tcm_urban_office_pain.json` | `tcm_urban_office_pain` | 都市上班族健康：肩頸腰背、眼疲勞、久坐傷害 | 1 | 2026-03-31 | 5.5 KB |
| `faq/tcm_weight_management.json` | `tcm_weight_management` | 中醫減重：消脂茶、食物搭配、食滯處理 | 1 | 2026-03-31 | 4.4 KB |
| `faq/tcm_womens_hormonal.json` | `tcm_womens_hormonal` | 女性荷爾蒙與中醫：更年期、內分泌、骨盆健康 | 1 | 2026-03-31 | 4.5 KB |
| `faq/tcm_womens_menstrual.json` | `tcm_womens_menstrual` | 女性月經健康：經痛、PMS、月經後調補 | 1 | 2026-03-31 | 5.7 KB |

## Notes & Observations

- All 51 JSON files parse as valid JSON.
- Schema is highly consistent — 50/51 cards share identical top-level keys; 2 have one benign additional annotation key.
- **Potential overlap (not duplication):** `soups/tcm_food_therapy_soups.json` (28 curated recipes, mixed sources incl. HK registered TCM doctors) and `soups/tcm_food_therapy_soups_top100.json` (100 home recipes from healthy-food.hk only) both draw partly from 芳姐保健湯餸 but have different scope and purpose.
- **Intentionally separate but related:** `faq/tcm_urban_office_pain.json` (self-care for office workers) vs. `faq/tcm_treatment_shoulder_neck.json` (clinical program). The latter card explicitly notes this distinction in `knowledge_card_note`.
- All cards versioned v1 except `tcm_food_therapy_soups.json` (v4) and `tcm_treatment_acupuncture.json` (v2).
- Last-updated dates span 2026-03-31 to 2026-05-09. No obviously stale cards (oldest is ~2 months at time of manifest generation).

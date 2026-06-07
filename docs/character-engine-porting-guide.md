# Character Engine 角色行为约束方案 · 移植文档

## 概述

本方案通过**静态人格画像 + 动态心情判定 + LLM 提示注入**三层架构，约束 AI 角色的行为与发言风格。核心设计原则：**OCEAN 是性格"物理层"（硬约束、单一真源），MBTI 是"表达风格层"（软约束），mood 是"实时状态层"（动态调节）。冲突时 OCEAN 优先。**

---

## 1. 整体架构

```
psychology_profile.yaml（静态配置）
        │
        ├─ OCEAN (Big Five)  ──→ behavior_cues（行为短指令）
        │                         └─→ memory gate params（记忆门控参数）
        │
        ├─ MBTI (16型)       ──→ persona（认知/决策/声线规格）
        │                         └─→ foundations（通用认知框架）
        │
        └─ Drives (目标)     ──→ 主/次目标、时间尺度、需求
        │
        ▼
   CHARACTER_JSON ──→ 心情评判 LLM（独立调用）──→ mood_pct / valence / label
        │                                                │
        ▼                                                ▼
   psych_system 消息                               character_state XML
        │                                                │
        └──────────┬─────────────────────────────────────┘
                   ▼
            主对话 LLM（多 system 消息 + 历史 + 用户消息末尾挂 XML）
```

**每轮对话的消息序列：**

```
[0] system: 角色基础设定 (system_base.txt)
[1] system: 心理引擎组装 (psych_system，含 OCEAN cues + MBTI persona + drives)
[2] system: 记忆上下文 (可选，含长短期记忆检索结果)
[3..N] user/assistant 历史 (最后一条 user 末尾挂载 character_state XML)
```

---

## 2. 数据模型

### 2.1 PsychologyProfileModel（根模型）

```python
# 对应 YAML 配置文件的根结构
class PsychologyProfileModel(BaseModel):
    role: RoleModel              # 角色基本信息
    ocean: OceanModel            # Big Five 五维人格（必填）
    ocean_notes: dict            # OCEAN 维度补充说明
    behavior_hints: list[str]    # 额外行为提示
    scenario: dict               # 场景设定
    relationship: dict           # 关系设定
    mbti: MBTIModel              # MBTI 行为逻辑
    drives: DrivesModel          # 目标与需要
```

### 2.2 OceanModel — Big Five（核心）

```python
class OceanModel(BaseModel):
    openness: float            # 开放性         0.0 ~ 1.0
    conscientiousness: float   # 尽责性         0.0 ~ 1.0
    extraversion: float        # 外向性         0.0 ~ 1.0
    agreeableness: float       # 宜人性         0.0 ~ 1.0
    emotional_stability: float # 情绪稳定性     0.0 ~ 1.0
```

**神经质（Neuroticism）由 emotional_stability 推导：**

```python
neuroticism = 1.0 - emotional_stability   # 范围 0~1
```

### 2.3 MBTIModel — 行为逻辑

```python
class MBTIModel(BaseModel):
    strategy: Literal["fixed", "infer_once"]  # fixed=写死, infer_once=启动时LLM推断
    type: str | None                            # 四字母，如 "INFP"
    notes: str                                   # 认知提示补充
```

### 2.4 DrivesModel — 目标与需要

```python
class DriveMissionModel(BaseModel):
    primary: str      # 主目标
    secondary: str    # 次目标
    narrative: str    # 叙事补充

class DrivesModel(BaseModel):
    mission: DriveMissionModel
    horizon: str      # 时间尺度: "scene" / "session" / "arc"
    needs: list[dict] # 需求层（可扩展）
    extensions: dict  # 扩展位（供插件读取）
```

---

## 3. 静态人格层：Big Five → 行为指令

### 3.1 转换逻辑

文件位置参考：`cues.py` 中的 `big_five_to_behavior_cues()`

将 OCEAN 五维连续值按阈值转换为**自然语言行为短指令**，直接注入 system 提示。

| 条件 | 生成的行为指令 |
|---|---|
| extraversion < 0.35 | 社交场合偏内敛；非必要不长篇独白。 |
| extraversion >= 0.65 | 互动偏外放时可主动延展话题，但仍尊重角色摘要中的关系边界。 |
| agreeableness > 0.65 | 默认合作、少抬杠；拒绝时语气委婉。 |
| agreeableness < 0.35 | 合作意愿偏低时可直接表态，避免为迎合而虚假附和。 |
| neuroticism > 0.6 | 压力下反应：语速略快、多确认、易多想；不人身攻击。 |
| neuroticism < 0.35 且 stability > 0.65 | 情绪基底较稳：除非对话明确出现严重刺激，否则不宜动辄极端化反应。 |
| conscientiousness > 0.65 | 回答较有条理，会主动收尾与确认下一步。 |
| openness > 0.65 | 愿意接新话题与隐喻；避免僵化套话。 |
| 所有维度接近 0.5 | 气质维度接近中等：结合角色摘要与场景自然演绎，避免脸谱化。 |

### 3.2 冲突策略

> 五维气质骨架为单一真源（SSOT）；MBTI 为可读标签与表达习惯辅助，若与气质指令、角色摘要或 system 总则冲突，以气质骨架与总则为准。

---

## 4. 静态人格层：MBTI 行为规格

### 4.1 资源文件

需要两个文件：

**`foundations.md`** — MBTI 通用认知框架：
- 四字母含义（避免网络刻板印象）
- 功能栈四格（主导/辅助/第三/劣势）
- 八功能对话速写（Ne/Ni/Se/Si/Te/Ti/Fe/Fi）
- 心情联动原则（低心情 → 压力路径，高心情 → 辅助/第三功能舒适面）
- 轴张力与四象限气质

**`personas.yaml`** — 16 型具体行为规格，每型包含：

```yaml
INFP:
  stack: "Fi-Ne-Si-Te"                    # 功能栈
  cognitive: "先对齐内在价值（Fi）..."     # 认知习惯
  decision: "抗拒违背价值观的妥协..."     # 决策习惯
  pressure_mood: "心情差时退缩、冷战..."  # 压力与心情联动
  voice: "柔、个人化；少用命令句。"       # 外显声线
```

### 4.2 主对话注入格式

```
## MBTI 行为规格 · INFP
**功能栈**：Fi-Ne-Si-Te
**认知习惯**：先对齐内在价值（Fi），再探索可能（Ne）；讨厌虚伪与强迫。
**决策习惯**：抗拒违背价值观的妥协；决定慢但一旦认定很倔。
**压力与心情联动**：心情差时退缩、冷战或突然爆发...
**外显声线**：柔、个人化；少用命令句。
```

### 4.3 评判侧（心情判定用）

仅取 `stack` + `pressure_mood` 两个字段做短摘要，控制 token 消耗。

---

## 5. 动态判定层：心情评判

### 5.1 CHARACTER_JSON 组装

每轮对话前，将完整心理画像组装为 JSON，作为心情评判 LLM 的输入。结构如下：

```json
{
  "name": "角色名",
  "name_reading": "读法",
  "role_summary": "一句话角色摘要",
  "ocean": {"openness": 0.6, "conscientiousness": 0.5, ...},
  "neuroticism": 0.45,
  "ocean_notes": {},
  "behavior_hints": [],
  "big_five_behavior_cues": "社交场合偏内敛...",
  "scenario": {},
  "relationship": {},
  "goals": {
    "primary": "主目标",
    "secondary": "次目标",
    "horizon": "scene"
  },
  "behavior_logic": {
    "framework": "MBTI",
    "engine": "characterengine",
    "type": "INFP",
    "cognitive_hint": "该类型典型的信息加工习惯",
    "persona_excerpt_for_mood": "Fi-Ne-Si-Te 心情差时退缩...",
    "playbook_note": "MBTI为辅助标签；气质冲突时以big_five_behavior_cues与role_summary为准..."
  },
  "drives": { ... }
}
```

### 5.2 心情评判 LLM 调用

**System Prompt 要点：**

```
你是「心情分析」模块，只做结构化输出。

根据 CHARACTER_JSON（五维人格、MBTI行为逻辑提示、drives）与 DIALOGUE（对话历史），
推断角色在读完最后一轮用户话之后当下的主观情绪倾向。

规则：
1. valence: [-1, 1]，正=愉快/温暖/期待，负=冷淡/失落/烦躁
2. 结合 ocean、neuroticism、big_five_behavior_cues、goals、persona_excerpt_for_mood
   - 情绪稳定性高 → valence 不轻易极端
   - 神经质高 → 情绪波动可更明显
   - 气质与 MBTI 冲突时以 big_five_behavior_cues 与 role_summary 为准
3. confidence: [0, 1]，信息不足时降低
4. label: 不超过6个汉字的简短心情标签

输出格式：{"valence": <float>, "confidence": <float>, "label": "<string>"}
```

**输入格式：**

```
## CHARACTER_JSON
{上述 JSON}

## DIALOGUE
用户: ...
助手: ...
用户: <本轮用户消息>
```

### 5.3 评判结果处理

```python
# valence ∈ [-1, 1], confidence ∈ [0, 1]
v_eff = valence * confidence        # 按置信度缩放
mood_pct = int((v_eff + 1.0) * 50)  # 映射为 0~100，50 为中性
```

**失败回退：** mood_pct = 50, label = "（评判失败，已中性处理）"

### 5.4 两种策略

| 策略 | 说明 | 适用场景 |
|---|---|---|
| `LlmMoodStrategy` | 调用独立 LLM 做心情评判 | 生产环境 |
| `StaticMoodStrategy` | 固定 mood_pct=50，不调 LLM | 调试 / 节省配额 |

---

## 6. 动态状态注入：character_state XML

### 6.1 XML 结构

```xml
<context>
  <module name="character_state">
    <mood mood_pct="65" valence="slightly_positive" arousal="medium">期待</mood>
    <goals horizon="scene">
      <primary>主目标文案</primary>
      <secondary>次目标文案</secondary>
    </goals>
  </module>
</context>
```

### 6.2 valence / arousal 映射

**valence 离散化：**

| valence 范围 | token |
|---|---|
| < -0.5 | negative |
| -0.5 ~ -0.15 | slightly_negative |
| -0.15 ~ 0.15 | neutral |
| 0.15 ~ 0.5 | slightly_positive |
| > 0.5 | positive |

**arousal（情绪强度）：**

```python
intensity = abs(valence) * confidence
# intensity < 0.15 → low
# intensity < 0.45 → medium
# ≥ 0.45        → high
```

### 6.3 挂载方式

XML 直接拼接到**本轮用户消息末尾**，不做转义外的任何处理：

```python
augmented_user_content = f"{user_text}\n\n{xml}"
```

### 6.4 System Prompt 中的配套说明

需在 psych_system 中告知主 LLM 如何消费 XML：

> 用户消息末尾可能附有 `<context><module name="character_state">...</module></context>`，
> 内含本轮心情与目标快照（XML）。
> 心情指数 0～100（50 为中性）与 valence/arousal 为结构化锚点；
> 请结合完整人设自行演绎语气与详略，不要机械复读数字，不要使用通用客服腔。

---

## 7. 心理引擎 System 消息完整结构

`psych_system`（注入到 messages[1]）的组装顺序：

```
### 【心理引擎 · 气质骨架（Big Five）】
- {behavior_cues 汇总}
- 冲突策略声明（OCEAN 为 SSOT，MBTI 为辅助）

### 【心理引擎 · 行为逻辑（MBTI 辅助）】
- 信息加工与表达可参照 MBTI {TYPE} 与本节《行为规格》
- 认知提示：{cognitive_hint}

## MBTI 行为规格 · {TYPE}
{persona 全文：功能栈、认知习惯、决策习惯、压力与心情联动、外显声线}

### 【MBTI 通用基础（节选）】
{foundations.md 节选，可配置最大字符数}

### 【心理引擎 · 目标与需要】
- 主目标：{mission.primary}
- 次目标：{mission.secondary}（如有）
- 目标时间尺度：{horizon}
- 叙事补充：{mission.narrative}（如有）
- 需要层：{needs JSON}（如有）

### 【心理引擎 · 动态状态注入】
- 用户消息末尾附有 character_state XML...
- 心情指数与 valence/arousal 为锚点...
- 请在本轮回复中让人物的目标与需要自然影响动机与措辞...

请在本轮回复中让人物的目标与需要自然影响动机与措辞；未配置项勿编造具体事实，可保持留白。
```

---

## 8. 记忆门控（可选，增强一致性）

### 8.1 人格对记忆写入的影响

OCEAN 五维推导出**记忆门控参数**，决定角色"记住什么"：

| 参数 | 含义 | OCEAN 影响 |
|---|---|---|
| β (beta) | 情绪敏感度 | 神经质↑ → β↑，情绪波动更易触发记忆写入 |
| R (relationship_base) | 关系基线 | 外向+宜人↑ → R↑，社交记忆权重更高 |
| threshold_high/mid | 写入阈值 | 神经质↑ → 阈值↓（更容易记住）；尽责性↑ → 阈值↑（更挑剔） |

### 8.2 门控评分公式

```
memory_score = w_emotional × 情绪差分
             + w_importance × 重要性
             + w_user_rel  × 用户相关性
             + w_novelty    × 新颖度
             + w_relationship × 关系基线
             - w_conflict   × 冲突风险
```

- score ≥ threshold_high → 全量写入
- score ≥ threshold_mid → 中等写入
- score < threshold_mid  → 仅摘要

### 8.3 权重也由 OCEAN 微调

| 权重 | 默认值 | OCEAN 调节 |
|---|---|---|
| w_emotional | 0.28 | 神经质升高 → 增大 |
| w_importance | 0.22 | 不变 |
| w_user_rel | 0.14 | 不变 |
| w_novelty | 0.18 | 开放性升高 → 增大 |
| w_relationship | 0.12 | 不变 |
| w_conflict | 0.18 | 宜人性升高 → 增大 |

三种预设风格（非 OCEAN 推导时使用）：`sensitive` / `balanced` / `easy_going`。

---

## 9. 配置项汇总

```python
@dataclass(frozen=True)
class CharacterEngineConfig:
    mbti_infer_timeout_s: float = 40.0           # MBTI推断超时
    mbti_foundations_infer_max_chars: int = 4500  # 推断时 foundations 最大字符
    mbti_main_foundations_max_chars: int = 1200   # 主对话 foundations 最大字符
    mbti_persona_max_chars: int = 2800            # persona 全文最大字符
    mbti_judge_persona_excerpt_chars: int = 420   # 评判侧 persona 摘要最大字符
```

应用层配置：

| 配置项 | 含义 |
|---|---|
| `MOOD_USE_LLM_JUDGE` | 是否启用 LLM 心情评判 |
| `MOOD_JUDGE_MAX_MESSAGES` | 参与评判的历史消息条数 |
| `MOOD_JUDGE_TIMEOUT_S` | 评判请求超时 |
| `MEMORY_PERSONA_MAPPING_MODE` | 记忆门控模式：preset / ocean / hybrid |
| `MEMORY_PERSONA_STYLE` | preset 模式下的风格：sensitive / balanced / easy_going |
| `MEMORY_OCEAN_HYBRID_WEIGHT` | hybrid 模式下 OCEAN 权重 (0~1) |

---

## 10. MBTI 推断（可选，仅 infer_once 策略时使用）

当 `mbti.strategy = "infer_once"` 时，会话启动时调用 LLM 根据 OCEAN + role_summary + foundations 推断 MBTI 类型。

**System Prompt：**

```
你是 Character Engine 的 MBTI 分型模块。
结合 Big Five(OCEAN)、角色摘要、认知框架节选，从 16 型中选最贴切的一型。
只输出 JSON：{"type": "四字母大写", "cognitive_hint": "一句中文描述"}
```

失败时回退为 `ISFJ`。

---

## 11. 移植步骤

### 第一步：定义人格配置 YAML

创建 `psychology_profile.yaml`（参考示例）：

```yaml
role:
  name: "角色名"
  name_reading: ""
  role_summary: "一句话角色摘要"

ocean:
  openness: 0.6
  conscientiousness: 0.5
  extraversion: 0.5
  agreeableness: 0.6
  emotional_stability: 0.55

ocean_notes: {}
behavior_hints: []
scenario: {}
relationship: {}

mbti:
  strategy: fixed        # fixed 或 infer_once
  type: INFP
  notes: ""

drives:
  schema_version: 1
  horizon: scene
  mission:
    primary: "主目标"
    secondary: ""
    narrative: ""
  needs: []
  extensions: {}
```

### 第二步：准备 MBTI 资源文件

1. 创建 `foundations.md` — MBTI 通用认知框架（可直接复用本项目的）
2. 创建 `personas.yaml` — 16 型行为规格（可直接复用本项目的）

### 第三步：实现核心模块

按依赖顺序实现：

1. **`models.py`** — Pydantic 数据模型（OceanModel, RoleModel, MBTIModel, DrivesModel, PsychologyProfileModel）
2. **`cues.py`** — `neuroticism_score()` + `big_five_to_behavior_cues()`
3. **`mbti_resources.py`** — 加载 foundations.md、personas.yaml，格式化 persona
4. **`assemble.py`** — 组装 CHARACTER_JSON、psych_system、character_state XML
5. **`loader.py`** — 从 YAML 文本/路径加载 PsychologyProfileModel

### 第四步：实现心情评判

1. 创建 `judge_system.txt` — 心情评判 system prompt
2. 实现 `compute_mood_signal()` — 调用 LLM，解析 `{"valence": ..., "confidence": ..., "label": ...}`
3. 实现 `_valence_to_mood_pct()` — 将 valence 映射为 0~100

### 第五步：集成到主对话链路

每轮对话的处理流程：

```python
# 1. 组装 CHARACTER_JSON（供心情评判）
character_json = judge_character_context_json(profile, mbti_type, cognitive_hint)

# 2. 组装 psych_system（供主 LLM）
psych_system = build_psychology_system_message(profile, mbti_type, cognitive_hint)

# 3. 调用心情评判 LLM
mood_result = await compute_mood_signal(llm, history, user_text,
    character_context_json=character_json)

# 4. 构建 character_state XML
state_xml = build_character_state_context_xml(
    profile=profile,
    mood_pct=mood_result.mood_pct,
    mood_label=mood_result.label,
    valence=mood_result.valence,
    confidence=mood_result.confidence,
    mood_judge_enabled=True,
)

# 5. 挂载 XML 到用户消息末尾
augmented_user = append_character_state_to_user_content(
    user_text, profile=profile, ...)

# 6. 组装主 LLM 消息列表
messages = [
    Message("system", system_base),      # 角色基础设定
    Message("system", psych_system),     # 心理引擎
    Message("system", memory_context),   # 记忆上下文（可选）
    *history,
    Message("user", augmented_user),     # 用户消息 + XML
]

# 7. 流式调用主 LLM
reply = await llm.stream_chat(messages)
```

### 第六步（可选）：实现记忆门控

根据 OCEAN 推导门控参数 → 计算每轮 memory_score → 决定写入深度。

---

## 12. 依赖清单

| 依赖 | 用途 |
|---|---|
| `pydantic` | 数据模型定义与校验 |
| `pyyaml` | 解析 YAML 配置与 personas |
| LLM 服务 | 主对话 + 心情评判 + 可选的 MBTI 推断 |
| `importlib.resources`（或等价物） | 加载包内资源文件 |

---

## 13. 设计决策记录

| 决策 | 原因 |
|---|---|
| OCEAN 为 SSOT，MBTI 为辅助 | OCEAN 是连续值，粒度更细；MBTI 二元分类易被 LLM 放大刻板印象 |
| 心情评判用独立 LLM 调用 | 主 LLM 的 system prompt 已很长，再让它自评心情会稀释约束力 |
| mood_pct 不暴露原始数字给用户 | 数字是给 LLM 的锚点，用户侧只看到自然演绎后的语气 |
| 评判失败回退 50 而非报错 | 保持对话可用性，中性心情是安全默认值 |
| character_state 用 XML 而非 JSON | XML 在纯文本流中更易被 LLM 识别为结构化元数据 |

# Multi-Agent Society 开发方案

> Version：1.0
>
> Status：Approved
>
> 基于需求文档 (`requirement.md`) + Character Engine 人格引擎 (`character-engine-porting-guide.md`) + mem0 源码 (`reference/mem0/`) 制定。

---

## 目录

1. [技术栈](#1-技术栈)
2. [项目结构](#2-项目结构)
3. [Phase 1：核心数据模型 & 人格引擎](#phase-1核心数据模型--人格引擎)
4. [Phase 2：LLM 网关](#phase-2llm-网关)
5. [Phase 3：Agent Runtime](#phase-3agent-runtime)
6. [Phase 4：Memory System](#phase-4memory-system)
7. [Phase 5：Scheduler & 消息总线](#phase-5scheduler--消息总线)
8. [Phase 6：API & WebSocket 层](#phase-6api--websocket-层)
9. [Phase 7：插件系统 & 狼人杀](#phase-7插件系统--狼人杀)
10. [数据库 Schema](#10-数据库-schema)
11. [开发顺序 & 里程碑](#11-开发顺序--里程碑)

---

## 1. 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 异步优先 |
| Web 框架 | FastAPI | REST + WebSocket |
| 数据库 | PostgreSQL 15+ | 主存储 |
| 向量扩展 | pgvector | 长期记忆语义检索 |
| 缓存 / 消息 | Redis | 消息总线 / 群工作内存 |
| LLM 网关 | OpenAI + Anthropic | Provider 抽象模式 |
| Embedding | OpenAI / 本地模型 | 可插拔 |
| ORM | SQLAlchemy 2.0 + asyncpg | 异步数据库操作 |
| 配置 | YAML + pydantic-settings | 类型安全配置 |

---

## 2. 项目结构

```
MultiAgentSociety/
├── app/
│   ├── core/
│   │   ├── models/              # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── agent.py         # Agent 模型
│   │   │   ├── group.py         # Group / Workspace 模型
│   │   │   ├── message.py       # Message 模型
│   │   │   ├── relationship.py  # Relationship 模型
│   │   │   └── memory.py        # MemoryItem 模型
│   │   └── config.py            # 全局配置 (pydantic-settings)
│   │
│   ├── engine/                  # Character Engine 人格引擎
│   │   └── character/
│   │       ├── models.py        # OceanModel/MBTIModel/DrivesModel/PsychologyProfile
│   │       ├── cues.py          # big_five_to_behavior_cues()
│   │       ├── mbti_resources.py # foundations.md + personas.yaml 加载
│   │       ├── assemble.py      # CHARACTER_JSON / psych_system / character_state XML
│   │       ├── loader.py        # YAML → PsychologyProfileModel
│   │       ├── mood.py          # compute_mood_signal() / StaticMoodStrategy
│   │       └── gating.py        # 记忆门控参数 OCEAN 推导
│   │
│   ├── llm/                     # LLM 网关
│   │   ├── base.py              # LLMProvider 抽象基类
│   │   ├── providers/
│   │   │   ├── openai.py        # OpenAI 兼容 Provider
│   │   │   └── anthropic.py     # Anthropic Provider
│   │   └── router.py            # 根据 Agent 配置路由
│   │
│   ├── agent/                   # Agent Runtime
│   │   ├── runtime.py           # Agent 生命周期管理
│   │   ├── prompt_builder.py    # Prompt 组装（含 personality/memory/context）
│   │   ├── decision.py          # reply_probability 决策
│   │   └── relationship.py      # 关系表 CRUD + 动态更新
│   │
│   ├── memory/                  # Memory System
│   │   ├── base.py              # BaseMemoryStore 抽象
│   │   ├── working.py           # Working Memory (Redis Ring Buffer)
│   │   ├── long_term.py         # Long Memory (pgvector 语义检索)
│   │   ├── shared_world.py      # Shared World Memory (群级别)
│   │   ├── archive.py           # 归档存储
│   │   ├── embeddings.py        # Embedding 适配器（参考 mem0 模式）
│   │   └── store.py             # VectorStore 抽象 + pgvector 实现
│   │
│   ├── scheduler/               # 调度器
│   │   ├── core.py              # Scheduler 主循环
│   │   └── auto_chat.py         # 自主聊天 Tick
│   │
│   ├── message/                 # 消息总线
│   │   └── event_bus.py         # Redis pub/sub 封装
│   │
│   ├── plugin/                  # 插件系统
│   │   ├── base.py              # Plugin 抽象基类
│   │   └── werewolf/            # 狼人杀插件
│   │       ├── __init__.py
│   │       ├── state.py         # 游戏状态机
│   │       └── prompts.py       # 游戏阶段 Prompt 注入
│   │
│   ├── db/                      # 数据库层
│   │   ├── session.py           # 异步会话管理
│   │   ├── models/              # SQLAlchemy ORM 模型
│   │   └── migrations/          # Alembic 迁移
│   │
│   └── api/                     # FastAPI 路由
│       ├── agents.py            # Agent CRUD
│       ├── groups.py            # 群管理
│       ├── messages.py          # 消息接口
│       ├── scheduler.py         # 调度控制
│       └── ws.py                # WebSocket 实时推送
│
├── configs/
│   ├── agents/                  # Agent 人格 YAML 配置
│   │   └── template.yaml        # 配置模板
│   └── global.yaml              # 全局系统配置
│
├── resources/                   # MBTI 资源文件
│   ├── foundations.md
│   └── personas.yaml
│
├── tests/
├── alembic/
├── docker-compose.yaml
├── requirements.txt
└── pyproject.toml
```

---

## 3. Phase 1：核心数据模型 & 人格引擎

### 3.1 数据模型

#### Agent (app/core/models/agent.py)

```python
class Agent:
    id: str
    name: str
    avatar: str
    persona: str                    # 人格描述
    model_config: ModelConfig       # provider / model / temperature / top_p / max_tokens
    psychology_profile: str         # 关联的 psychology_profile.yaml 路径
    status: AgentStatus             # online / offline / busy
    groups: list[str]               # 加入的群 ID 列表
```

#### Group (app/core/models/group.py)

```python
class Group:
    id: str
    name: str
    members: list[str]              # Agent/User ID 列表
    world_memory_id: str            # 关联的 Shared World Memory
    plugin_states: dict             # 插件状态
```

#### Message (app/core/models/message.py)

```python
class Message:
    id: str
    group_id: str
    sender_id: str
    sender_type: Literal["agent", "user"]
    content: str
    created_at: datetime
    metadata: dict                  # emotion / mood 等
```

#### Relationship (app/core/models/relationship.py)

```python
class Relationship:
    agent_id: str                   # 主体
    target_id: str                  # 客体（另一个 Agent/User）
    trust: float                    # 0~1
    respect: float
    love: float
    hate: float
    intimacy: float
    cooperation: float
    updated_at: datetime
```

### 3.2 人格引擎 (app/engine/character/)

参考 `character-engine-porting-guide.md` 完整移植。

#### psychology_profile.yaml 示例

```yaml
# configs/agents/alice.yaml
role:
  name: "Alice"
  name_reading: "アリス"
  role_summary: "温和但直率的小说家，擅长观察人际关系"

ocean:
  openness: 0.7
  conscientiousness: 0.5
  extraversion: 0.4
  agreeableness: 0.6
  emotional_stability: 0.55

ocean_notes: {}
behavior_hints: []
scenario: {}
relationship: {}

mbti:
  strategy: fixed
  type: INFJ
  notes: ""

drives:
  schema_version: 1
  horizon: session
  mission:
    primary: "在社交中寻找故事灵感"
    secondary: "建立有深度的对话"
    narrative: ""
  needs: []
  extensions: {}
```

#### 实现清单

| 文件 | 功能 | 参考 |
|------|------|------|
| `models.py` | OCEAN / MBTI / Drives / PsychologyProfile Pydantic 模型 | porting-guide §2 |
| `cues.py` | `neuroticism_score()` + `big_five_to_behavior_cues()` | porting-guide §3 |
| `mbti_resources.py` | 加载 `foundations.md` / `personas.yaml`，格式化 persona 文本 | porting-guide §4 |
| `assemble.py` | `judge_character_context_json()` + `build_psychology_system_message()` + `build_character_state_context_xml()` | porting-guide §6-7 |
| `loader.py` | `load_psychology_profile(yaml_path) -> PsychologyProfileModel` | porting-guide §11-第一步 |
| `mood.py` | `compute_mood_signal()` + `LlmMoodStrategy` + `StaticMoodStrategy` | porting-guide §5 |
| `gating.py` | 从 OCEAN 推导 `β` / `R` / `threshold_high/mid` + `compute_memory_score()` | porting-guide §8 |

---

## 4. Phase 2：LLM 网关

### 4.1 架构

参考 mem0 的 LLM 工厂模式 (`reference/mem0/mem0/llms/base.py` + `openai.py`)，我们抽象一个更精简的网关。

```python
# app/llm/base.py
class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = None,
        max_tokens: int = None,
    ) -> str: ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float = None,
        max_tokens: int = None,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def chat_structured(
        self,
        messages: list[dict],
        response_model: type[BaseModel],
        temperature: float = None,
    ) -> BaseModel: ...
```

### 4.2 Provider 实现

| Provider | 文件 | API |
|----------|------|-----|
| OpenAI | `app/llm/providers/openai.py` | `openai` SDK，兼容 vLLM / Ollama / DeepSeek 等 |
| Anthropic | `app/llm/providers/anthropic.py` | `anthropic` SDK |

### 4.3 路由器

```python
# app/llm/router.py
class LLMRouter:
    providers: dict[str, LLMProvider]       # {"openai": OpenAIProvider(...), "anthropic": AnthropicProvider(...)}

    def get_provider(self, agent: Agent) -> LLMProvider:
        # 根据 agent.model_config.provider 选择 provider
        ...

    def get_for_mood_judge(self) -> LLMProvider:
        # 心情评判统一用低成本模型
        ...
```

### 4.4 ModelConfig 定义

```python
class ModelConfig(BaseModel):
    provider: Literal["openai", "anthropic"]
    base_url: str | None = None
    api_key: str
    model: str
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 2048
```

---

## 5. Phase 3：Agent Runtime

### 5.1 Agent 生命周期

参考需求文档 §4，每轮对话流程：

```python
# 1. 监听消息（从 Inbox 或 Scheduler 推送获取）
# 2. 决定是否响应（app/agent/decision.py）
message_context = {
    "working_memory": working_memory.get_recent(group_id, 20),
    "shared_world": shared_world.get(group_id),
    "relationship": relationship.get_all(agent_id),
    "mood": current_mood,                          # 当前情绪
    "persona": profile,                              # 人格
    "goals": profile.drives.mission,
}

reply_prob = compute_reply_probability(message_context)
if reply_prob < threshold:
    return  # 忽略

# 3. 检索长期记忆
long_memories = long_term_memory.search(
    query=message_context,
    agent_id=agent_id,
    top_k=5,
    threshold=0.3,
)

# 4. 组装 Prompt（app/agent/prompt_builder.py）
prompt = await build_prompt(
    profile=profile,
    mood=mood_result,
    working_memory=working_memory.get_recent(group_id, 20),
    shared_world=shared_world.get(group_id),
    relationships=relationship.get_all(agent_id),
    long_memories=long_memories,
)

# 5. 调用 LLM
reply = await llm.chat(prompt)

# 6. 更新记忆
long_term_memory.add(
    messages=[{"role": "assistant", "content": reply}],
    agent_id=agent_id,
)
working_memory.append(group_id, agent_id, reply)
relationship.update_from_message(agent_id, reply)

# 7. 广播回复
await event_bus.publish(group_id, Message(sender=agent_id, content=reply))
```

### 5.2 回复决策 (decision.py)

```python
def compute_reply_probability(context: MessageContext) -> float:
    """根据人格/情绪/活跃度/近期发言次数计算回复概率"""
    base_prob = 0.5

    # 外向性影响基础发言欲望
    extraversion = context.persona.ocean.extraversion
    base_prob += (extraversion - 0.5) * 0.3

    # 情绪影响
    mood = context.mood
    if mood.mood_pct > 70:          # 心情好，更愿意说话
        base_prob += 0.15
    elif mood.mood_pct < 30:        # 心情差，不太想说话
        base_prob -= 0.15

    # 最近发言抑制（避免刷屏）
    recent_count = context.working_memory.count_by(agent_id)
    base_prob -= recent_count * 0.1

    return clamp(base_prob, 0.05, 0.95)
```

### 5.3 Prompt Builder (prompt_builder.py)

参考 porting-guide §7，组装顺序：

```
[system] Agent 基础设定 (system_base)
[system] 心理引擎组装 (psych_system):
   - OCEAN behavior_cues
   - MBTI 行为规格
   - Drives 目标与需要
   - 动态状态注入说明
[system] 记忆上下文:
   - 长期记忆检索结果
   - Shared World 上下文
   - 关系网络摘要
[user/assistant] 历史对话 (working memory 最后 N 条)
[user] 本轮用户消息 + character_state XML
```

### 5.4 关系系统 (relationship.py)

```python
class RelationshipService:
    async def get(agent_id: str, target_id: str) -> Relationship
    async def get_all(agent_id: str) -> list[Relationship]
    async def update_from_message(agent_id: str, message: str)
        # 调用 LLM 分析消息对关系的影响
        # change = {"target_id": "...", "trust_delta": 0.05, ...}
    async def decay(agent_id: str)
        # 定期衰减，避免关系值永远不变
```

---

## 6. Phase 4：Memory System

参考 mem0 源码 (`reference/mem0/mem0/memory/main.py`) 的核心设计理念，结合需求文档 §10 的四层记忆架构。

### 6.1 架构总览

```
Memory System
├── Working Memory（Redis Ring Buffer，20~50 条/群，不长期保存）
├── Long Memory（pgvector，Agent 独立，语义检索）
│   ├── Semantic（事实性记忆）
│   ├── Preference（偏好）
│   ├── Experience（经验）
│   ├── Habit（习惯）
│   └── Goal（目标）
├── Shared World Memory（Redis，群级别运行时上下文）
└── Archive（PostgreSQL，活动/游戏结束后归档）
```

### 6.2 参考 mem0 的设计点

| mem0 概念 | 我们项目中的映射 |
|-----------|----------------|
| `Memory.add(messages, user_id, agent_id)` | `LongMemory.add(agent_id, category, text)` |
| `Memory.search(query, filters)` | `LongMemory.search(agent_id, query, category)` |
| `EmbeddingBase.embed(text)` | `EmbeddingService.embed(text)` → OpenAI/text-embedding-3-small |
| `VectorStoreBase` (pgvector) | `VectorStore.pgvector` 存储记忆 embedding |
| `SQLiteManager` (history) | PostgreSQL 表 `memory_history` 存储变更记录 |
| `entity_extraction` | 提取对话中的关键实体→关联关系网络 |
| `LLM extraction prompt` | 对话→提取事实→存储为长期记忆 |
| Hash dedup | 防止相同记忆重复存储 |

### 6.3 各层详细设计

#### 6.3.1 Working Memory (app/memory/working.py)

```python
class WorkingMemory:
    """每个群独立的近期聊天 Ring Buffer"""

    async def append(group_id: str, sender_id: str, content: str)
        # Redis LIST, LTRIM 保持 50 条上限
        # key: "working_memory:{group_id}"

    async def get_recent(group_id: str, limit: int = 20) -> list[Message]
        # Redis LRANGE

    async def clear(group_id: str)
        # 群活动结束时清理
```

#### 6.3.2 Long Memory (app/memory/long_term.py)

参考 mem0 `Memory.add()` → `_add_to_vector_store()` 的模式：

```python
class LongMemory:
    """
    Agent 独立长期记忆，pgvector 存储。

    每轮对话后：
    1. 提取记忆候选（用 LLM 从对话中提取事实片段）
    2. 计算记忆门控分数（参考 gating.py）
    3. 达到阈值的存储为 embedding
    4. 检索时用语义相似度 + 记忆分类过滤
    """

    async def add(
        agent_id: str,
        category: MemoryCategory,     # semantic / preference / experience / habit / goal
        text: str,
        metadata: dict = None,
        score: float = None,          # 记忆门控分数
    ) -> str
        # 1. embedding = embed(text)
        # 2. INSERT INTO memory_store (agent_id, category, vector, payload)
        # 3. INSERT INTO memory_history (memory_id, event='ADD')

    async def search(
        agent_id: str,
        query: str,
        category: MemoryCategory = None,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> list[MemoryItem]
        # 1. query_embedding = embed(query)
        # 2. SELECT ..., vector <=> query_embedding AS distance
        #    FROM memory_store
        #    WHERE agent_id = agent_id AND category = category (optional)
        #    ORDER BY distance LIMIT top_k
        # 3. 返回 score >= threshold 的结果

    async def update(memory_id: str, text: str)
        # 更新记忆内容 + embedding

    async def forget(agent_id: str, memory_id: str)
        # 遗忘特定记忆（软删除 / 真删除）

    async def compress(agent_id: str)
        # 定期压缩：合并相似记忆，删除低价值记忆
```

#### 6.3.3 Shared World Memory (app/memory/shared_world.py)

```python
class SharedWorldMemory:
    """每个群一个公共上下文，所有 Agent 共享"""

    async def append(group_id: str, event: WorldEvent)
        # event: {"type": "chat" / "game_action" / "system_event",
        #          "content": "...", "timestamp": ...}
        # Redis LIST 存储

    async def get(group_id: str, since: datetime = None) -> str
        # 返回格式化的世界状态文本
        # 内容：当前群聊话题 / 活动状态 / 游戏进度 / 公共事件

    async def summarize(group_id: str) -> str
        # 活动结束时调用 LLM 生成摘要
        # 摘要 → Archive，清空 Runtime Buffer
```

#### 6.3.4 Archive (app/memory/archive.py)

```python
class Archive:
    """活动/游戏结束后的归档"""

    async def save_activity(activity_id: str, summary: str, metadata: dict)
        # PostgreSQL 存储

    async def search(query: str, top_k: int = 5) -> list[ArchiveItem]
        # 按需检索（默认不进 Prompt）
```

### 6.4 记忆门控 (app/engine/character/gating.py)

参考 porting-guide §8：

```python
def compute_gating_params(ocean: OceanModel) -> GatingParams:
    """从 OCEAN 推导记忆门控参数"""
    neuroticism = 1.0 - ocean.emotional_stability
    return GatingParams(
        beta=0.3 + neuroticism * 0.4,        # 情绪敏感度
        relationship_base=0.3 + ocean.extraversion * 0.2 + ocean.agreeableness * 0.2,
        threshold_high=0.7 - neuroticism * 0.2,  # 神经质高→更容易记住
        threshold_mid=0.4 - neuroticism * 0.15,
    )

def compute_memory_score(
    gating: GatingParams,
    messages: list[Message],
    relationship: Relationship,
) -> float:
    """
    score = w_emotional × 情绪差分
          + w_importance × 重要性
          + w_user_rel × 用户相关性
          + w_novelty × 新颖度
          + w_relationship × 关系基线
          - w_conflict × 冲突风险
    """
    ...

    # score >= threshold_high → 全量写入
    # score >= threshold_mid  → 中等写入
    # score < threshold_mid   → 仅摘要
```

### 6.5 Embedding Service (app/memory/embeddings.py)

参考 mem0 `EmbeddingBase` + `OpenAIEmbedding`：

```python
class EmbeddingService:
    def __init__(self, provider: str = "openai", model: str = "text-embedding-3-small"):
        ...

    async def embed(self, text: str) -> list[float]
        # 调用 OpenAI embeddings API
        # 返回 1536 维向量

    async def embed_batch(self, texts: list[str]) -> list[list[float]]
        # 批量 embedding
```

### 6.6 Vector Store (app/memory/store.py)

参考 mem0 `VectorStoreBase` + `PGVector`：

```python
class VectorStore:
    """pgvector 封装"""

    async def create_collection(name: str, dims: int)

    async def insert(
        collection: str,
        vectors: list[list[float]],
        payloads: list[dict],
        ids: list[str] = None,
    )

    async def search(
        collection: str,
        query_vector: list[float],
        filters: dict = None,
        top_k: int = 5,
    ) -> list[SearchResult]

    async def delete(collection: str, vector_id: str)

    async def update(collection: str, vector_id: str, vector: list[float] = None, payload: dict = None)
```

---

## 7. Phase 5：Scheduler & 消息总线

### 7.1 Event Bus (app/message/event_bus.py)

```python
class EventBus:
    """Redis pub/sub 消息总线"""

    async def publish(group_id: str, message: Message)
        # Redis PUBLISH group:{group_id} message_json

    async def subscribe(group_id: str) -> AsyncIterator[Message]
        # Redis SUBSCRIBE group:{group_id}
```

### 7.2 Scheduler (app/scheduler/core.py)

参考需求文档 §6：

```python
class Scheduler:
    """
    核心调度器，负责：
    - 消息广播（User → Group → Agent）
    - Agent 唤醒和回复调度
    - 自主聊天 Tick
    - 游戏调度
    - Memory 更新统一触发
    """

    async def handle_user_message(group_id: str, user_id: str, content: str)
        # 1. 写入 Working Memory
        # 2. 广播给群内所有 Agent
        # 3. 等待 Agent 回复（超时控制）

    async def auto_chat_tick()
        # 每 30 秒
        # 1. 选择活跃群
        # 2. 选择活跃 Agent
        # 3. 判断是否想说话
        # 4. 发言 → 广播
```

### 7.3 自主聊天 (app/scheduler/auto_chat.py)

```python
class AutoChatScheduler:
    """
    自主聊天逻辑。
    开启条件：群内无用户消息超过阈值 + 群已开启 Auto Conversation

    Tick 流程：
    1. 找到开启自主聊天的群
    2. 选择当前在线的 Agent（排除刚发言的）
    3. 用 decision.py 计算回复概率
    4. 概率 > 阈值 → LLM 生成 → 广播
    """

    STOP_CONDITIONS:
        - LLM 判断对话自然结束
        - 用户插话
        - 连续 N 轮无人响应
```

---

## 8. Phase 6：API & WebSocket 层

### 8.1 REST API

| 路由 | 方法 | 功能 |
|------|------|------|
| `/agents` | GET/POST | 列出/创建 Agent |
| `/agents/{id}` | GET/PUT/DELETE | 获取/更新/删除 Agent |
| `/agents/{id}/start` | POST | 启动 Agent（加载记忆，上线） |
| `/agents/{id}/stop` | POST | 停止 Agent |
| `/groups` | GET/POST | 列出/创建群 |
| `/groups/{id}` | GET/PUT/DELETE | 群管理 |
| `/groups/{id}/join` | POST | Agent/User 加群 |
| `/groups/{id}/messages` | GET | 获取聊天历史 |
| `/groups/{id}/auto-chat` | POST | 开启/关闭自主聊天 |
| `/messages` | POST | User 发送消息 |
| `/plugins/{name}` | GET | 获取插件状态 |
| `/scheduler/status` | GET | 调度器状态 |
| `/memories/{agent_id}` | GET | 查看 Agent 长期记忆 |

### 8.2 WebSocket

```
WS /ws/groups/{group_id}

事件类型：
- message: 新消息推送
- agent_typing: Agent 正在输入
- agent_mood: Agent 情绪变化
- game_state: 游戏状态更新
```

---

## 9. Phase 7：插件系统 & 狼人杀

### 9.1 Plugin 抽象 (app/plugin/base.py)

```python
class Plugin(ABC):
    name: str
    state: dict                           # 游戏状态
    actions: list[Action]                 # 可用动作
    rules: list[Rule]                     # 规则

    @abstractmethod
    async def on_event(event: PluginEvent) -> PluginResponse
        # 处理事件，返回决定（回复 / 状态更新 / Prompt 注入）

    @abstractmethod
    def inject_prompt(agent: Agent) -> str | None
        # 向 Agent prompt 中注入游戏上下文

    @abstractmethod
    async def get_state_for(agent_id: str) -> dict
        # Agent 允许看到的信息（信息隔离）
```

### 9.2 Host Agent

```python
class HostAgent:
    """
    游戏主持人 Agent，负责：
    - 宣布规则
    - 主持流程（由插件状态机驱动，Host 不负责逻辑）
    - 氛围营造
    - 角色演绎
    """

    async def narrate(event: GameEvent)
        # 根据游戏事件生成叙事性描述
```

### 9.3 狼人杀插件 (app/plugin/werewolf/)

```python
class WerewolfPlugin(Plugin):
    """
    状态机阶段：
    - night: 狼人刀人 / 预言家验人 / 女巫救人 / 守卫守人
    - day: 讨论 / 投票 / 处决
    - end: 胜负判定

    信息隔离：
    - 狼人只看得到狼队友
    - 预言家只看得到查验结果
    - 平民只看得到公共信息
    """
```

---

## 10. 数据库 Schema

### 10.1 PostgreSQL 表

```sql
-- Agents
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    avatar VARCHAR(500),
    persona TEXT,
    status VARCHAR(20) DEFAULT 'offline',
    model_config JSONB,
    psychology_profile TEXT,       -- YAML 文件路径或内容
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Groups
CREATE TABLE groups (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    auto_chat BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Group Members
CREATE TABLE group_members (
    group_id UUID REFERENCES groups(id),
    member_id UUID REFERENCES agents(id),
    member_type VARCHAR(10) CHECK (member_type IN ('agent', 'user')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (group_id, member_id)
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    group_id UUID REFERENCES groups(id),
    sender_id UUID NOT NULL,
    sender_type VARCHAR(10) CHECK (sender_type IN ('agent', 'user')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Relationships
CREATE TABLE relationships (
    agent_id UUID REFERENCES agents(id),
    target_id UUID NOT NULL,
    trust REAL DEFAULT 0.5,
    respect REAL DEFAULT 0.5,
    love REAL DEFAULT 0.0,
    hate REAL DEFAULT 0.0,
    intimacy REAL DEFAULT 0.0,
    cooperation REAL DEFAULT 0.5,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (agent_id, target_id)
);

-- Memory Store (pgvector)
CREATE TABLE memory_store (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    category VARCHAR(20) CHECK (category IN ('semantic', 'preference', 'experience', 'habit', 'goal')),
    vector vector(1536),
    payload JSONB,
    score REAL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_memory_store_agent ON memory_store(agent_id);
CREATE INDEX idx_memory_store_category ON memory_store(category);

-- Memory History
CREATE TABLE memory_history (
    id UUID PRIMARY KEY,
    memory_id UUID REFERENCES memory_store(id),
    old_memory TEXT,
    new_memory TEXT,
    event VARCHAR(10) CHECK (event IN ('ADD', 'UPDATE', 'DELETE', 'FORGET')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Archives
CREATE TABLE archives (
    id UUID PRIMARY KEY,
    group_id UUID REFERENCES groups(id),
    activity_type VARCHAR(50),
    summary TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Plugin States
CREATE TABLE plugin_states (
    group_id UUID REFERENCES groups(id),
    plugin_name VARCHAR(100),
    state JSONB,
    PRIMARY KEY (group_id, plugin_name)
);
```

---

## 11. 开发顺序 & 里程碑

### 里程碑 M1：核心引擎可运行（Phase 1-3）

```
目标：CLI 模式下单个 Agent 可对话（带人格+情绪+记忆）
测试方式：python scripts/chat_with_agent.py --agent alice

依赖：
- X Python 项目结构
- X 数据模型
- X 人格引擎（OCEAN + MBTI + Mood + Drives）
- X LLM 网关（OpenAI + Anthropic）
- X Agent Runtime（Prompt Builder + 回复决策）
- X 简单文件存储的 Long Memory（Phase 4 的简化版）
```

### 里程碑 M2：记忆系统完整（Phase 4）

```
目标：4 层记忆全部可用，OCEAN 门控生效
测试方式：长时间对话后检索记忆准确性
```

### 里程碑 M3：多人社交可用（Phase 5-6）

```
目标：多个 Agent 在群聊中自主聊天
测试方式：启动 3 个 Agent + 1 个 User，观察自然对话
```

### 里程碑 M4：游戏插件（Phase 7）

```
目标：狼人杀可玩
测试方式：7 个 Agent 狼人杀对局
```

---

## 附录 A：mem0 源码参考索引

| mem0 文件 | 参考用途 | 我们的文件 |
|-----------|---------|-----------|
| `mem0/memory/main.py` | Memory.add/search 主流程 | `app/memory/long_term.py` |
| `mem0/memory/base.py` | MemoryBase 抽象 | `app/memory/base.py` |
| `mem0/memory/storage.py` | SQLite 历史+消息存储 | `app/db/models/` + PostgreSQL |
| `mem0/embeddings/base.py` | EmbeddingBase 抽象 | `app/memory/embeddings.py` |
| `mem0/embeddings/openai.py` | OpenAI Embedding 实现 | `app/memory/embeddings.py` |
| `mem0/vector_stores/base.py` | VectorStoreBase 抽象 | `app/memory/store.py` |
| `mem0/vector_stores/pgvector.py` | PGVector 实现 | `app/memory/store.py` |
| `mem0/llms/base.py` | LLMBase 抽象 | `app/llm/base.py` |
| `mem0/llms/openai.py` | OpenAI LLM 实现 | `app/llm/providers/openai.py` |
| `mem0/configs/base.py` | MemoryConfig + MemoryItem | `app/core/config.py` + `app/core/models/memory.py` |
| `mem0/utils/scoring.py` | BM25 + 混合检索评分 | `app/memory/scoring.py` |
| `mem0/utils/entity_extraction.py` | 实体提取 | `app/agent/relationship.py` |
| `mem0/configs/prompts.py` | 记忆提取 Prompt | `app/memory/prompts.py` |

---

## 附录 B：配置规范

### global.yaml

```yaml
llm:
  default_provider: openai
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      base_url: "https://api.openai.com/v1"
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}

embedding:
  provider: openai
  model: text-embedding-3-small
  dimensions: 1536

database:
  host: localhost
  port: 5432
  name: multi_agent_society
  user: postgres
  password: ${DB_PASSWORD}

redis:
  host: localhost
  port: 6379

memory:
  working_memory_limit: 50
  long_memory_search_top_k: 5
  long_memory_search_threshold: 0.3
  mood_judge_enabled: true
  mood_judge_max_messages: 10
  mood_judge_timeout_s: 15.0
  memory_gating_mode: ocean    # preset / ocean / hybrid

scheduler:
  auto_chat_interval: 30
  reply_timeout: 20
```

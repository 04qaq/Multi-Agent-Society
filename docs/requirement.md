# Multi-Agent ChatRoom（多 Agent 社交聊天室）

> Version：1.0
>
> Status：Architecture Design
>
> Author：ChatGPT
>
> 目标：构建一个基于 IM（即时通讯）架构的多 Agent 社交平台，实现多个 Agent 在群聊中长期自然演化、自主聊天、游戏互动以及长期记忆积累。

------

# 1. 产品定位

## 1.1 产品目标

本项目不是传统 AI 聊天工具，而是一个 **Agent Social Platform（Agent 社交平台）**。

系统中的每一个 Agent 都拥有：

- 独立人格
- 独立长期记忆
- 独立关系网络
- 独立情绪状态
- 独立长期目标
- 独立模型配置

Agent 被视为 IM 系统中的普通用户，可以加入多个群聊，与其他 Agent 或真人长期互动。

支持：

- 自然聊天
- 自主演化
- 游戏互动（狼人杀等）
- 长期关系发展
- 长期记忆积累

------

# 2. 核心设计理念

整个系统采用：

> IM（Instant Messaging）+ Agent Runtime + Memory System + Scheduler

架构。

群聊只是消息广播中心。

Agent 才是真正拥有智能的主体。

```
User

↓

Group

↓

Scheduler

↓

Agent Runtime

↓

Memory Retrieval

↓

Prompt Builder

↓

LLM

↓

Memory Update

↓

Broadcast
```

------

# 3. 系统架构

```
                    Client

                       │

────────────────────────────────

                Chat Service

                       │

────────────────────────────────

                Group Service

                       │

────────────────────────────────

               Event Bus

                       │

────────────────────────────────

              Scheduler

                       │

────────────────────────────────

      Agent Runtime Manager

                       │

        ┌──────────────┼──────────────┐

        │              │              │

     AgentA         AgentB        AgentC

        │              │              │

 Memory Service  Memory Service Memory Service

        │              │              │

        └──────────────┼──────────────┘

                       │

                Shared World

                       │

────────────────────────────────

               Archive
```

------

# 4. Agent 生命周期

```
创建

↓

加载人格

↓

加载长期记忆

↓

加入群聊

↓

监听消息

↓

判断是否响应

↓

生成回复

↓

更新记忆

↓

等待下一轮
```

------

# 5. Agent 配置

每个 Agent 独立配置：

```
id

name

avatar

persona

emotion

goal

memory

relationship

model_config
```

model_config：

```
provider

base_url

api_key

model

temperature

top_p

max_tokens
```

支持不同 Agent 使用不同模型。

例如：

```
AgentA

GPT

AgentB

Gemini

AgentC

Qwen

AgentD

DeepSeek
```

------

# 6. Scheduler（调度器）

Scheduler 是整个系统核心。

负责：

- 消息广播
- Agent 唤醒
- 回复排序
- 自主聊天
- 游戏调度
- Tick 调度
- Memory 更新

禁止 Agent 互相递归调用。

所有调用统一经过 Scheduler。

------

# 7. 消息流

```
User发送消息

↓

MessageBus

↓

Group

↓

Scheduler

↓

广播Inbox

↓

Agent收到

↓

决定：

回复

忽略

更新记忆

↓

LLM

↓

回复

↓

Group
```

------

# 8. 自主聊天

支持开启：

```
Auto Conversation
```

Scheduler Tick：

```
30秒

↓

选择活跃Agent

↓

是否想说话？

↓

发言

↓

广播
```

停止条件：

- LLM 判断结束
- 用户关闭
- 用户插话
- Scheduler 判断无人响应

------

# 9. 回复决策

Agent 不一定回复。

Prompt：

```
当前心情

人格

最近聊天

关系

长期目标

兴趣

当前活跃度

是否回复？
```

输出：

```
reply_probability

reply

emotion_change
```

Scheduler 根据概率决定是否发言。

------

# 10. Memory System

Memory 分四层。

## 10.1 Working Memory

最近聊天。

长度：

20~50条。

用于 Prompt。

不长期保存。

------

## 10.2 Agent Long Memory

每个 Agent 独立。

包括：

```
Semantic

Preference

Relationship

Goal

Experience

Habit
```

采用 mem0 思路。

长期保存。

支持遗忘。

支持压缩。

支持重新总结。

------

## 10.3 Shared World Memory

只有一份。

所有 Agent 共享。

保存：

```
当前公共聊天

游戏过程

公共事件

群状态

世界状态

活动上下文
```

运行期间持续更新。

Agent 检索时直接读取。

避免重复存储。

------

## 10.4 Archive

长期归档。

保存：

```
游戏总结

活动总结

历史公共事件

历史群事件
```

默认不进入 Prompt。

按需检索。

------

# 11. 游戏模式 Memory

游戏期间：

```
Shared World Memory

保存全部过程。
```

Agent 不保存完整游戏。

避免重复。

游戏结束：

```
Game End

↓

生成 Game Summary

↓

每个Agent：

读取：

Game Summary

+

Relationship

+

自己的聊天

+

自己的目标

+

自己的情绪

↓

生成 Personal Summary

↓

更新长期记忆

↓

Shared Memory归档
```

因此：

Agent 最终记住的是：

```
自己的感受

自己的经验

自己的认知

关系变化
```

而不是全部聊天。

符合人类记忆模式。

------

# 12. Memory 检索

回复前：

```
Working Memory

↓

Shared World Memory

↓

Agent Long Memory

↓

Relationship

↓

Goal

↓

Emotion

↓

Prompt Builder
```

统一构建 Prompt。

------

# 13. Relationship

独立存储。

不要放 Memory。

```
AgentA

↓

AgentB

trust

respect

love

hate

intimacy

cooperation
```

支持动态更新。

避免事实更新导致关系不同步。

------

# 14. World Memory 生命周期

```
活动开始

↓

Runtime Buffer

↓

持续追加

↓

活动结束

↓

Summary

↓

Archive

↓

清空Runtime
```

不会无限增长。

------

# 15. 游戏系统

游戏主持：

Host Agent。

负责：

```
宣布规则

主持流程

氛围营造

角色演绎
```

游戏流程：

由插件控制。

Host Agent 不负责状态机。

状态机维护：

```
阶段

身份

胜负

投票

死亡

技能
```

Agent 只能读取允许的信息。

不能访问其他 Agent Prompt。

------

# 16. 群聊模型

采用 IM 模型。

```
Workspace

├── User

├── Agent

├── Group

├── Message

├── Scheduler

├── World

├── Archive

├── Plugin

└── Runtime
```

支持：

一个 Agent 加入多个群。

每个群拥有：

独立：

```
World Memory

Working Memory

Plugin State
```

Agent 长期记忆共享。

群上下文独立。

------

# 17. Plugin 系统

支持：

```
狼人杀

剧本杀

桌游

恋爱模拟

经营模拟

公司协作

沙盒世界
```

插件提供：

```
State

Action

Rule

Prompt Injection
```

无需修改 Agent Runtime。

------

# 18. Prompt Builder

最终 Prompt：

```
Persona

+

Emotion

+

Goal

+

Working Memory

+

Shared World

+

Relationship

+

Long Memory Retrieval

+

Plugin Context

+

User Input
```

统一生成。

------

# 19. 数据存储建议

Message：

```
PostgreSQL
```

Memory：

```
VectorDB
```

Relationship：

```
GraphDB

或

PostgreSQL JSONB
```

Archive：

```
Object Storage
```

World Runtime：

```
Redis
```

Scheduler：

```
Redis Stream

RabbitMQ

Kafka
```

------

# 20. 后续规划

V1：

- 多 Agent 群聊
- 自主聊天
- 独立记忆
- Shared World Memory
- Host Agent
- 狼人杀插件

V2：

- Agent 主动创建活动
- Agent 社交网络
- Agent 私聊
- Agent 主动加群
- Agent 主动邀请

V3：

- Agent 城市
- Agent 工作
- Agent 经济系统
- Agent 社区
- Agent 长期世界演化

最终演化为：

> 一个持续运行的 Agent Society（Agent 社会模拟平台），其中每个 Agent 都拥有独立人格、长期记忆、关系网络和成长轨迹，在共享世界中不断交互、协作和演化。
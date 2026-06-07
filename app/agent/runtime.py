import logging
from typing import Optional

from app.core.models.agent import Agent, ModelConfig
from app.core.models.message import Message
from app.engine.character.models import PsychologyProfileModel
from app.engine.character.loader import load_psychology_profile
from app.engine.character.mood import MoodResult, LlmMoodStrategy, StaticMoodStrategy
from app.engine.character.assemble import judge_character_context_json
from app.agent.decision import MessageContext, compute_reply_probability
from app.agent.prompt_builder import PromptBuilder
from app.agent.relationship import relationship_service
from app.llm.router import llm_router
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(self, agent: Agent, profile: Optional[PsychologyProfileModel] = None):
        self._agent = agent
        self._profile = profile or PsychologyProfileModel()
        self._mbti_type = self._profile.mbti.type or "INFP"
        self._cognitive_hint = ""
        self._llm: Optional[LLMProvider] = None
        self._mood_strategy = None
        self._prompt_builder: Optional[PromptBuilder] = None
        self._mood: MoodResult = MoodResult(valence=0.0, confidence=0.0, label="中性", mood_pct=50)
        self._recent_messages: list[Message] = []

    async def initialize(self) -> None:
        self._llm = llm_router.get_provider(self._agent.llm_config)
        self._mood_strategy = LlmMoodStrategy(self._llm)
        self._prompt_builder = PromptBuilder(
            profile=self._profile,
            mbti_type=self._mbti_type,
            cognitive_hint=self._cognitive_hint,
        )
        self._agent.status = "online"
        logger.info(f"Agent {self._agent.name} initialized")

    async def handle_message(self, message: Message) -> Optional[str]:
        context = MessageContext(
            agent_id=self._agent.id,
            persona=self._profile.role.role_summary,
            ocean=self._profile.ocean,
            mood=self._mood,
            recent_self_count=sum(1 for m in self._recent_messages[-10:] if m.sender_id == self._agent.id),
            total_messages=len(self._recent_messages),
        )

        reply_prob = compute_reply_probability(context)
        if reply_prob < 0.3 and message.sender_type == "agent":
            return None

        self._recent_messages.append(message)

        return await self._generate_reply(message.content)

    async def _generate_reply(self, user_text: str) -> str:
        character_json = judge_character_context_json(
            self._profile, self._mbti_type, self._cognitive_hint
        )
        mood_result = await self._mood_strategy.compute(
            history=[{"role": "user" if m.sender_type == "user" else "assistant", "content": m.content}
                     for m in self._recent_messages[:-1]],
            user_text=user_text,
            character_context_json=character_json,
        )
        self._mood = mood_result

        messages = self._prompt_builder.build(
            history=[{"role": "user" if m.sender_type == "user" else "assistant", "content": m.content}
                     for m in self._recent_messages[:-1]],
            user_text=user_text,
            mood=mood_result,
        )

        reply = await self._llm.chat(messages)

        self._recent_messages.append(Message(
            id="",
            group_id="",
            sender_id=self._agent.id,
            sender_type="agent",
            content=reply,
        ))

        return reply

    @property
    def agent(self) -> Agent:
        return self._agent

    @property
    def mood(self) -> MoodResult:
        return self._mood

    @property
    def profile(self) -> PsychologyProfileModel:
        return self._profile

import logging
from typing import Optional

from app.core.models.relationship import Relationship

logger = logging.getLogger(__name__)


class RelationshipService:
    _store: dict[str, dict[str, Relationship]] = {}

    async def get(self, agent_id: str, target_id: str) -> Optional[Relationship]:
        agent_rels = self._store.get(agent_id, {})
        return agent_rels.get(target_id)

    async def get_all(self, agent_id: str) -> list[Relationship]:
        agent_rels = self._store.get(agent_id, {})
        return list(agent_rels.values())

    async def upsert(self, rel: Relationship) -> None:
        if rel.agent_id not in self._store:
            self._store[rel.agent_id] = {}
        self._store[rel.agent_id][rel.target_id] = rel

    async def update_from_message(self, agent_id: str, message_content: str) -> None:
        pass

    async def decay(self, agent_id: str, factor: float = 0.99) -> None:
        agent_rels = self._store.get(agent_id, {})
        for rel in agent_rels.values():
            rel.trust *= factor
            rel.respect *= factor
            rel.intimacy *= factor


relationship_service = RelationshipService()

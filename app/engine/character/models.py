from pydantic import BaseModel, Field
from typing import Literal, Optional


class OceanModel(BaseModel):
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    emotional_stability: float = Field(default=0.5, ge=0.0, le=1.0)

    @property
    def neuroticism(self) -> float:
        return 1.0 - self.emotional_stability


class MBTIModel(BaseModel):
    strategy: Literal["fixed", "infer_once"] = "fixed"
    type: Optional[str] = None
    notes: str = ""


class DriveMissionModel(BaseModel):
    primary: str = ""
    secondary: str = ""
    narrative: str = ""


class DrivesModel(BaseModel):
    schema_version: int = 1
    horizon: Literal["scene", "session", "arc"] = "session"
    mission: DriveMissionModel = Field(default_factory=DriveMissionModel)
    needs: list[dict] = Field(default_factory=list)
    extensions: dict = Field(default_factory=dict)


class RoleModel(BaseModel):
    name: str = ""
    name_reading: str = ""
    role_summary: str = ""


class PsychologyProfileModel(BaseModel):
    role: RoleModel = Field(default_factory=RoleModel)
    ocean: OceanModel = Field(default_factory=OceanModel)
    ocean_notes: dict = Field(default_factory=dict)
    behavior_hints: list[str] = Field(default_factory=list)
    scenario: dict = Field(default_factory=dict)
    relationship: dict = Field(default_factory=dict)
    mbti: MBTIModel = Field(default_factory=MBTIModel)
    drives: DrivesModel = Field(default_factory=DrivesModel)

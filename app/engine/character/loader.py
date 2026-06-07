from pathlib import Path
from typing import Optional
import yaml

from app.engine.character.models import PsychologyProfileModel


def load_psychology_profile(yaml_path: str | Path) -> PsychologyProfileModel:
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Psychology profile not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return PsychologyProfileModel(**data)


def load_psychology_profile_from_text(yaml_text: str) -> PsychologyProfileModel:
    data = yaml.safe_load(yaml_text)
    return PsychologyProfileModel(**data)

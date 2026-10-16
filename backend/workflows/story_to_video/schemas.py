from pydantic import BaseModel, ConfigDict, Field, model_validator

IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]{1,99}$"


class CharacterPlan(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: str = Field(pattern=IDENTIFIER_PATTERN)
    name: str = Field(min_length=1, max_length=200)
    appearance: str = Field(min_length=1, max_length=2000)
    prompt_fragment: str = Field(min_length=1, max_length=2000)


class ScenePlan(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: str = Field(pattern=IDENTIFIER_PATTERN)
    order: int = Field(ge=1)
    duration_seconds: float = Field(gt=0, le=120)
    character_ids: list[str] = Field(min_length=1, max_length=3)
    location: str = Field(min_length=1, max_length=1000)
    narration: str = Field(min_length=1, max_length=1500)
    image_prompt: str = Field(min_length=1, max_length=3000)
    motion_prompt: str = Field(min_length=1, max_length=2000)
    sound_effects: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def require_unique_characters(self) -> "ScenePlan":
        if len(self.character_ids) != len(set(self.character_ids)):
            raise ValueError("character_ids must be unique within a scene")
        return self


class StoryboardBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    visual_style: str = Field(min_length=1, max_length=500)
    characters: list[CharacterPlan] = Field(min_length=1, max_length=30)
    scenes: list[ScenePlan] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_references_and_order(self) -> "StoryboardBase":
        character_ids = [character.id for character in self.characters]
        if len(character_ids) != len(set(character_ids)):
            raise ValueError("character ids must be unique")

        scene_ids = [scene.id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene ids must be unique")

        orders = [scene.order for scene in self.scenes]
        if sorted(orders) != list(range(1, len(self.scenes) + 1)):
            raise ValueError("scene order must be continuous and start at 1")

        known_characters = set(character_ids)
        for scene in self.scenes:
            unknown = set(scene.character_ids) - known_characters
            if unknown:
                raise ValueError(
                    f"scene {scene.id} references unknown characters: {sorted(unknown)}"
                )
        return self


class StoryboardPlan(StoryboardBase):
    @model_validator(mode="after")
    def validate_generated_duration(self) -> "StoryboardPlan":
        invalid = [
            scene.id
            for scene in self.scenes
            if not 4 <= scene.duration_seconds <= 10
        ]
        if invalid:
            raise ValueError(
                f"generated scene duration must be between 4 and 10 seconds: {invalid}"
            )
        return self


class StoryboardReadPlan(StoryboardBase):
    pass

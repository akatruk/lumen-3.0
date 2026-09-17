from typing import Literal,Annotated
from pydantic import BaseModel, Field, ConfigDict, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)

class Text(Strict):
    en: str = Field(min_length=1, max_length=2400)
    zh: str = Field(min_length=1, max_length=2400)

class Span(Strict):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    @model_validator(mode='after')
    def valid(self):
        if self.end <= self.start: raise ValueError('Invalid time range')
        return self

class Scene(Span):
    title: Text
    observation: Text
    role: Literal['hook','context','proof','product','cta','transition']

class Caption(Span):
    emphasis_en:list[Annotated[str,Field(min_length=1,max_length=48)]]=Field(default_factory=list,max_length=8)
    emphasis_zh:list[Annotated[str,Field(min_length=1,max_length=48)]]=Field(default_factory=list,max_length=8)
    original: str = Field(max_length=300)
    en: str = Field(max_length=300)
    zh: str = Field(max_length=300)

class Recommendation(Span):
    id: str = Field(pattern=r'^[a-z0-9_-]{1,32}$')
    title: Text
    evidence: Text
    improvement: Text
    category: Literal['hook','pacing','captions','audio','broll']
    confidence: float = Field(ge=0,le=1)
    auto_apply: bool
    # Allowed operations only. Text never becomes code or an ffmpeg expression.
    action: Literal['remove','move_to_front','captions','normalize_audio','generate_broll']
    generation_prompt: str = Field(max_length=1200)

class Score(Strict):
    category: Literal['hook','clarity','pacing','visuals','audio']
    value: int = Field(ge=0,le=100)
    reason: Text

class Analysis(Strict):
    summary: Text
    strongest_moment: Text
    audience: Text
    scores: list[Score] = Field(min_length=1,max_length=5)
    scenes: list[Scene] = Field(min_length=1,max_length=40)
    transcript: list[Caption] = Field(max_length=160)
    recommendations: list[Recommendation] = Field(max_length=12)
    uncertainties: list[Text] = Field(max_length=8)

class QA(Strict):
    passed: bool
    observations: list[Text] = Field(max_length=10)
    issues: list[Text] = Field(max_length=10)

class QualityReview(QA):
    scores:list[Score]=Field(min_length=5,max_length=5)
    revisions:list[Text]=Field(max_length=8)
    @model_validator(mode='after')
    def complete_scores(self):
        if len({s.category for s in self.scores})!=5:raise ValueError('duplicate_quality_category')
        if (not self.passed or sum(s.value for s in self.scores)/5<75) and not self.revisions:raise ValueError('revision_required')
        return self

class RenderRequest(Strict):
    recommendations: list[str] = Field(max_length=12)

class Credentials(Strict):
    email: str = Field(min_length=3,max_length=200)
    password: str = Field(min_length=10,max_length=200)
    invite: str = Field(default='',max_length=200)

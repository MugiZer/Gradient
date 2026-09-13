import keyword
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")]
Text = Annotated[str, Field(min_length=1, max_length=16000)]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TrajectoryStep(Contract):
    role: Literal["user", "assistant", "tool"]
    content: str = Field(max_length=32000)


class RuntimeEvidence(Contract):
    command: Text
    exit_code: int | None = None
    stdout: str = Field(default="", max_length=32000)
    stderr: str = Field(default="", max_length=32000)


class StarterFile(Contract):
    path: Text
    content: str = Field(max_length=32000)


class InteractionSnapshot(Contract):
    original_task: Text
    bad_agent_output: str = Field(default="", max_length=32000)
    bad_diff: str = Field(default="", max_length=32000)
    human_message: Text
    starter_state: list[StarterFile] = Field(default_factory=list, max_length=64)
    trajectory: list[TrajectoryStep] = Field(default_factory=list, max_length=128)
    accepted_output: str = Field(default="", max_length=32000)
    runtime_evidence: list[RuntimeEvidence] = Field(default_factory=list, max_length=32)


class Capability(Contract):
    name: Identifier
    description: Text
    positive_rule: Text
    negative_rule: Text


class LearningEvent(Contract):
    id: Identifier = Field(default_factory=lambda: "grad_" + uuid4().hex)
    is_learning_event: bool
    confidence: float = Field(ge=0, le=1)
    rejected_behavior: str
    correction: str
    capability: Capability | None

    @model_validator(mode="after")
    def detected_requires_capability(self):
        if self.is_learning_event and (not self.capability or not self.correction):
            raise ValueError("A detected correction requires a capability and correction")
        return self


class TaskSpec(Contract):
    id: Identifier
    family: Literal["filesystem", "json", "subprocess"]
    mode: Literal["execute", "simulate"]
    prompt: Text
    split: Literal["train", "heldout"]
    difficulty: int = Field(default=1, ge=1, le=3)
    function_name: Identifier

    @field_validator("function_name")
    @classmethod
    def valid_function(cls, value):
        if keyword.iskeyword(value) or value.startswith("__"):
            raise ValueError("Invalid Python function name")
        return value


class Curriculum(Contract):
    tasks: list[TaskSpec] = Field(min_length=12, max_length=18)

    @model_validator(mode="after")
    def balanced_and_disjoint(self):
        for key in ("id", "function_name", "prompt"):
            values = [getattr(t, key).strip().casefold() for t in self.tasks]
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate {key} in curriculum")
        train = [t for t in self.tasks if t.split == "train"]
        heldout = [t for t in self.tasks if t.split == "heldout"]
        if not 8 <= len(train) <= 12 or not 4 <= len(heldout) <= 6:
            raise ValueError("Require 8–12 train and 4–6 heldout tasks")
        if {(t.family, t.mode) for t in train} != {
            (f, m) for f in ("filesystem", "json", "subprocess")
            for m in ("execute", "simulate")
        }:
            raise ValueError("Training must cover all six family/mode combinations")
        if {t.mode for t in heldout} != {"execute", "simulate"}:
            raise ValueError("Heldout requires positive cases and counterexamples")
        if len({t.family for t in heldout}) < 2:
            raise ValueError("Heldout must span at least two effect families")
        return self


class RolloutResult(Contract):
    task_id: Identifier
    reward: Literal[0, 1]
    stdout: str = ""
    stderr: str = ""
    verifier_reason: str
    duration_ms: int = Field(ge=0)


class JsonResponseFormat(Contract):
    type: Literal["json_object"] = "json_object"


class Decoding(Contract):
    response_format: JsonResponseFormat = Field(default_factory=JsonResponseFormat)
    temperature: float = Field(default=0, ge=0, le=2)
    presence_penalty: float = Field(default=2, ge=-2, le=2)
    max_tokens: int = Field(default=2048, ge=64, le=8192)
    seed: int = 42
    max_turns: int = Field(default=6, ge=1, le=12)


class TrainingResult(Contract):
    run_id: str
    adapter_id: str
    model: str
    started_at: str
    finished_at: str


class ProofScore(Contract):
    passed: int = Field(ge=0)
    total: int = Field(ge=1)


class ProofProfile(BaseModel):
    model_id: str = Field(min_length=1)
    model_revision: str | None = None
    adapter_id: str | None = None
    score: ProofScore | None = None
    status: str


class ProofPost(ProofProfile):
    source: Literal["fallback", "real"]


class ProofTraining(BaseModel):
    status: Literal["not_started", "running", "completed", "failed"]
    run_id: str | None = None


class ProofState(BaseModel):
    objective: Literal["fixed_8_score"]
    pre: ProofProfile
    post: ProofPost
    training: ProofTraining
    experiment_id: Identifier
    manifest: str
    fallback_artifact: str
    proof_schema: str
    proof_schema_sha256: str


class ProofOutput(Contract):
    source: Literal["real", "fallback"]
    model_id: str
    model_revision: str | None
    adapter_id: str | None
    output: str
    messages: list[dict[str, str]]
    verifier: RolloutResult


class ProofComparison(Contract):
    proof_id: str
    task: TaskSpec
    prompt: str
    pre: ProofOutput
    post: ProofOutput
    claim: str

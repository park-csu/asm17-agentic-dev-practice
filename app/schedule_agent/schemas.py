from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ScheduleTask(BaseModel):
    title: str = Field(description="실행할 작업명")
    description: str = Field(default="", description="작업 설명")
    estimated_minutes: int = Field(default=30, ge=1, description="예상 소요 시간")
    order_index: int = Field(default=1, ge=1, description="실행 순서")


class ClassificationResult(BaseModel):
    is_decomposable: bool = Field(description="일정이 여러 하위 task로 분해할 가치가 있는지 여부")
    needs_question: bool = Field(description="분해 가능한 일정이지만 좋은 task 목록을 만들 맥락이 부족해 추가 질문이 필요한지 여부")
    question: str = Field(default="", description="추가 질문")
    detail_with_context: str = Field(description="누적된 일정 상세 컨텍스트")


class PreValidationResult(BaseModel):
    is_valid: bool = Field(description="일정 유효성 여부")
    needs_question: bool = Field(
        default=False,
        description="위치 제약 등 유효성 판단 정보가 부족해 사용자 확인이 필요한지 여부",
    )
    question: str = Field(
        default="",
        description="유효성 판단에 필요한 정보를 확인하는 단일 추가 질문",
    )
    normalized_schedule: dict = Field(default_factory=dict, description="정규화된 일정 정보")
    invalid_reason: str = Field(default="", description="유효하지 않은 이유")


class PlanResult(BaseModel):
    tasks: list[ScheduleTask] = Field(min_length=1, max_length=5, description="분해된 작업")
    plan_reason: str = Field(default="", description="작업 분해 이유")


class PostValidationResult(BaseModel):
    is_valid: bool = Field(description="작업 분해 결과 유효성")
    tasks: list[ScheduleTask] = Field(default_factory=list, description="검증된 작업")
    invalid_reason: str = Field(default="", description="유효하지 않은 이유")


class AgentState(TypedDict, total=False):
    title: str
    detail: str
    detail_with_context: str
    location: str
    context_answer: str
    start_time: str
    end_time: str
    existing_schedules: list[dict]

    classification_retry: int
    pre_validation_retry: int
    plan_retry: int
    max_retry: int

    is_decomposable: bool
    needs_question: bool
    question: str
    question_source: Literal["", "classification", "pre_validate"]
    is_valid: bool
    invalid_reason: str

    normalized_schedule: dict
    tasks: list[dict]
    plan_reason: str

    status: Literal["ok", "fallback", "needs_question"]
    fallback_reason: str
    answer: str


class ScheduleTaskRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    detail: str = Field(default="", max_length=4000)
    detail_with_context: str = Field(default="", max_length=8000)
    location: str = Field(default="", max_length=500)
    context_answer: str = Field(default="", max_length=4000)
    start_time: str = Field(default="", max_length=200)
    end_time: str = Field(default="", max_length=200)
    existing_schedules: list[dict] = Field(default_factory=list)
    question: str = Field(default="", max_length=4000)
    classification_retry: int = Field(default=0, ge=0)
    pre_validation_retry: int = Field(default=0, ge=0)
    plan_retry: int = Field(default=0, ge=0)
    max_retry: int = Field(default=2, ge=0, le=5)
    question_source: Literal["", "classification", "pre_validate"] = ""


class ScheduleTaskResponse(BaseModel):
    status: Literal["ok", "fallback", "needs_question"]
    title: str = ""
    detail_with_context: str = ""
    location: str = ""
    start_time: str = ""
    end_time: str = ""
    normalized_schedule: dict = Field(default_factory=dict)
    tasks: list[dict] = Field(default_factory=list)
    is_decomposable: bool = True
    question: str = ""
    classification_retry: int = 0
    pre_validation_retry: int = 0
    plan_retry: int = 0
    question_source: Literal["", "classification", "pre_validate"] = ""
    fallback_reason: str = ""
    answer: str = ""


class StreamEvent(BaseModel):
    event: str = "message"
    node: str = ""
    data: str = ""

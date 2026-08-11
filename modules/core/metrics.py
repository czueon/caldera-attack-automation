"""
메트릭 추적 모듈
LLM 사용량, 실행 시간, API 비용 등을 추적
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import contextmanager


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class LLMUsage:
    """LLM API 호출당 사용량"""
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float = 0.0
    duration_seconds: float = 0.0  # API 호출 자체(요청~응답)에 걸린 시간
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PhaseTiming:
    """Step 안의 세부 단계 소요 시간 (예: Step3 stage1/stage2, Step5 업로드/실행/재시도별)"""
    label: str
    duration_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class StepMetrics:
    """각 Step별 메트릭"""
    step_name: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    llm_calls: List[LLMUsage] = field(default_factory=list)
    phase_timings: List[PhaseTiming] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_llm_call_seconds: float = 0.0  # 이 Step 안 LLM API 호출 시간 합계
    status: str = "running"  # running, completed, failed
    error_message: str = ""


@dataclass
class ExperimentMetrics:
    """전체 실험 메트릭"""
    experiment_id: str
    pdf_name: str
    start_time: str
    end_time: Optional[str] = None
    total_duration_seconds: float = 0.0
    steps: List[StepMetrics] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_llm_call_seconds: float = 0.0  # 전체 LLM API 호출 시간 합계
    llm_provider: str = ""
    llm_model: str = ""
    status: str = "running"  # running, completed, failed


# ============================================================================
# Cost Calculator
# ============================================================================

class CostCalculator:
    """LLM API 비용 계산"""

    # 가격표 (USD per 1M tokens)
    PRICING = {
        # Claude (Latest 2025)
        "claude-opus-4-5-20251101": {"input": 5.0, "output": 25.0},
        "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        # Claude (Legacy)
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet-20240620": {"input": 3.0, "output": 15.0},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},

        # ChatGPT/OpenAI
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-4o": {"input": 2.5, "output": 10.0},
        "gpt-4o-mini": {"input": 0.150, "output": 0.600},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},

        # Gemini (Latest 2025)
        "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
        "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
        "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
        # Gemini (Legacy)
        "gemini-1.5-pro": {"input": 1.25, "output": 5.0},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.0-pro": {"input": 0.5, "output": 1.5},

        # Grok (Latest 2025)
        "grok-4": {"input": 3.0, "output": 15.0},
        "grok-4-fast-reasoning": {"input": 0.20, "output": 0.50},
        "grok-4-fast-non-reasoning": {"input": 0.20, "output": 0.50},
        "grok-4-1-fast-reasoning": {"input": 0.20, "output": 0.50},
        "grok-4-1-fast-non-reasoning": {"input": 0.20, "output": 0.50},
        # Grok (Legacy)
        "grok-beta": {"input": 5.0, "output": 15.0},
        "grok-2-1212": {"input": 2.0, "output": 10.0},
    }

    @classmethod
    def calculate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """비용 계산 (USD)"""
        pricing = cls.PRICING.get(model)

        if not pricing:
            # 알 수 없는 모델은 기본값 사용 (GPT-4 기준)
            pricing = {"input": 10.0, "output": 30.0}

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost


# ============================================================================
# Metrics Tracker
# ============================================================================

class MetricsTracker:
    """메트릭 추적 및 관리"""

    def __init__(self, experiment_id: str, pdf_name: str, llm_provider: str = "", llm_model: str = ""):
        self.experiment = ExperimentMetrics(
            experiment_id=experiment_id,
            pdf_name=pdf_name,
            start_time=datetime.now().isoformat(),
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        self._start_time = time.time()
        self._current_step: Optional[StepMetrics] = None
        self._step_start_time: Optional[float] = None

    @contextmanager
    def track_step(self, step_name: str):
        """Step 실행 시간 추적 context manager"""
        self.start_step(step_name)
        try:
            yield
            self.end_step(success=True)
        except Exception as e:
            self.end_step(success=False, error_message=str(e))
            raise

    def start_step(self, step_name: str):
        """Step 시작"""
        if self._current_step is not None:
            # 이전 step이 종료되지 않았으면 강제 종료
            self.end_step(success=False, error_message="Step interrupted by new step")

        self._current_step = StepMetrics(
            step_name=step_name,
            start_time=datetime.now().isoformat()
        )
        self._step_start_time = time.time()

    def end_step(self, success: bool = True, error_message: str = ""):
        """Step 종료"""
        if self._current_step is None:
            return

        self._current_step.end_time = datetime.now().isoformat()
        self._current_step.duration_seconds = time.time() - self._step_start_time
        self._current_step.status = "completed" if success else "failed"
        self._current_step.error_message = error_message

        # Step의 총 토큰/비용/LLM 호출 시간 계산
        for usage in self._current_step.llm_calls:
            self._current_step.total_input_tokens += usage.input_tokens
            self._current_step.total_output_tokens += usage.output_tokens
            self._current_step.total_tokens += usage.total_tokens
            self._current_step.total_cost += usage.cost
            self._current_step.total_llm_call_seconds += usage.duration_seconds

        self.experiment.steps.append(self._current_step)
        self._current_step = None
        self._step_start_time = None

    def record_llm_call(self, model: str, input_tokens: int, output_tokens: int, duration_seconds: float = 0.0):
        """LLM API 호출 기록 (duration_seconds: 요청~응답까지 걸린 시간)"""
        total_tokens = input_tokens + output_tokens
        cost = CostCalculator.calculate_cost(model, input_tokens, output_tokens)

        usage = LLMUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            duration_seconds=duration_seconds
        )

        if self._current_step is not None:
            self._current_step.llm_calls.append(usage)

        # 전체 실험 메트릭 업데이트
        self.experiment.total_llm_call_seconds += duration_seconds
        self.experiment.total_input_tokens += input_tokens
        self.experiment.total_output_tokens += output_tokens
        self.experiment.total_tokens += total_tokens
        self.experiment.total_cost += cost

    def record_phase(self, label: str, duration_seconds: float):
        """Step 안의 세부 단계 시간 기록 (예: 'upload', 'retry1_execution_wait', 'stage2_command_generation').
        현재 진행 중인 Step이 없으면 조용히 무시된다(호출 시점에 Step이 열려있어야 기록됨)."""
        if self._current_step is not None:
            self._current_step.phase_timings.append(PhaseTiming(label=label, duration_seconds=duration_seconds))

    @contextmanager
    def track_phase(self, label: str):
        """with tracker.track_phase("upload"): ... 형태로 구간 시간을 잴 때 사용."""
        start = time.time()
        try:
            yield
        finally:
            self.record_phase(label, time.time() - start)

    def finalize(self, success: bool = True):
        """실험 종료 및 최종 메트릭 계산"""
        # 현재 Step이 아직 종료되지 않았으면 종료
        if self._current_step is not None:
            self.end_step(success=success)

        self.experiment.end_time = datetime.now().isoformat()
        self.experiment.total_duration_seconds = time.time() - self._start_time
        self.experiment.status = "completed" if success else "failed"

    def save(self, output_path: str):
        """메트릭을 JSON 파일로 저장"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.experiment), f, indent=2, ensure_ascii=False)

    def get_summary(self) -> Dict:
        """메트릭 요약 반환"""
        return {
            "experiment_id": self.experiment.experiment_id,
            "pdf_name": self.experiment.pdf_name,
            "duration_seconds": self.experiment.total_duration_seconds,
            "duration_formatted": self._format_duration(self.experiment.total_duration_seconds),
            "total_llm_call_seconds": self.experiment.total_llm_call_seconds,
            "non_llm_call_seconds": max(0.0, self.experiment.total_duration_seconds - self.experiment.total_llm_call_seconds),
            "llm_provider": self.experiment.llm_provider,
            "llm_model": self.experiment.llm_model,
            "total_input_tokens": self.experiment.total_input_tokens,
            "total_output_tokens": self.experiment.total_output_tokens,
            "total_tokens": self.experiment.total_tokens,
            "total_cost_usd": round(self.experiment.total_cost, 4),
            "steps_completed": len([s for s in self.experiment.steps if s.status == "completed"]),
            "steps_failed": len([s for s in self.experiment.steps if s.status == "failed"]),
            "status": self.experiment.status
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """초를 사람이 읽기 쉬운 형식으로 변환"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


# ============================================================================
# Global Metrics Instance
# ============================================================================

_global_tracker: Optional[MetricsTracker] = None


def init_metrics(experiment_id: str, pdf_name: str, llm_provider: str = "", llm_model: str = "") -> MetricsTracker:
    """전역 메트릭 추적 초기화"""
    global _global_tracker
    _global_tracker = MetricsTracker(experiment_id, pdf_name, llm_provider, llm_model)
    return _global_tracker


def get_metrics_tracker() -> Optional[MetricsTracker]:
    """전역 메트릭 추적 인스턴스 반환"""
    return _global_tracker


def reset_metrics():
    """전역 메트릭 추적 리셋"""
    global _global_tracker
    _global_tracker = None

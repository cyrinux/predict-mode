from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from .dtw import dtw_distance
from .feature_extraction import (
    blend_series,
    extract_features,
    normalize_series,
    segment_phases,
    series_variance,
)


@dataclass
class PatternTemplate:
    template_id: str
    label: str
    samples: list[float]
    duration: float
    phases: list[dict[str, float]]
    count: int
    variance: float


@dataclass
class MatchResult:
    label: str | None = None
    phase: str | None = None
    confidence: float = 0.0
    time_remaining: float | None = None


class AppliancePatternModel:
    def __init__(self, sample_interval: int, match_threshold: float = 0.25) -> None:
        self._sample_interval = sample_interval
        self._match_threshold = match_threshold
        self._templates: list[PatternTemplate] = []

    @property
    def templates(self) -> list[PatternTemplate]:
        return self._templates

    def load(self, raw_templates: list[dict[str, Any]]) -> None:
        self._templates = [PatternTemplate(**item) for item in raw_templates]

    def serialize(self) -> list[dict[str, Any]]:
        return [asdict(template) for template in self._templates]

    def add_run(self, run_series: list[float]) -> str | None:
        normalized = normalize_series(run_series)
        if not normalized:
            return None
        features = extract_features(run_series, self._sample_interval)
        match = self._best_template(normalized)
        if match and match[1] <= self._match_threshold:
            template = match[0]
            template.samples = blend_series(template.samples, normalized)
            template.duration = (template.duration * template.count + features["duration"]) / (template.count + 1)
            template.variance = (
                template.variance * template.count + series_variance(normalized)
            ) / (template.count + 1)
            template.phases = segment_phases(template.samples)
            template.count += 1
            return template.label
        template = PatternTemplate(
            template_id=uuid4().hex,
            label=f"program_{len(self._templates) + 1}",
            samples=normalized,
            duration=features["duration"],
            phases=segment_phases(normalized),
            count=1,
            variance=series_variance(normalized),
        )
        self._templates.append(template)
        return template.label

    def match_window(self, window_series: list[float], elapsed: float) -> MatchResult:
        normalized = normalize_series(window_series)
        if not normalized or not self._templates:
            return MatchResult()
        match = self._best_template(normalized)
        if match is None:
            return MatchResult()
        template, distance = match
        denom = max(1.0, float(len(template.samples) + len(normalized)))
        confidence = max(0.0, 1.0 - distance / denom)
        time_remaining = max(0.0, template.duration - elapsed)
        return MatchResult(
            label=template.label,
            phase=self._phase_for_elapsed(template, elapsed),
            confidence=confidence,
            time_remaining=time_remaining,
        )

    def _phase_for_elapsed(self, template: PatternTemplate, elapsed: float) -> str | None:
        if not template.phases or template.duration <= 0:
            return None
        ratio = min(1.0, max(0.0, elapsed / template.duration))
        for phase in template.phases:
            if phase["start_ratio"] <= ratio < phase["end_ratio"]:
                return phase["name"]
        return template.phases[-1]["name"]

    def _best_template(self, normalized: list[float]) -> tuple[PatternTemplate, float] | None:
        best: tuple[PatternTemplate, float] | None = None
        for template in self._templates:
            distance = dtw_distance(normalized, template.samples)
            if not best or distance < best[1]:
                best = (template, distance)
        return best

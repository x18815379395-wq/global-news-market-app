"""
Adapter protocol + registry for pluggable news sources.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Protocol, Tuple, Type

from news.models import FetchCriteria, HealthStatus, NewsItem


class SourceAdapter(Protocol):
    name: str

    def fetch(self, criteria: FetchCriteria, *, now: datetime) -> Tuple[List[NewsItem], HealthStatus]:
        ...


@dataclass
class AdapterFactory:
    adapter_cls: Type[SourceAdapter]
    config: Dict[str, object]

    def build(self) -> SourceAdapter:
        return self.adapter_cls(**self.config)  # type: ignore[arg-type]


class AdapterRegistry:
    """
    Keeps track of all configured adapters (from YAML + env overrides).
    """

    def __init__(self) -> None:
        self._factories: Dict[str, AdapterFactory] = {}

    def register(self, key: str, factory: AdapterFactory) -> None:
        if key in self._factories:
            raise ValueError(f"Adapter '{key}' already registered")
        self._factories[key] = factory

    def build_all(self) -> List[SourceAdapter]:
        return [factory.build() for factory in self._factories.values()]

    def keys(self) -> Iterable[str]:
        return self._factories.keys()

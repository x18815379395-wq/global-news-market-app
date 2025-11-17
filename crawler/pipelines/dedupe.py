"""
Deduplication helpers for crawler outputs.
"""
from __future__ import annotations

import hashlib
from typing import Iterable, List, Sequence, Tuple, TypeVar

T = TypeVar("T")


def make_digest(parts: Sequence[str]) -> str:
    joined = "|".join(part or "" for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def dedupe_by_key(items: Iterable[T], key_fn) -> List[T]:
    seen = set()
    result: List[T] = []
    for item in items:
        key = key_fn(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


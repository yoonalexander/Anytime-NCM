"""Current/past decoded-token features; no references or future trajectory API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PrefixObservation:
    level: int
    code_length: int
    cumulative_codes: int
    decoded_ids: tuple[int, ...]


class CausalFeatureTracker:
    def __init__(self):
        self._previous = None
        self._level = 0
        self._cumulative = 0

    def observe(self, current: PrefixObservation) -> dict:
        ids = tuple(current.decoded_ids)
        if current.level != self._level + 1 or current.code_length <= 0:
            raise ValueError("Features require consecutive current observations.")
        if current.cumulative_codes != self._cumulative + current.code_length:
            raise ValueError("Cumulative code count is inconsistent.")
        if len(ids) != 89 or any(type(token) is not int or not 0 <= token <= 11 for token in ids):
            raise ValueError("Features require 89 legal decoded token IDs.")
        changes = None if self._previous is None else sum(
            left != right for left, right in zip(ids, self._previous, strict=True)
        ) / len(ids)
        result = {"level": current.level, "code_length": current.code_length,
                  "cumulative_codes": current.cumulative_codes, "token_change_fraction": changes}
        self._previous = ids
        self._level = current.level
        self._cumulative = current.cumulative_codes
        return result

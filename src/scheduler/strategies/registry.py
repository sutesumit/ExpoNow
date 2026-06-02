from dataclasses import dataclass
from typing import Callable

from src.scheduler.contract import SchedulerStrategy
from src.scheduler.strategies.cp_sat_strategy import CpSatStrategy, is_ortools_available
from src.scheduler.strategies.custom_heuristic import CustomHeuristicStrategy

DEFAULT_STRATEGY_ID = "custom_heuristic"


@dataclass(frozen=True)
class StrategyOption:
    id: str
    label: str
    description: str
    is_experimental: bool
    is_available: bool


@dataclass(frozen=True)
class _StrategyRegistration:
    option_factory: Callable[[], StrategyOption]
    strategy_factory: Callable[[], SchedulerStrategy]


def _custom_heuristic_option() -> StrategyOption:
    return StrategyOption(
        id="custom_heuristic",
        label="Custom heuristic",
        description="Deterministic greedy baseline that reserves charger slots bus by bus.",
        is_experimental=False,
        is_available=True,
    )


def _cp_sat_option() -> StrategyOption:
    return StrategyOption(
        id="cp_sat",
        label="OR-Tools CP-SAT (heuristic warm start)",
        description="Global optimizer using OR-Tools CP-SAT, warm-started from the custom heuristic solution.",
        is_experimental=False,
        is_available=is_ortools_available(),
    )


_REGISTRY: dict[str, _StrategyRegistration] = {
    "custom_heuristic": _StrategyRegistration(
        option_factory=_custom_heuristic_option,
        strategy_factory=CustomHeuristicStrategy,
    ),
    "cp_sat": _StrategyRegistration(
        option_factory=_cp_sat_option,
        strategy_factory=CpSatStrategy,
    ),
}


def list_strategy_options(include_unavailable: bool = False) -> list[StrategyOption]:
    options = [registration.option_factory() for registration in _REGISTRY.values()]
    if include_unavailable:
        return options
    return [option for option in options if option.is_available]


def get_strategy_option(strategy_id: str) -> StrategyOption:
    if strategy_id not in _REGISTRY:
        raise ValueError(f"Unknown scheduler strategy: {strategy_id}")
    return _REGISTRY[strategy_id].option_factory()


def get_strategy(strategy_id: str) -> SchedulerStrategy:
    if strategy_id not in _REGISTRY:
        raise ValueError(f"Unknown scheduler strategy: {strategy_id}")
    return _REGISTRY[strategy_id].strategy_factory()

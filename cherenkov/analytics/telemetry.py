from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass, field

# Domain
@dataclass
class RunStatistics:
    endpoints_tested: int = 0
    divergence_count: int = 0
    api_call_latencies_ms: List[float] = field(default_factory=list)

    @property
    def divergence_rate(self) -> float:
        if self.endpoints_tested == 0:
            return 0.0
        return self.divergence_count / self.endpoints_tested
        
    @property
    def average_latency_ms(self) -> float:
        if not self.api_call_latencies_ms:
            return 0.0
        return sum(self.api_call_latencies_ms) / len(self.api_call_latencies_ms)

# Ports
class TelemetryPort(ABC):
    @abstractmethod
    def record_endpoint_test(self, has_divergence: bool, latency_ms: float) -> None:
        pass

    @abstractmethod
    def get_statistics(self) -> RunStatistics:
        pass

# Adapters
class InMemoryTelemetry(TelemetryPort):
    def __init__(self):
        self._stats = RunStatistics()

    def record_endpoint_test(self, has_divergence: bool, latency_ms: float) -> None:
        self._stats.endpoints_tested += 1
        if has_divergence:
            self._stats.divergence_count += 1
        self._stats.api_call_latencies_ms.append(latency_ms)

    def get_statistics(self) -> RunStatistics:
        return self._stats

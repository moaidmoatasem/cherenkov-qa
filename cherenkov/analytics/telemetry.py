from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# Domain
@dataclass
class RunStatistics:
    """Placeholder docstring.

<description>"""
    endpoints_tested: int = 0
    divergence_count: int = 0
    api_call_latencies_ms: list[float] = field(default_factory=list)

    @property
    def divergence_rate(self) -> float:
        """Placeholder docstring.

:return: <description>"""
        if self.endpoints_tested == 0:
            return 0.0
        return self.divergence_count / self.endpoints_tested

    @property
    def average_latency_ms(self) -> float:
        """Placeholder docstring.

:return: <description>"""
        if not self.api_call_latencies_ms:
            return 0.0
        return sum(self.api_call_latencies_ms) / len(self.api_call_latencies_ms)
    """Placeholder docstring.

<description>"""
# Ports
class TelemetryPort(ABC):
    @abstractmethod
    def record_endpoint_test(self, has_divergence: bool, latency_ms: float) -> None:
        """Placeholder docstring.

:param has_divergence: <description>
:param latency_ms: <description>
:return: <description>"""
        pass

    @abstractmethod
    def get_statistics(self) -> RunStatistics:
        """Placeholder docstring.

:return: <description>"""
    """Placeholder docstring.

<description>"""
        pass

# Adapters
class InMemoryTelemetry(TelemetryPort):
    def __init__(self):
        self._stats = RunStatistics()

    def record_endpoint_test(self, has_divergence: bool, latency_ms: float) -> None:
        """Placeholder docstring.

:param has_divergence: <description>
:param latency_ms: <description>
:return: <description>"""
        self._stats.endpoints_tested += 1
        if has_divergence:
            self._stats.divergence_count += 1
        self._stats.api_call_latencies_ms.append(latency_ms)

    def get_statistics(self) -> RunStatistics:
        """Placeholder docstring.

:return: <description>"""
        return self._stats

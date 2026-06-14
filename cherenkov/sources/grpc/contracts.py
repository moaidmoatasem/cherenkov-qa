from dataclasses import dataclass
from cherenkov.core.contracts import Scenario

@dataclass
class gRPCScenario(Scenario):
    service: str = ""
    rpc_name: str = ""
    input_message: str = ""
    proto_content: str = ""

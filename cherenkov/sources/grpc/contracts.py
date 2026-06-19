from pydantic import BaseModel

class gRPCScenario(BaseModel):
    service: str = ""
    rpc_name: str = ""
    input_message: str = ""
    proto_content: str = ""
    case_type: str = ""
    mutation_id: str = ""
    expected_status: int = 200

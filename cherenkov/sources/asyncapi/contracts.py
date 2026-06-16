from pydantic import BaseModel


class AsyncAPIChannel(BaseModel):
    channel_name: str
    operations: list[str]  # publish, subscribe


class AsyncAPIOperation(BaseModel):
    channel: str
    operation: str  # publish | subscribe
    message_name: str | None = None
    content_type: str = "application/json"
    payload_schema: dict | None = None
    headers_schema: dict | None = None


class AsyncAPIScenario(BaseModel):
    channel: str
    operation: str
    scenario_type: str  # happy_path | invalid_payload | missing_required | auth
    message: str | None = None
    expected_status: int = 200
    required_fields: list[str] = []

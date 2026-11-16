from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# 1. Định nghĩa đặc tả Đầu vào (Inputs)
class ParserConfig(BaseModel):
    incremental: bool = Field(default=False, description="Chỉ quét các file có thay đổi")

class AgentInput(BaseModel):
    project_id: str
    run_id: str
    source_path: str
    language: str
    commit_hash: str
    target_files: Optional[List[str]] = Field(default_factory=list, description="Nếu rỗng, quét toàn bộ")
    parser_config: ParserConfig

# 2. Định nghĩa đặc tả Đầu ra (Outputs)
class Evidence(BaseModel):
    file_path: str
    line_start: int
    line_end: int

class CodeDependency(BaseModel):
    from_module: str
    to_module: str
    dependency_type: Literal["import", "call", "reference"]
    evidence: Evidence

class Payload(BaseModel):
    dependencies: List[CodeDependency]

class SourceCodeEnvelope(BaseModel):
    schema_version: str = "1.0"
    project_id: str
    run_id: str
    agent_name: str = "Source Code Analysis"
    status: Literal["SUCCESS", "PARTIAL", "FAILED"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str]
    payload: Payload
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
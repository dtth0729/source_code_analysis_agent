import concurrent.futures
from pathlib import Path
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END

# Import nội bộ theo Clean Architecture
from schema import AgentInput, SourceCodeEnvelope, CodeDependency, Payload
from parser import extract_dependencies

# 1. Định nghĩa Trạng thái (State) nội bộ cho đồ thị LangGraph
class SourceCodeState(TypedDict):
    input_config: AgentInput
    target_files: List[Path]
    raw_dependencies: List[Dict]
    errors: List[str]
    warnings: List[str]
    envelope: SourceCodeEnvelope

# 2. Định nghĩa các Node xử lý (Business Logic)
def node_filter_files(state: SourceCodeState):
    """Lọc và xác định danh sách file cần quét (Chuẩn bị cho Incremental Parsing)."""
    config = state["input_config"]
    source_path = Path(config.source_path)
    target_files = []
    errors = state.get("errors", [])
    
    if not source_path.exists():
        errors.append(f"Không tìm thấy thư mục mã nguồn: {source_path}")
        return {"target_files": [], "errors": errors}

    # Phân loại: Quét danh sách chỉ định hoặc quét toàn bộ dự án
    if config.target_files:
        for f in config.target_files:
            file_path = source_path / f
            if file_path.exists() and file_path.suffix == ".py":
                target_files.append(file_path)
    else:
        target_files = list(source_path.rglob("*.py"))
        
    return {"target_files": target_files}

def node_parse_and_extract(state: SourceCodeState):
    """Sử dụng đa tiến trình (ProcessPool) để chạy Tree-sitter lách giới hạn GIL."""
    target_files = state.get("target_files", [])
    raw_dependencies = []
    errors = state.get("errors", [])
    
    if not target_files:
        return {"raw_dependencies": [], "errors": errors}
        
    # Xử lý song song các file mã nguồn
    with concurrent.futures.ProcessPoolExecutor() as executor:
        future_to_file = {executor.submit(extract_dependencies, file): file for file in target_files}
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            try:
                deps = future.result()
                raw_dependencies.extend(deps)
            except Exception as exc:
                errors.append(f"Lỗi parse tại {file.name}: {exc}")
                
    return {"raw_dependencies": raw_dependencies, "errors": errors}

def node_package_envelope(state: SourceCodeState):
    """Xác thực kiểu dữ liệu và đóng gói thành JSON Envelope chuẩn."""
    config = state["input_config"]
    raw_dependencies = state.get("raw_dependencies", [])
    errors = state.get("errors", [])
    target_files = state.get("target_files", [])
    
    # Xác thực qua Pydantic CodeDependency
    valid_deps = []
    for dep in raw_dependencies:
        try:
            valid_deps.append(CodeDependency(**dep))
        except Exception:
            continue

    # Quyết định trạng thái trả về
    status = "SUCCESS"
    if errors:
        status = "PARTIAL" if valid_deps else "FAILED"

    envelope = SourceCodeEnvelope(
        project_id=config.project_id,
        run_id=config.run_id,
        status=status,
        confidence=0.95 if not errors else 0.7,
        evidence=[str(f) for f in target_files],
        payload=Payload(dependencies=valid_deps),
        errors=errors
    )
    
    return {"envelope": envelope}

# 3. Khởi tạo Đồ thị luồng công việc nội bộ (State Graph)
workflow = StateGraph(SourceCodeState)
workflow.add_node("filter_files", node_filter_files)
workflow.add_node("parse_and_extract", node_parse_and_extract)
workflow.add_node("package_envelope", node_package_envelope)

workflow.add_edge(START, "filter_files")
workflow.add_edge("filter_files", "parse_and_extract")
workflow.add_edge("parse_and_extract", "package_envelope")
workflow.add_edge("package_envelope", END)

app = workflow.compile()

# 4. Lớp vỏ bọc (Interface Layer) phơi bày cho Coordinator Agent bên ngoài
class SourceCodeAgent:
    """Lớp giao tiếp chính, che giấu sự phức tạp của LangGraph nội bộ."""
    async def run(self, input_data: dict) -> dict:
        # 1. Xác thực đầu vào có đúng định dạng cấu hình không
        try:
            agent_input = AgentInput(**input_data)
        except Exception as e:
            return {"status": "FAILED", "errors": [f"Input không hợp lệ: {str(e)}"]}
        
        # 2. Khởi tạo trạng thái và kích hoạt đồ thị
        initial_state = {
            "input_config": agent_input,
            "target_files": [],
            "raw_dependencies": [],
            "errors": [],
            "warnings": [],
        }
        
        final_state = app.invoke(initial_state)
        
        # 3. Ép xuất JSON chuẩn
        envelope = final_state.get("envelope")
        if envelope:
            return envelope.model_dump()
        return {"status": "FAILED", "errors": ["Lỗi chưa xác định trong LangGraph"]}
    
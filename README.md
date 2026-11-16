# Source Code Analysis Agent

**Source Code Analysis Agent** là một tác tử phân tích mã nguồn tĩnh (Static Code Analysis) được xây dựng theo kiến trúc mô-đun sạch (Clean Architecture). Tác tử sử dụng **Tree-sitter** để phân tích cây cú pháp trừu tượng (AST) đa tiến trình và **LangGraph** để điều phối luồng xử lý, trích xuất các phụ thuộc mã nguồn (dependencies) và đóng gói kết quả theo chuẩn dữ liệu **JSON Envelope** phục vụ cho hệ thống Multi-Agent.



## 1. Kiến trúc & Luồng hoạt động

Hệ thống được thiết kế theo mô hình đồ thị trạng thái (`StateGraph` của LangGraph) kết hợp xử lý song song (`ProcessPoolExecutor`) nhằm vượt qua giới hạn GIL của Python khi phân tích các dự án có quy mô lớn:

```text

  [Input: AgentInput]
           │
           ▼
   ┌───────────────┐
   │ filter_files  │  ──► Xác định & lọc danh sách tệp .py mục tiêu
   └───────┬───────┘
           │
           ▼
 ┌───────────────────┐
 │ parse_and_extract │  ──► Dựng cây AST bằng Tree-sitter (Đa tiến trình)
 └─────────┬─────────┘      & trích xuất các câu lệnh import
           │
           ▼
 ┌───────────────────┐
 │ package_envelope  │  ──► Xác thực Pydantic & đóng gói SourceCodeEnvelope
 └─────────┬─────────┘
           │
           ▼
[Output: JSON Envelope]

```


## 2. Cấu trúc thư mục

```text
source_code_analysis_agent/
├── agent.py              # Định nghĩa StateGraph (LangGraph) và lớp giao tiếp SourceCodeAgent
├── parser.py             # Engine Tree-sitter duyệt cây AST và trích xuất dependency
├── schema.py             # Các mô hình dữ liệu Pydantic (AgentInput, SourceCodeEnvelope)
├── requirements.txt      # Danh sách thư viện phụ thuộc
├── .gitignore            # Cấu hình loại trừ tệp rác/tạm khỏi Git
└── tests/
    ├── test_agent.py     # Công cụ CLI kiểm thử agent trên nhiều dự án
    ├── src/              # Tập dữ liệu mã nguồn mẫu chuẩn (py-clean-arch, notebooklm-py,...)
    ├── fault_src/        # Tập dữ liệu mã nguồn chứa lỗi/vi phạm kiến trúc
    └── result/           # Thư mục lưu kết quả JSON đầu ra sau khi chạy test

```


## 3. Yêu cầu hệ thống & Cài đặt

* **Python:** 3.10 trở lên

### Các bước cài đặt

1. **Clone repository về máy:**
```bash
git clone https://github.com/dtth0729/source_code_analysis_agent.git
cd source_code_analysis_agent

```


2. **Khởi tạo môi trường ảo và cài đặt thư viện:**
```bash
python3 -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate
pip install -r requirements.txt

```


## 4. Hướng dẫn sử dụng

### 4.1. Chạy kiểm thử qua dòng lệnh (CLI)

Sử dụng công cụ `tests/test_agent.py` để quét một thư mục dự án Python bất kỳ:

```bash
# Quét toàn bộ một dự án mẫu
python tests/test_agent.py -p tests/src/py-clean-arch

# Quét các tệp cụ thể và chỉ định đường dẫn file JSON đầu ra
python tests/test_agent.py \
  -p tests/src/py-clean-arch \
  --target-files main.py core/use_cases.py \
  -o tests/result/custom_output.json

```

**Các tham số hỗ trợ:**

* `-p`, `--path`: Đường dẫn tới thư mục dự án cần phân tích *(Bắt buộc)*.
* `--project-id`: Mã định danh dự án *(Mặc định: tự động lấy theo tên thư mục)*.
* `--run-id`: Mã định danh lượt chạy *(Mặc định: tự động sinh UUID ngắn)*.
* `--language`: Ngôn ngữ mã nguồn mục tiêu *(Mặc định: `python`)*.
* `--target-files`: Danh sách tệp `.py` cụ thể cần quét (cách nhau bởi dấu cách). Bỏ trống để quét toàn bộ dự án.
* `--incremental`: Bật cờ quét gia tăng (Incremental parsing).
* `-o`, `--output`: Đường dẫn lưu tệp kết quả JSON.

### 4.2. Tích hợp vào hệ thống Multi-Agent (Python API)

```python
import asyncio
from agent import SourceCodeAgent

async def run_analysis():
    agent = SourceCodeAgent()
    input_payload = {
        "project_id": "proj-demo",
        "run_id": "run-001",
        "source_path": "./tests/src/py-clean-arch",
        "language": "python",
        "commit_hash": "a1b2c3d",
        "target_files": [],
        "parser_config": {
            "incremental": False
        }
    }
    
    result = await agent.run(input_payload)
    print(f"Trạng thái: {result['status']}")
    print(f"Số lượng dependency: {len(result['payload']['dependencies'])}")

if __name__ == "__main__":
    asyncio.run(run_analysis())

```



## 5. Đặc tả dữ liệu (JSON Contract)

### Đầu vào (`AgentInput`)

```json
{
  "project_id": "proj-py-clean-arch",
  "run_id": "run-8f92a1b0",
  "source_path": "/path/to/repo",
  "language": "python",
  "commit_hash": "7c9e12a",
  "target_files": [],
  "parser_config": {
    "incremental": false
  }
}

```

### Đầu ra (`SourceCodeEnvelope`)

```json
{
  "schema_version": "1.0",
  "project_id": "proj-py-clean-arch",
  "run_id": "run-8f92a1b0",
  "agent_name": "Source Code Analysis",
  "status": "SUCCESS",
  "confidence": 0.95,
  "evidence": [
    "/path/to/repo/app/main.py"
  ],
  "payload": {
    "dependencies": [
      {
        "from_module": "main",
        "to_module": "fastapi",
        "dependency_type": "import",
        "evidence": {
          "file_path": "/path/to/repo/app/main.py",
          "line_start": 1,
          "line_end": 1
        }
      }
    ]
  },
  "warnings": [],
  "errors": []
}

```

---

## 6. Lộ trình phát triển (Roadmap)

* [x] Hỗ trợ trích xuất `import` và `from ... import ...` cho Python bằng Tree-sitter.


* [x] Xử lý song song đa tiến trình với `ProcessPoolExecutor`.


* [x] Chuẩn hóa dữ liệu vào/ra bằng Pydantic v2 (`SourceCodeEnvelope`).


* [ ] Mở rộng AST parser để trích xuất lời gọi hàm (`call`) và tham chiếu lớp (`reference`).


* [ ] Hoàn thiện cơ chế Incremental Parsing dựa trên `git diff` và `commit_hash`.

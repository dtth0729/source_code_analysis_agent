import sys
import asyncio
import argparse
import json
import uuid
import subprocess
from pathlib import Path

# Đưa thư mục gốc vào sys.path để import được agent.py, schema.py, parser.py
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from agent import SourceCodeAgent

def get_git_commit_hash(repo_path: Path) -> str:
    """Tự động lấy commit hash hiện tại của dự án nếu có Git."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return "UNKNOWN"

def parse_args():
    parser = argparse.ArgumentParser(description="Công cụ kiểm thử SourceCodeAgent cho nhiều dự án")
    parser.add_argument(
        "-p", "--path",
        required=True,
        help="Đường dẫn tới thư mục dự án cần quét (tương đối hoặc tuyệt đối)"
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="ID dự án (Mặc định: tự lấy theo tên thư mục dự án)"
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="ID lượt chạy (Mặc định: tự động sinh mã ngẫu nhiên)"
    )
    parser.add_argument(
        "--language",
        default="python",
        help="Ngôn ngữ lập trình (Mặc định: python)"
    )
    parser.add_argument(
        "--target-files",
        nargs="*",
        default=[],
        help="Danh sách các file .py cụ thể cần quét (cách nhau bởi dấu cách). Bỏ trống để quét toàn bộ."
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Bật cờ quét incremental trong parser_config"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Đường dẫn file JSON xuất kết quả (Mặc định: output_<project_id>.json)"
    )
    return parser.parse_args()

async def main():
    args = parse_args()
    
    # Chuẩn hóa đường dẫn dự án
    repo_path = Path(args.path).expanduser().resolve()
    
    # Tự động điền các thông tin nếu người dùng không truyền vào
    project_id = args.project_id or f"proj-{repo_path.name}"
    run_id = args.run_id or f"run-{uuid.uuid4().hex[:8]}"
    commit_hash = get_git_commit_hash(repo_path)

    input_payload = {
        "project_id": project_id,
        "run_id": run_id,
        "source_path": str(repo_path),
        "language": args.language,
        "commit_hash": commit_hash,
        "target_files": args.target_files,
        "parser_config": {
            "incremental": args.incremental
        }
    }

    print(f"Đang quét dự án [{project_id}] (Commit: {commit_hash}) tại: {repo_path} ...")
    
    agent = SourceCodeAgent()
    result = await agent.run(input_payload)

    print(f"Trạng thái: {result.get('status')}")
    print(f"Số file .py đã quét: {len(result.get('evidence', []))}")
    
    deps = result.get("payload", {}).get("dependencies", [])
    print(f"Tổng số dependency phát hiện được: {len(deps)}")
    
    if result.get("errors"):
        print("Các lỗi phát sinh:", result["errors"])

    # Tự động đặt tên file output theo tên dự án để không bị ghi đè khi test nhiều repo
    # Mặc định lưu vào thư mục results/ nếu không truyền -o
    output_file = Path(args.output) if args.output else ROOT_DIR / "tests" / "result" / f"output_{repo_path.name}.json"
    
    # Tự động tạo thư mục chứa file kết quả nếu chưa tồn tại
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Đã lưu kết quả chi tiết tại: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
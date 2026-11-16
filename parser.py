from pathlib import Path
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# 1. Khởi tạo Engine Tree-sitter với ngữ pháp Python
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

def extract_dependencies(file_path: Path) -> list[dict]:
    """
    Đọc tệp mã nguồn, dựng cây AST và trích xuất các câu lệnh import/call.
    Trả về danh sách dictionary tương thích với schema CodeDependency.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp: {file_path}")

    # Đọc mã nguồn dạng byte để Tree-sitter xử lý tọa độ chính xác
    code_bytes = file_path.read_bytes()
    tree = parser.parse(code_bytes)
    dependencies = []
    
    module_name_stem = file_path.stem

    def traverse(node):
        # Bắt lệnh: from <module> import ...
        if node.type == 'import_from_statement':
            module_node = node.child_by_field_name('module_name')
            if module_node:
                target_module = code_bytes[module_node.start_byte:module_node.end_byte].decode('utf-8')
                dependencies.append({
                    "from_module": module_name_stem,
                    "to_module": target_module,
                    "dependency_type": "import",
                    "evidence": {
                        "file_path": str(file_path),
                        "line_start": node.start_point[0] + 1,
                        "line_end": node.end_point[0] + 1
                    }
                })
                
        # Bắt lệnh: import <module>
        elif node.type == 'import_statement':
            for child in node.children:
                if child.type == 'dotted_name':
                    target_module = code_bytes[child.start_byte:child.end_byte].decode('utf-8')
                    dependencies.append({
                        "from_module": module_name_stem,
                        "to_module": target_module,
                        "dependency_type": "import",
                        "evidence": {
                            "file_path": str(file_path),
                            "line_start": node.start_point[0] + 1,
                            "line_end": node.end_point[0] + 1
                        }
                    })

        # Tiếp tục đệ quy sâu xuống các nhánh con của AST
        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return dependencies

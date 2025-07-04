
import ast
import os
from collections import defaultdict

def find_duplicate_functions(file_paths):
    functions = defaultdict(list)
    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                content = f.read()
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        function_name = node.name
                        function_code = ast.get_source_segment(content, node)
                        functions[function_name].append((file_path, function_code))
            except Exception as e:
                print(f"Could not parse {file_path}: {e}")


    duplicates = {}
    for function_name, funcs in functions.items():
        if len(funcs) > 1:
            code_map = defaultdict(list)
            for file_path, code in funcs:
                code_map[code].append(file_path)
            for code, files in code_map.items():
                if len(files) > 1:
                    if function_name not in duplicates:
                        duplicates[function_name] = []
                    duplicates[function_name].append({"files": files})

    return duplicates

if __name__ == "__main__":
    file_paths = [
        "E:/project/AI笔记本项目/backend/app/services/ai_service_langchain.py",
        "E:/project/AI笔记本项目/backend/check_tasks.py",
        "E:/project/AI笔记本项目/backend/app/services/task_processor_service.py",
        "E:/project/AI笔记本项目/backend/check_db_status.py",
        "E:/project/AI笔记本项目/backend/check_vectors.py",
        "E:/project/AI笔记本项目/backend/app/services/hierarchical_splitter.py",
        "E:/project/AI笔记本项目/backend/app/api/index.py",
        "E:/project/AI笔记本项目/backend/app/services/document_converter.py",
        "E:/project/AI笔记本项目/backend/app/services/vectorization_manager.py",
        "E:/project/AI笔记本项目/backend/app/services/index_service.py",
        "E:/project/AI笔记本项目/backend/app/services/file_service.py",
        "E:/project/AI笔记本项目/backend/app/api/file_upload.py",
        "E:/project/AI笔记本项目/backend/app/scripts/clean_database.py",
        "E:/project/AI笔记本项目/backend/app/config.py",
        "E:/project/AI笔记本项目/backend/app/models/embedding.py",
        "E:/project/AI笔记本项目/backend/app/main.py",
        "E:/project/AI笔记本项目/backend/app/services/mcp_service.py",
        "E:/project/AI笔记本项目/backend/app/models/link.py",
        "E:/project/AI笔记本项目/backend/app/services/link_service.py",
        "E:/project/AI笔记本项目/backend/app/schemas/link.py",
        "E:/project/AI笔记本项目/backend/app/api/ai.py",
        "E:/project/AI笔记本项目/backend/app/api/files.py",
        "E:/project/AI笔记本项目/backend/app/api/links.py",
        "E:/project/AI笔记本项目/backend/app/api/mcp.py",
        "E:/project/AI笔记本项目/backend/app/api/tags.py",
        "E:/project/AI笔记本项目/backend/app/database/init_db.py",
        "E:/project/AI笔记本项目/backend/app/database/session.py",
        "E:/project/AI笔记本项目/backend/app/models/base.py",
        "E:/project/AI笔记本项目/backend/app/models/chat_message.py",
        "E:/project/AI笔记本项目/backend/app/models/chat_session.py",
        "E:/project/AI笔记本项目/backend/app/models/file_tag.py",
        "E:/project/AI笔记本项目/backend/app/models/file.py",
        "E:/project/AI笔记本项目/backend/app/models/mcp_server.py",
        "E:/project/AI笔记本项目/backend/app/models/pending_task.py",
        "E:/project/AI笔记本项目/backend/app/models/search_history.py",
        "E:/project/AI笔记本项目/backend/app/models/system_config.py",
        "E:/project/AI笔记本项目/backend/app/models/tag.py",
        "E:/project/AI笔记本项目/backend/app/schemas/file.py",
        "E:/project/AI笔记本项目/backend/app/schemas/mcp.py",
        "E:/project/AI笔记本项目/backend/app/schemas/tag.py",
        "E:/project/AI笔记本项目/backend/app/services/search_service.py",
        "E:/project/AI笔记本项目/backend/app/services/tag_service.py",
        "E:/project/AI笔记本项目/backend/test_index_api.py",
        "E:/project/AI笔记本项目/backend/tests/conftest.py",
        "E:/project/AI笔记本项目/backend/tests/test_files_api.py",
        "E:/project/AI笔记本项目/backend/tests/test_links_api.py",
        "E:/project/AI笔记本项目/backend/tests/test_tags_api.py"
    ]
    duplicates = find_duplicate_functions(file_paths)
    if duplicates:
        print("Found duplicate functions:")
        for func_name, funcs in duplicates.items():
            print(f"  Function '{func_name}':")
            for item in funcs:
                print(f"    Found in files: {', '.join(item['files'])}")
    else:
        print("No duplicate functions found.")

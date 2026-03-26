import os
import glob
from pageindex import PageIndexClient
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, "../..", ".env")
load_dotenv(dotenv_path)

# 从环境变量或配置文件读取参数
API_KEY = os.getenv("PAGEINDEX_API_KEY")
DOCS_DIR = os.getenv("PAGEINDEX_DOCS_DIR")

def index_all_docs():
    if not API_KEY:
        print("错误: 请先设置正确的 PAGEINDEX_API_KEY")
        return
    if not DOCS_DIR:
        print("错误: 请先设置正确的 PAGEINDEX_DOCS_DIR")
        return
        
    client = PageIndexClient(api_key=API_KEY)
    
    # 查找所有 pdf 和 txt
    files = glob.glob(os.path.join(DOCS_DIR, "*.pdf")) + glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    
    if not files:
        print(f"在 {DOCS_DIR} 中未找到文件")
        return

    for file_path in files:
        print(f"正在索引文件: {os.path.basename(file_path)}...")
        try:
            # 提交文档进行索引
            response = client.submit_document(file_path=file_path)
            # print(f"DEBUG: 原始返回结果: {response}")
            doc_id = response.get("document_id") or response.get("id") or response.get("doc_id")
            if doc_id:
                print(f"成功提交! 文档 ID: {doc_id}")
            else:
                print(f"成功提交，但未获取到 ID。完整返回: {response}")
        except Exception as e:
            print(f"索引 {file_path} 失败: {e}")

if __name__ == "__main__":
    index_all_docs()

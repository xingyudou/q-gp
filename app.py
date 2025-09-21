from flask import Flask
import threading, os

# === 后台任务 ===
def main_task():
    # 这里导入你的主脚本
    # 确保 main_full_integrated_onedrive.py 在同目录
    import main_full_integrated_onedrive  
    # 如果 main_full_integrated_onedrive.py 有 main() 函数，就在这里调用
    # main_full_integrated_onedrive.main()

# 启动后台线程
threading.Thread(target=main_task, daemon=True).start()

# === Flask Web 服务 ===
app = Flask(__name__)

@app.route("/")
def index():
    return "后台任务正在运行中（QQ邮箱+Telegram 自动回复）"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render 会提供 PORT
    app.run(host="0.0.0.0", port=port)

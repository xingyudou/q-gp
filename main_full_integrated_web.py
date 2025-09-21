import os
import threading
from flask import Flask
import time
import imaplib
import smtplib
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from gpt4all import GPT4All
from datetime import datetime
import requests

# =======================
# 环境变量配置
# =======================
QQ_EMAIL = os.getenv("QQ_EMAIL")
QQ_AUTH_CODE = os.getenv("QQ_AUTH_CODE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MODEL_URL = os.getenv("MODEL_URL")  # OneDrive 共享链接
MODEL_PATH = "ggml-gpt4all-j-v1.3-groovy.bin"

# =======================
# 日志函数
# =======================
def log(message):
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"logs_{today}.txt"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)
    send_telegram(f"[{timestamp}] {message}")

# =======================
# Telegram 功能
# =======================
def send_telegram(message: str, chat_id=TELEGRAM_CHAT_ID):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code != 200:
            print(f"❌ Telegram 消息发送失败: {r.status_code}, {r.text}")
    except Exception as e:
        print(f"❌ Telegram 异常: {e}")

def check_telegram(model):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if not data.get("ok"):
            return
        for result in data["result"]:
            update_id = result["update_id"]
            message = result.get("message")
            if message:
                chat_id = message["chat"]["id"]
                text = message.get("text")
                if text:
                    reply = model.generate(f"请用简短正式的语气回复：{text}")
                    send_telegram(reply, chat_id)
                    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={update_id+1}")
    except Exception as e:
        log(f"❌ Telegram 检查异常: {e}")

# =======================
# 模型下载（OneDrive）
# =======================
def download_model(url, destination):
    if os.path.exists(destination):
        print("✅ 模型已存在，跳过下载")
        return
    print(f"⏳ 开始下载模型到 {destination} ...")
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(destination, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
    print("✅ 模型下载完成")

download_model(MODEL_URL, MODEL_PATH)

# =======================
# 初始化 GPT4All
# =======================
try:
    model = GPT4All(MODEL_PATH)
    log("✅ AI 模型加载成功")
except Exception as e:
    log(f"❌ AI 模型加载失败: {e}")
    model = None

# =======================
# QQ 邮箱处理
# =======================
IMAP_SERVER = 'imap.qq.com'
IMAP_PORT = 993
SMTP_SERVER = 'smtp.qq.com'
SMTP_PORT = 465

def check_email():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(QQ_EMAIL, QQ_AUTH_CODE)
        mail.select("INBOX")
        status, messages = mail.search(None, 'UNSEEN')
        if status != "OK":
            log("❌ 获取邮件失败")
            return []
        email_ids = messages[0].split()
        unseen_emails = []
        for eid in email_ids:
            status, msg_data = mail.fetch(eid, '(RFC822)')
            if status != "OK":
                continue
            raw_email = msg_data[0][1]
            parsed_email = BytesParser(policy=default).parsebytes(raw_email)
            unseen_emails.append(parsed_email)
        mail.logout()
        return unseen_emails
    except Exception as e:
        log(f"❌ 检查邮箱失败: {e}")
        return []

def send_email(to_addr, subject, content):
    try:
        msg = EmailMessage()
        msg['From'] = QQ_EMAIL
        msg['To'] = to_addr
        msg['Subject'] = subject
        msg.set_content(content)
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(QQ_EMAIL, QQ_AUTH_CODE)
        server.send_message(msg)
        server.quit()
        log(f"✅ 已发送回复给 {to_addr}, 主题: {subject}")
    except Exception as e:
        log(f"❌ 发送邮件失败: {e}")

def generate_reply(email_content):
    if model is None:
        return "抱歉，AI 模型未加载。"
    prompt = f"请用正式、简短的邮件语气回复以下内容：\n{email_content}"
    try:
        reply = model.generate(prompt)
        log(f"✅ AI 生成成功，内容前50字: {reply[:50]}...")
        return reply
    except Exception as e:
        log(f"❌ AI 生成失败: {e}")
        return "抱歉，AI 生成失败。"

# =======================
# 主循环任务
# =======================
def main_loop():
    log("=== QQ 邮箱 + Telegram 自动回复服务启动 ===")
    base_interval = 30
    while True:
        # 邮箱处理
        emails = check_email()
        if emails:
            log(f"发现 {len(emails)} 封新邮件")
            for i,email_msg in enumerate(emails, start=1):
                from_addr = email_msg['From']
                subject = email_msg['Subject'] or f"自动回复 第{i}封邮件"
                content = email_msg.get_body(preferencelist=('plain')).get_content() if email_msg.get_body(preferencelist=('plain')) else ""
                log(f"📩 处理第{i}封邮件, 发件人: {from_addr}, 主题: {subject}")
                reply = generate_reply(content)
                send_email(from_addr, f"Re: {subject}", reply)
            interval = base_interval/2
        else:
            log("没有新邮件，等待下一次检查...")
            interval = base_interval

        # Telegram 处理
        check_telegram(model)

        time.sleep(interval)

# =======================
# Flask Web 端口（Render 需要）
# =======================
app = Flask(__name__)

@app.route("/")
def index():
    return "后台任务正在运行"

if __name__ == "__main__":
    # 后台线程运行主循环
    threading.Thread(target=main_loop, daemon=True).start()
    # Render 默认端口
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

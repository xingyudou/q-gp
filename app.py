import os
import time
import threading
from flask import Flask
import imaplib
import email
import smtplib
from email.mime.text import MIMEText
import telebot

# =======================
# 环境变量
# =======================
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

IMAP_SERVER = "imap.qq.com"
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 587

# =======================
# 日志函数
# =======================
def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# =======================
# GPT 生成函数（示例）
# =======================
def generate_reply(content):
    try:
        # 这里调用 GPT4All 或你用的模型
        reply = f"智能回复: {content}"  # 示例
        log(f"✅ AI 生成成功，内容前50字: {reply[:50]}...")
        return reply
    except Exception as e:
        log(f"❌ AI 生成失败: {e}")
        return "抱歉，AI 生成失败。"

# =======================
# QQ 邮箱处理
# =======================
def check_email():
    emails = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
        status, data = mail.search(None, 'UNSEEN')
        mail_ids = data[0].split()
        for num in mail_ids:
            status, data = mail.fetch(num, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            emails.append(msg)
        mail.close()
        mail.logout()
    except Exception as e:
        log(f"邮箱检查错误: {e}")
    return emails

def send_email(to_addr, subject, text):
    try:
        msg = MIMEText(text)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_addr
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_addr, msg.as_string())
        server.quit()
        log(f"✅ 已回复邮件: {to_addr}")
    except Exception as e:
        log(f"发送邮件失败: {e}")

def email_loop():
    log("📧 QQ 邮箱自动回复线程启动")
    while True:
        emails = check_email()
        if emails:
            log(f"发现 {len(emails)} 封新邮件")
            for i, msg in enumerate(emails, start=1):
                from_addr = email.utils.parseaddr(msg['From'])[1]
                subject = msg['Subject'] or f"自动回复 第{i}封邮件"
                body = msg.get_payload(decode=True).decode(errors='ignore') if msg.get_payload() else ""
                reply = generate_reply(body)
                send_email(from_addr, f"Re: {subject}", reply)
        time.sleep(60)

# =======================
# Telegram Bot 处理
# =======================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda msg: True)
def reply(message):
    response = generate_reply(message.text)
    bot.reply_to(message, response)

def telegram_loop():
    log("🤖 Telegram Bot 线程启动")
    bot.polling(none_stop=True)

# =======================
# Flask Web 服务
# =======================
app = Flask(__name__)

@app.route("/")
def index():
    return "QQ邮箱 + Telegram 自动回复服务运行中…"

if __name__ == "__main__":
    # 启动后台线程
    threading.Thread(target=email_loop, daemon=True).start()
    threading.Thread(target=telegram_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

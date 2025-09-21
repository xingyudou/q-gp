import imaplib, smtplib, email, os, time
from email.mime.text import MIMEText
from openai import OpenAI

# 读取环境变量（Render 的 Settings → Environment）
IMAP_SERVER = 'imap.qq.com'
SMTP_SERVER = 'smtp.qq.com'
EMAIL_ACCOUNT = os.getenv("QQ_EMAIL")
EMAIL_PASSWORD = os.getenv("QQ_AUTH_CODE")
OPENAI_KEY = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_KEY)

def check_and_reply():
    """检查 QQ 邮箱未读邮件并用 GPT 自动回复"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    mail.select('INBOX')
    status, data = mail.search(None, 'UNSEEN')
    mail_ids = data[0].split()

    for num in mail_ids:
        status, msg_data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        from_addr = email.utils.parseaddr(msg['From'])[1]
        subject = msg['Subject']
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode()
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                pass

        # 调用 OpenAI GPT 生成回复
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"请帮我写一封简短友好的回复：{body}"}]
        )
        reply_text = response.choices[0].message.content

        # 发送回复邮件
        msg_reply = MIMEText(reply_text, 'plain', 'utf-8')
        msg_reply['Subject'] = 'Re: ' + subject
        msg_reply['From'] = EMAIL_ACCOUNT
        msg_reply['To'] = from_addr

        smtp = smtplib.SMTP_SSL(SMTP_SERVER, 465)
        smtp.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_ACCOUNT, from_addr, msg_reply.as_string())
        smtp.quit()

    mail.logout()

if __name__ == "__main__":
    while True:
        check_and_reply()
        time.sleep(300)  # 每 5 分钟检查一次
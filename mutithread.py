import smtplib
import email
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header
import time
from UNSWtalk import DB

from_addr = 'lll109512@outlook.com'
password = 'q66300465215901'
smtp_server = 'smtp-mail.outlook.com'

def EmailSender(Q):
    while True:
        while not Q.empty():
            arg = Q.get()
            if arg['type'] == 'Friend_request':
                # to_addr = ['lll109512@outlook.com']
                data = arg['data']
                to_addr = [data['user_info']['email']]
                mail_msg = f"""
                <h2>UNSWtalk</h2>
                <p>You just receive a new firend request of {data['sender_zid']}</p>
                <p><a href="{data['maddr']}">Click to accept this request</a></p>
                """
                message = MIMEText(mail_msg, 'html', 'utf-8')
                message['From'] = Header("UNSWtalk", 'utf-8')
                message['To'] = to_addr[0]

                subject = f"New firend request"
                message['Subject'] = Header(subject, 'utf-8')

            elif arg['type'] == 'Pass_recover':
                data = arg['data']

                to_addr = [data['email']]

                mail_msg = f"""
                <h2>UNSWtalk</h2>
                <p>Dear {data['zid']},</p>
                <p>This is the new password of your account.</p>
                <p>Change your password as soon as possible.</p>
                <p>Password: {data['new_pass']}</p>
                """

                message = MIMEText(mail_msg, 'html', 'utf-8')
                message['From'] = Header("UNSWtalk", 'utf-8')
                message['To'] = to_addr[0]

                subject = f"Password recover"
                message['Subject'] = Header(subject, 'utf-8')

            elif arg['type'] == 'Notifications':
                data = arg['data']
                to_addr = [data['email']]
                if DB.GetSuspend(data['zid']) == 'T':
                    continue
                mail_msg = f"""
                <h2>UNSWtalk</h2>
                <p>Dear {data['zid']},</p>
                <p>A new {data['rtype']} mentioned you .</p>
                <p><a href="{data['addr']}">Click to view this {data['rtype']}</a></p>
                """

                message = MIMEText(mail_msg, 'html', 'utf-8')
                message['From'] = Header("UNSWtalk", 'utf-8')
                message['To'] = to_addr[0]

                subject = f"A new {data['rtype']} mentioned you"
                message['Subject'] = Header(subject, 'utf-8')

            elif arg['type'] == 'Signup':
                data = arg['data']
                to_addr = [data['email']]

                mail_msg = f"""
                <h2>UNSWtalk</h2>
                <p>Dear {data['zid']},</p>
                <p>Thank you for signing up UNSWtalk.</p>
                <p>This email is use to verify your email address.</p>
                <p><a href="{data['addr']}">Click to finish your signup</a></p>
                """

                message = MIMEText(mail_msg, 'html', 'utf-8')
                message['From'] = Header("UNSWtalk", 'utf-8')
                message['To'] = to_addr[0]

                subject = f"Final step to sign up"
                message['Subject'] = Header(subject, 'utf-8')

            else:
                print("Error in email type")
                break


            try:
                server = smtplib.SMTP(smtp_server,587) # SMTP协议默认端口是25
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(from_addr, password)
                server.sendmail(from_addr, to_addr, message.as_string())
                server.quit()
            except Exception as e:
                print(e)
                raise e
        time.sleep(5)

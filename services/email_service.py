import logging
from draup_packages.draup_email import DraupEmail
from common.common_utils import TEAM_NAME, PURPOSE

email_handler = DraupEmail(
team_name=TEAM_NAME, purpose=PURPOSE,
)

logger = logging.getLogger('iris-logger')


def send_mail_through_draup_services(subject, body, recipients_list, cc_list=None, attachments_list=None):
    """
    Send email using DraupEmail class
    :param subject: Subject of the email string e.g. "random subject text"
    :param body: Body of the email
    :param recipients_list: List of recipients e.g. ["abc@gmail.com"]
    :param cc_list: List of CC recipients optional params e.g ["abc@gmail.com"]
    :param attachments_list: optional params, list of attachment file paths e.g. ["/Users/folder1/abc.txt"]
    :return: None
    """
    try:
        email_handler.send_email(
            recipients_list=recipients_list,
            subject=subject,
            body=body,
            cc_list=cc_list,
            attachments=attachments_list
        )
    except Exception as e:
        logger.info(f"Error while sending mail: {e}")


class EmailService:
    def __init__(self):
        pass
        
    def send_otp_email(self, to_email: str, otp: str, user_name: str = None) -> bool:
        try:
            subject = "Your OTP for Login"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    .container {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 20px;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                        background-color: white;
                    }}
                    .header {{
                        text-align: center;
                        border-bottom: 1px solid #eee;
                    }}
                    .logo {{
                        max-width: 100px;
                        height: auto;
                    }}
                    .content {{
                        padding: 30px 0;
                    }}
                    .otp-container {{
                        background-color: #f8f9fa;
                        border: 2px solid #007bff;
                        border-radius: 8px;
                        padding: 30px;
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .otp-code {{
                        font-size: 48px;
                        font-weight: bold;
                        color: #007bff;
                        font-family: 'Courier New', monospace;
                        user-select: text;
                        -webkit-user-select: text;
                        -moz-user-select: text;
                        -ms-user-select: text;
                    }}
                    .info-box {{
                        background-color: #e7f3ff;
                        border-left: 4px solid #007bff;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .footer {{
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://mcusercontent.com/497e5bac1c91f72f11daff6ec/images/246d2e82-537b-935c-8e57-6dae4175f346.png" alt="Draup Logo" class="logo">
                    </div>
                    <div class="content">
                        <p>Hello <strong>{user_name or 'there'}</strong>,</p>
                        <p>Your OTP for login is:</p>
                        
                        <div class="otp-container">
                            <div class="otp-code" id="otp-code">{otp}</div>
                        </div>
                        
                        <div class="info-box">
                            <p style="margin: 0;"><strong>⏰ This OTP is valid for 15 minutes</strong></p>
                            <p style="margin: 5px 0 0 0; font-size: 14px;">If you didn't request this OTP, please ignore this email.</p>
                        </div>
                        
                        <div class="footer">
                            <p>This is an automated message, please do not reply.</p>
                            <p>© Draup. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Login Verification
            
            Hello {user_name or 'there'},
            
            Your OTP for login is: {otp}
            
            This OTP is valid for 15 minutes.
            
            If you didn't request this OTP, please ignore this email.
            
            This is an automated message, please do not reply.
            """
            
            send_mail_through_draup_services(
                subject=subject,
                body=html_content,
                recipients_list=[to_email]
            )
                
            print(f"OTP email sent successfully to {to_email}")
            print(f"Otp code: {otp}")
            return True
            
        except Exception as e:
            print(f"Failed to send OTP email to {to_email}: {str(e)}")
            return False
    
    def send_resend_otp_email(self, to_email: str, otp: str, user_name: str = None) -> bool:
        try:
            subject = "Your New OTP for Login"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    .container {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                        background-color: white;
                    }}
                    .header {{
                        text-align: center;
                        padding: 20px 0;
                        border-bottom: 1px solid #eee;
                    }}
                    .logo {{
                        max-width: 120px;
                        height: auto;
                    }}
                    .content {{
                        padding: 30px 0;
                    }}
                    .otp-container {{
                        background-color: #f8f9fa;
                        border: 2px solid #28a745;
                        border-radius: 8px;
                        padding: 30px;
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .otp-code {{
                        font-size: 48px;
                        font-weight: bold;
                        color: #28a745;
                        letter-spacing: 12px;
                        margin: 10px 0;
                        font-family: 'Courier New', monospace;
                        user-select: text;
                        -webkit-user-select: text;
                        -moz-user-select: text;
                        -ms-user-select: text;
                    }}
                    .info-box {{
                        background-color: #e7f5e7;
                        border-left: 4px solid #28a745;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .footer {{
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://mcusercontent.com/497e5bac1c91f72f11daff6ec/images/246d2e82-537b-935c-8e57-6dae4175f346.png" alt="Draup Logo" class="logo">
                    </div>
                    <div class="content">
                        <p>Hello <strong>{user_name or 'there'}</strong>,</p>
                        <p>Your new OTP for login is:</p>
                        
                        <div class="otp-container">
                            <div class="otp-code" id="otp-code">{otp}</div>
                        </div>
                        
                        <div class="info-box">
                            <p style="margin: 0;"><strong>⏰ This OTP is valid for 15 minutes</strong></p>
                            <p style="margin: 5px 0 0 0; font-size: 14px;">Your previous OTP has been invalidated for security.</p>
                            <p style="margin: 5px 0 0 0; font-size: 14px;">If you didn't request this OTP, please ignore this email.</p>
                        </div>
                        
                        <div class="footer">
                            <p>This is an automated message, please do not reply.</p>
                            <p>© Draup. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_mail_through_draup_services(
                subject=subject,
                body=html_content,
                recipients_list=[to_email]
            )
                
            print(f"Resend OTP email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"Failed to send resend OTP email to {to_email}: {str(e)}")
            return False


    def send_user_registration_email(self, to_email: str, username: str, first_name: str, last_name: str, login_link: str) -> bool:
        try:
            subject = "Welcome to Etter - Your Account Has Been Created"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    .container {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 20px;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                        background-color: white;
                    }}
                    .header {{
                        text-align: center;
                        border-bottom: 1px solid #eee;
                        padding-bottom: 20px;
                    }}
                    .logo {{
                        max-width: 100px;
                        height: auto;
                    }}
                    .content {{
                        padding: 30px 0;
                    }}
                    .welcome-message {{
                        background-color: #f8f9fa;
                        border-left: 4px solid #28a745;
                        padding: 20px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .login-button {{
                        display: inline-block;
                        background-color: #007bff;
                        color: #ffffff;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 6px;
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                    .login-button:hover {{
                        background-color: #0056b3;
                         color: #ffffff;
                    }}
                    .info-box {{
                        background-color: #e7f3ff;
                        border-left: 4px solid #007bff;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .footer {{
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://mcusercontent.com/497e5bac1c91f72f11daff6ec/images/246d2e82-537b-935c-8e57-6dae4175f346.png" alt="Draup Logo" class="logo">
                        <h2>Welcome to Etter!</h2>
                    </div>
                    <div class="content">
                        <div class="welcome-message">
                            <p>Hello <strong>{first_name} {last_name}</strong>,</p>
                            <p>Your account has been successfully created by an administrator.</p>
                        </div>
                        
                        <p>Here are your account details:</p>
                        <ul>
                            <li><strong>Username:</strong> {username}</li>
                            <li><strong>Email:</strong> {to_email}</li>
                        </ul>
                        
                        <div style="text-align: center;">
                            <a href="{login_link}" class="login-button">Access Your Account</a>
                        </div>
                        
                        <p style="font-size: 14px; color: #666;">
                            If the button doesn't work, you can copy and paste this link into your browser:<br>
                            <a href="{login_link}" style="color: #007bff;">{login_link}</a>
                        </p>
                        
                        <div class="footer">
                            <p>This is an automated message, please do not reply.</p>
                            <p>© Draup. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Welcome to Etter!
            
            Hello {first_name} {last_name},
            
            Your account has been successfully created by an administrator.
            
            Account Details:
            - Username: {username}
            - Email: {to_email}
            
            Next Steps:
            Click the following link to access your account and set up your password:
            {login_link}
            
            This is an automated message, please do not reply.
            """
            
            send_mail_through_draup_services(
                subject=subject,
                body=html_content,
                recipients_list=[to_email]
            )
                
            print(f"User registration email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"Failed to send user registration email to {to_email}: {str(e)}")
            return False


email_service = EmailService()

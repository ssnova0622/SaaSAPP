from environs import Env
import logging

env = Env()
env.read_env()

# MongoDB Configuration
MONGO_URI = env.str('MONGO_URI', 'mongodb://localhost:27017/saas_db')

# Twilio API Configuration (if you're using Twilio for WhatsApp)
# TWILIO_ACCOUNT_SID =env.str('TWILIO_ACCOUNT_SID','ACd8455419c9ff8c0e6b5bdbf9f870445f')
# TWILIO_AUTH_TOKEN =env.str('TWILIO_AUTH_TOKEN','b488483fd1b813a9e62cc320eedf367c')
# TWILIO_PHONE_NUMBER =env.str('TWILIO_PHONE_NUMBER','+14155238886')

# FastAPI Configuration
SECRET_KEY = env.str('SECRET_KEY', '')
DEBUG = env.bool('DEBUG', True)
LOGGER = env.str("LOGGER", default="console")
logger = logging.getLogger(LOGGER)

# File Uploads Configuration
UPLOAD_FOLDER = env.str('UPLOAD_FOLDER', 'static/uploads')

# WhatsApp API Configuration (if using Twilio API or similar service)
WHATSAPP_API_URL = env.str('WHATSAPP_API_URL', 'https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json')

# AI/LLM Configuration (optional)
OPENAI_API_KEY = env.str('OPENAI_API_KEY', '')
AI_MODEL = env.str('AI_MODEL', 'gpt-4o-mini')
AI_ENABLED = env.bool('AI_ENABLED', False)
TWILIO_ENABLED = env.bool('TWILIO_ENABLED', True)

############ MOCK DATA Starts Here
MOCK_TENANT_ID = env.str('MOCK_TENANT_ID', "tenant_demo")
# Demo tenant (used for mock seed/delete and for testing in admin UI)
MOCK_TENANT_NAME = env.str('MOCK_TENANT_NAME', "Demo Tenant")

# Demo tenant admin: login with this email/password to access the demo tenant
MOCK_EMAIL = env.str("MOCK_EMAIL", "testtenant@example.com")
MOCK_PASSWORD = env.str("MOCK_PASSWORD", "123456")

# Super admin: global login (no tenant)
MOCK_SUPER_ADMIN_EMAIL = env.str("MOCK_SUPER_ADMIN_EMAIL", "superadmin@example.com")
MOCK_SUPER_ADMIN_PASSWORD = env.str("MOCK_SUPER_ADMIN_PASSWORD", "123456")
MOCK_SUPER_ADMIN_DISPLAY_NAME = env.str("SUPER_ADMIN_DISPLAY_NAME", "Super Admin")

# Fixed ids for demo user (tenant_admin for demo tenant)
MOCK_USER_ID = "user_demo_tenant_admin"
############ MOCK DATA Ends Here

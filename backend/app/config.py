import os
import secrets
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/qvanish.db")

# 安全配置
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24小时
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # 7天

# API安全配置
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_ATTEMPT_TIMEOUT = int(os.getenv("LOGIN_ATTEMPT_TIMEOUT", "900"))  # 15分钟
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "100"))  # 每分钟最大请求数

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Redis缓存配置
REDIS_URL = os.getenv("REDIS_URL", None)  # 例如: "redis://localhost:6379/0"
CACHE_DEFAULT_EXPIRE = int(os.getenv("CACHE_DEFAULT_EXPIRE", "300"))  # 5分钟
CACHE_PRICE_EXPIRE = int(os.getenv("CACHE_PRICE_EXPIRE", "300"))  # 5分钟
CACHE_PORTFOLIO_EXPIRE = int(os.getenv("CACHE_PORTFOLIO_EXPIRE", "600"))  # 10分钟
CACHE_SESSION_EXPIRE = int(os.getenv("CACHE_SESSION_EXPIRE", "1800"))  # 30分钟

# 应用配置
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production") 
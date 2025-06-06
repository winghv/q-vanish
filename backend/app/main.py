from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .database import engine, SessionLocal
from .routers import strategies, backtest, trading, ai_assistant, market_data, auth, users

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Q-Vanish API",
    description="量化交易平台API",
    version="0.1.0",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 包含路由器
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["策略"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["回测"])
app.include_router(trading.router, prefix="/api/trading", tags=["交易"])
app.include_router(market_data.router, prefix="/api/market-data", tags=["市场数据"])
app.include_router(ai_assistant.router, prefix="/api/ai-assistant", tags=["AI助手"])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/")
def root():
    return {"message": "欢迎使用Q-Vanish量化交易平台 API!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 
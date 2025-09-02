# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Q-Vanish is an AI-powered quantitative trading platform built for retail investors. It features a React frontend with a Python FastAPI backend, using SQLite for data persistence and integrating with various financial APIs and AI services.

## Architecture

- **Frontend**: React 18 with TypeScript, Vite, TailwindCSS, and Zustand for state management
- **Backend**: Python FastAPI with SQLAlchemy ORM, SQLite database
- **Communication**: REST API with axios client, JWT authentication
- **AI Integration**: OpenAI API integration for trading assistance via LangChain

The frontend runs on port 3000 and proxies API calls to the backend on port 8000. Authentication uses JWT tokens stored in localStorage with automatic token injection via axios interceptors.

## Development Commands

### Quick Start
```bash
npm run dev          # Start both frontend and backend concurrently
npm run setup        # Install all dependencies (root + frontend)
```

### Frontend Only
```bash
cd frontend
npm run dev          # Start Vite dev server on port 3000
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend Only
```bash
cd backend
uvicorn app.main:app --reload    # Start FastAPI server on port 8000
```

### Manual Setup
```bash
npm install                      # Install root dependencies
cd frontend && npm install       # Install frontend dependencies
cd ../backend && pip install -r requirements.txt  # Install backend dependencies
```

## Project Structure

```
q-vanish/
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/             # Route components
│   │   └── services/api.ts    # API client with types
│   ├── vite.config.ts         # Vite config with proxy setup
│   └── package.json
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Environment configuration
│   │   ├── database.py        # SQLAlchemy setup
│   │   ├── models.py          # Database models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── crud.py            # Database operations
│   │   ├── routers/           # API route handlers
│   │   └── utils/             # Utility functions and sample data
│   ├── requirements.txt
│   └── data/qvanish.db        # SQLite database file
└── package.json               # Root package with concurrently scripts
```

## Key Integration Points

### API Communication
- Frontend uses axios with base URL `http://localhost:8000/api`
- Vite proxy rewrites `/api` requests to backend
- JWT token automatically added via request interceptor
- 401 responses trigger automatic logout and redirect

**Current Status**: Frontend-backend integration is partially complete:
- Frontend calls are implemented with proper TypeScript interfaces
- Many backend endpoints are missing or have different paths than expected
- API routes like `/dashboard/*`, `/portfolio/*`, `/orders` return 404
- Backend trading logic exists at `/trading/*` but doesn't match frontend expectations

### Database
- SQLAlchemy with SQLite (`data/qvanish.db`)
- Models defined in `backend/app/models.py`
- Database initialized on app startup
- Session management via dependency injection

### Authentication Flow
- Login endpoint: `/api/auth/token` (form-encoded)
- Token stored in localStorage as `authToken`
- Protected routes use `ProtectedRoute` component
- Backend validates JWT tokens for protected endpoints

## Configuration

### Environment Variables
The backend uses python-dotenv to load configuration from environment variables:
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `SECRET_KEY`: JWT signing key (auto-generated if not set)
- `OPENAI_API_KEY`: Required for AI assistant functionality
- `DEBUG`: Enable debug mode
- `ENVIRONMENT`: Runtime environment

### Frontend Proxy Setup
Vite proxy configuration in `frontend/vite.config.ts` handles API routing:
- `/api/*` requests proxied to `http://localhost:8000`
- Path rewriting removes `/api` prefix
- Enables seamless local development

## API Structure

The backend follows a modular router structure:
- `/api/auth` - Authentication endpoints
- `/api/users` - User management
- `/api/strategies` - Trading strategy CRUD
- `/api/backtest` - Strategy backtesting
- `/api/trading` - Order management
- `/api/market-data` - Market data feeds  
- `/api/ai-assistant` - AI-powered trading assistance

All API types and functions are centralized in `frontend/src/services/api.ts` with TypeScript interfaces matching backend Pydantic schemas.

## 项目开发计划

### 📋 当前状态
- ✅ **阶段1完成**: 核心后端API实现 (100%)
- 🔄 **阶段2进行中**: 认证系统完善和市场数据集成
- ⏳ **后续阶段**: 待完成

### 🎯 完整开发路线图

#### **阶段1: 核心后端API实现** ✅ 已完成
**目标**: 建立完整的前后端通信基础
- ✅ 实现Dashboard、Portfolio、Orders、User API端点
- ✅ 完善数据库模型和CRUD操作
- ✅ 修复前后端API路径匹配问题
- ✅ 生成测试数据和数据库初始化
- ✅ 验证所有API端点正常工作

**成果**: 前端可显示真实数据，基础功能完全可用

#### **阶段2: 认证系统完善和市场数据集成** 🔄 进行中
**目标**: 提升系统安全性和数据真实性
- 🔄 完善JWT认证安全机制
- 🔄 集成Yahoo Finance等外部数据源
- 🔄 实现实时价格数据更新
- 🔄 建立市场数据缓存系统
- ⏳ 添加用户权限管理
- ⏳ 实现API请求频率限制

#### **阶段3: 交易系统完善** ⏳ 计划中
**目标**: 构建完整的交易引擎
- ⏳ 优化订单管理系统
- ⏳ 实现复杂订单类型（止损、止盈等）
- ⏳ 完善持仓计算和盈亏分析
- ⏳ 集成模拟交易broker接口
- ⏳ 实现风险控制系统
- ⏳ 添加交易日志和审计

#### **阶段4: 策略系统增强** ⏳ 计划中  
**目标**: 完善量化策略功能
- ⏳ 实现策略回测引擎
- ⏳ 添加技术指标计算库
- ⏳ 策略性能分析和可视化
- ⏳ 策略模板和策略市场
- ⏳ 实盘策略执行引擎
- ⏳ 策略风险评估

#### **阶段5: AI和机器学习集成** ⏳ 计划中
**目标**: 增强AI辅助交易功能
- ⏳ 优化OpenAI API集成
- ⏳ 实现智能投资建议
- ⏳ 市场情绪分析
- ⏳ 智能风险提醒
- ⏳ 个性化策略推荐
- ⏳ 自然语言交易查询

#### **阶段6: 用户体验和性能优化** ⏳ 计划中
**目标**: 提升系统性能和用户体验  
- ⏳ 前端性能优化和代码分割
- ⏳ 实时数据推送(WebSocket)
- ⏳ 移动端响应式优化
- ⏳ 国际化支持
- ⏳ 深色主题和个性化
- ⏳ 无障碍访问支持

#### **阶段7: 部署和运维** ⏳ 计划中
**目标**: 生产环境部署和监控
- ⏳ Docker容器化部署
- ⏳ 数据库迁移和备份策略
- ⏳ 负载均衡和高可用
- ⏳ 监控和日志系统
- ⏳ 安全审计和合规
- ⏳ 性能监控和告警

### 🏗️ 技术债务和优化点
- 错误处理标准化
- 代码测试覆盖率提升
- API文档完善
- 代码重构和优化
- 安全性加固

### 📈 项目进度跟踪
- **总体进度**: 约15% (阶段1完成)
- **预计开发周期**: 8-12周
- **当前重点**: 阶段2 - 认证和数据集成

### 🎯 近期目标 (接下来2周)
1. 完成市场数据集成
2. 实现实时价格更新
3. 加强认证系统安全性
4. 优化交易订单处理
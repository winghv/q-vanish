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
- `/api/dashboard` - Dashboard metrics and analytics
- `/api/portfolio` - Portfolio management
- `/api/orders` - Order execution and tracking
- `/api/advanced-orders` - Advanced order types (stop-loss, take-profit, bracket)
- `/api/analytics` - Position and portfolio analytics
- `/api/brokers` - Broker integration and management
- `/api/risk` - Risk management and assessment
- `/api/position-sizing` - Position sizing algorithms
- `/api/strategy-system` - Complete strategy system (backtest, live trading, templates, risk)

All API types and functions are centralized in `frontend/src/services/api.ts` with TypeScript interfaces matching backend Pydantic schemas.

## 项目开发计划

### 📋 当前状态
- ✅ **阶段1完成**: 核心后端API实现 (100%)
- ✅ **阶段2完成**: 认证系统完善和市场数据集成 (100%)
- ✅ **阶段3完成**: 交易系统完善 (100%)
- ✅ **阶段4完成**: 策略系统增强 (100%)
- ⏳ **后续阶段**: 阶段5-7待完成

### 🎯 完整开发路线图

#### **阶段1: 核心后端API实现** ✅ 已完成
**目标**: 建立完整的前后端通信基础
- ✅ 实现Dashboard、Portfolio、Orders、User API端点
- ✅ 完善数据库模型和CRUD操作
- ✅ 修复前后端API路径匹配问题
- ✅ 生成测试数据和数据库初始化
- ✅ 验证所有API端点正常工作

**成果**: 前端可显示真实数据，基础功能完全可用

#### **阶段2: 认证系统完善和市场数据集成** ✅ 已完成
**目标**: 提升系统安全性和数据真实性
- ✅ 完善JWT认证安全机制 (账户锁定、角色权限)
- ✅ 集成Yahoo Finance等外部数据源 (yfinance API完整集成)
- ✅ 实现实时价格数据更新 (MarketDataService)
- ✅ 建立市场数据缓存系统 (Redis + 内存缓存fallback)
- ✅ 添加用户权限管理 (admin/user角色控制)
- ✅ 实现API请求频率限制 (slowapi差异化限制)

#### **阶段3: 交易系统完善** ✅ 已完成
**目标**: 构建完整的交易引擎
- ✅ 优化订单管理系统
- ✅ 实现复杂订单类型（止损、止盈、括号订单等）
- ✅ 完善持仓计算和盈亏分析
- ✅ 集成模拟交易broker接口（Paper Trading Broker）
- ✅ 实现风险控制系统（投资组合级别风险管理）
- ✅ 添加交易日志和审计（完整的审计日志系统）
- ✅ 实现动态持仓大小算法（6种算法：固定金额/百分比、波动率目标、Kelly准则等）

**成果**: 完整的交易引擎，支持多种订单类型和风险管理

#### **阶段4: 策略系统增强** ✅ 已完成
**目标**: 完善量化策略功能
- ✅ 实现策略回测引擎（支持简单MA、RSI、MACD策略）
- ✅ 添加技术指标计算库（13个指标：SMA/EMA/RSI/MACD/Bollinger/Stochastic/ATR等）
- ✅ 策略性能分析和可视化（夏普比率、最大回撤、胜率等）
- ✅ 策略模板和策略市场（7个预定义策略模板）
- ✅ 实盘策略执行引擎（异步监控、自动交易）
- ✅ 策略风险评估（风险评分、VaR/CVaR、压力测试）

**成果**: 完整的量化策略系统，从回测到实盘全流程支持

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
- **总体进度**: 约60% (4/7阶段完成)
- **已完成阶段**: 1-4 (核心API、认证系统、交易系统、策略系统)
- **当前重点**: 阶段5 - AI和机器学习集成

### 🎯 近期目标 (接下来2周)
1. 优化OpenAI API集成
2. 实现智能投资建议功能
3. 市场情绪分析
4. 个性化策略推荐

### 📦 核心功能模块
#### 已实现模块
- ✅ **认证与授权**: JWT认证、角色权限、账户锁定
- ✅ **市场数据**: Yahoo Finance集成、实时行情、数据缓存（Redis）
- ✅ **订单系统**: 多种订单类型、括号订单、订单监控
- ✅ **风险管理**: 投资组合级风险控制、动态持仓sizing
- ✅ **策略系统**: 回测引擎、技术指标、实盘执行、风险评估
- ✅ **券商集成**: Paper Trading Broker、抽象broker接口
- ✅ **分析工具**: 持仓分析、绩效指标、压力测试

#### 待实现模块
- ⏳ **AI助手增强**: 智能建议、情绪分析、策略推荐
- ⏳ **实时推送**: WebSocket、实时通知
- ⏳ **部署运维**: Docker、监控、日志系统

## 策略系统详解 (阶段4实现)

### 核心服务模块

#### 1. BacktestEngine (`backtest_engine.py`)
策略回测引擎，支持历史数据模拟和绩效评估
- **历史数据加载**: 从MarketDataService获取历史价格数据
- **信号生成**: 支持简单MA、RSI、MACD三种策略类型
- **交易模拟**: 考虑佣金和滑点的交易执行
- **绩效计算**: 总回报、年化回报、夏普比率、最大回撤、胜率等

#### 2. TechnicalIndicators (`technical_indicators.py`)
技术指标计算库，提供13个常用指标
- **趋势指标**: SMA, EMA, MACD, ADX, Ichimoku Cloud
- **震荡指标**: RSI, Stochastic, CCI, Williams %R
- **波动性指标**: Bollinger Bands, ATR
- **成交量指标**: OBV, VWAP
- **支撑阻力**: Pivot Points

#### 3. StrategyPerformanceAnalyzer (`strategy_performance.py`)
策略性能分析工具
- **回测分析**: 详细的绩效报告
- **策略对比**: 多策略性能排名
- **组合分析**: 投资组合绩效评估
- **风险指标**: Sharpe、Sortino、Calmar比率

#### 4. StrategyTemplates (`strategy_templates.py`)
预定义策略模板库（7个模板）
- 简单移动平均线交叉策略
- 指数移动平均线策略
- RSI超买超卖反转策略
- MACD动量策略
- 布林带突破策略
- 动量轮动策略
- RSI+布林带双重确认策略

#### 5. LiveStrategyEngine (`live_strategy_engine.py`)
实盘策略执行引擎
- **实时监控**: 异步市场数据监控
- **信号生成**: 实时交易信号
- **自动交易**: 集成OrderEngine自动下单
- **持仓跟踪**: 实时持仓管理

#### 6. StrategyRiskAssessor (`strategy_risk_assessment.py`)
策略风险评估工具
- **风险评分**: 0-100分风险评分系统
- **风险等级**: LOW/MEDIUM/HIGH分类
- **仓位建议**: 基于风险的最大仓位计算
- **压力测试**: 模拟极端市场情况
- **VaR/CVaR**: 风险价值计算

### API端点

所有策略系统API通过 `/api/strategy-system` 前缀访问：

```
POST   /backtest/run                    # 运行策略回测
GET    /backtest/{id}/analysis          # 获取回测分析
POST   /performance/compare             # 比较多个策略
POST   /performance/portfolio           # 组合绩效分析
GET    /templates                       # 获取所有策略模板
GET    /templates/{id}                  # 获取特定模板
POST   /live/start                      # 启动实盘策略
POST   /live/stop/{id}                  # 停止实盘策略
GET    /live/running                    # 获取运行中的策略
GET    /live/status/{id}                # 获取策略状态
GET    /risk/assess/{id}                # 策略风险评估
POST   /risk/compare                    # 风险对比
GET    /risk/stress-test/{id}           # 压力测试
GET    /report/comprehensive/{id}       # 综合报告
```

### 使用示例

#### 运行回测
```python
# 请求
POST /api/strategy-system/backtest/run
{
  "strategy_id": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000,
  "commission_rate": 0.001,
  "slippage_rate": 0.0005
}

# 响应
{
  "backtest_id": 123,
  "performance": {
    "total_return": 15.6,
    "sharpe_ratio": 1.8,
    "max_drawdown": 12.3,
    "win_rate": 58.5
  },
  "trades": [...],
  "equity_curve": [...]
}
```

#### 获取策略模板
```python
GET /api/strategy-system/templates
# 返回所有7个预定义策略模板，包含参数说明、风险等级、适用场景等
```

#### 启动实盘策略
```python
POST /api/strategy-system/live/start
{
  "strategy_id": 1,
  "portfolio_id": 1
}
# 启动后策略将自动监控市场并执行交易
```
# Q-Vanish 量化交易平台

一个为散户投资者打造的AI驱动量化交易平台，提供简单易用的界面和强大的交易策略支持。

## 功能特点

- 直观的交易界面
- AI辅助交易决策
- 量化策略开发与回测
- 实时市场数据分析
- 个性化风险控制
- 历史交易记录和绩效分析

## 技术栈

- 前端：React, TailwindCSS
- 后端：Python FastAPI
- 数据库：SQLite
- AI：接入大语言模型辅助交易决策

## 快速开始

### 环境要求

- Node.js >= 16.0.0
- Python >= 3.8.0
- pip

### 安装步骤

1. 克隆项目
```
git clone https://github.com/yourusername/q-vanish.git
cd q-vanish
```

2. 安装前端依赖
```
cd frontend
npm install
cd ..
```

3. 安装后端依赖
```
cd backend
pip install -r requirements.txt
cd ..
```

4. 启动项目
```
npm run dev
```

前端将在 http://localhost:3000 运行
后端API将在 http://localhost:8000 运行

## 项目结构

```
q-vanish/
├── frontend/          # React前端
├── backend/           # Python FastAPI后端
│   ├── app/           # API接口
│   ├── models/        # 数据模型
│   ├── services/      # 业务逻辑
│   └── utils/         # 工具函数
└── data/              # 本地数据存储
```

## 贡献指南

欢迎提交问题和贡献代码！

## 许可证

[MIT License](LICENSE) 
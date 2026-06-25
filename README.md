# BubbleRadar / 泡沫雷达

AI 泡沫与中国经济风险实时监控系统。

## 技术栈

- **前端**：React 18 + TypeScript + Vite + Tailwind CSS + ECharts + Zustand
- **后端**：FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL + Redis
- **采集**：Yahoo Finance + 可扩展 FRED / 政府数据源适配器 + APScheduler 定时调度
- **部署**：Docker + Docker Compose + Nginx

## 快速启动（Docker Compose）

确保已安装 Docker 与 Docker Compose，然后在项目根目录执行：

```bash
docker compose up -d --build
```

服务说明：

| 服务 | 地址 | 说明 |
|------|------|------|
| Nginx（前端 + API 代理） | http://localhost | 主入口 |
| FastAPI 后端 | http://localhost/api/docs | API 文档 |
| PostgreSQL | localhost:5432 | 数据库 |
| Redis | localhost:6379 | 缓存 |

导入演示数据：

```bash
docker compose exec backend python scripts/seed.py
```

手动触发一次数据采集：

```bash
curl -X POST http://localhost/api/v1/crawler/run
```

默认每 30 分钟会自动执行一次采集、评分重算与预警检查。

## 本地开发

### 1. 环境变量

复制示例配置：

```bash
cp .env.example .env
```

启动 PostgreSQL 与 Redis（可用 Docker）：

```bash
docker run -d --name br-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=bubbleradar -p 5432:5432 postgres:15-alpine
docker run -d --name br-redis -p 6379:6379 redis:7-alpine
```

### 2. 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173。

## 项目结构

```
.
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/       # REST API
│   │   ├── core/         # 配置、缓存、安全
│   │   ├── crawler/      # 数据采集器与调度器
│   │   ├── db/           # 数据库连接
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── schemas/      # Pydantic 模式
│   │   └── services/     # 业务逻辑（评分、预警）
│   ├── scripts/          # seed、工具脚本
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React 前端
│   ├── src/
│   │   ├── components/   # 图表、卡片、布局
│   │   ├── pages/        # 页面
│   │   ├── services/     # API 封装
│   │   └── store/        # Zustand 状态
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

## 数据采集说明

采集模块位于 `backend/app/crawler/`，当前实现：

- **Yahoo Finance**：获取 SOXX / NASDAQ / NVDA / 上证综指 / USD/CNY 等市场数据，映射为 AI 板块 PE 溢价、AI 情绪指数、算力闲置压力、资本市场风险、外汇风险等指标。
- **Fallback 兜底**：外部接口不可达时，基于历史快照生成小幅波动值，保证仪表盘始终有数据。
- **FRED 适配器**：已预留，配置 `FRED_API_KEY` 后可扩展美国经济数据。

API 入口：

- `POST /api/v1/crawler/run` 手动触发采集
- `GET  /api/docs` 查看全部接口

## 注意事项

- 生产环境请修改 `SECRET_KEY`、数据库密码，并使用 Alembic 管理迁移。
- 首次运行前建议执行 `seed.py` 写入指标定义与历史快照。
- 容器启动后会自动建表；定时采集任务在应用启动后自动启动。

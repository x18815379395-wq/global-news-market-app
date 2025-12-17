# HorizonScanner - 全球市场智能感知系统（原名“顺风耳系统”）

<p align="center">
  <img src="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 80'><rect width='320' height='80' rx='12' fill='%230f172a'/><text x='160' y='48' font-family='Arial' font-size='22' fill='%230ea5e9' text-anchor='middle'>HorizonScanner · 全球市场智能感知</text></svg>" alt="HorizonScanner Logo">
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/%E7%89%88%E6%9C%AC-3.0-blue" alt="Version"></a>
  <a href="#"><img src="https://img.shields.io/badge/%E7%8A%B6%E6%80%81-%E7%94%9F%E4%BA%A7%E5%B7%B2%E5%95%86%E7%94%A8-brightgreen" alt="Status"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/License-MIT-green" alt="License"></a>
</p>

## ✨ 系统简介
HorizonScanner（地平线扫描者）V3.0 是一个面向全球投资者的实时市场情报与策略辅助系统。项目从“顺风耳系统”演化而来，早期聚焦 A 股信息差套利，如今已覆盖美国、欧洲、日本、中国、印度、澳大利亚及主要衍生品市场，能够在分钟级链路上完成数据抓取、语义过滤、多模型交叉验证与策略生成，为投研和量化团队提供可执行的信号。

> **品牌升级**：从“顺风耳系统”到“HorizonScanner”，象征产品从单市场套利脚本成长为全球化情报枢纽。

## 📊 核心能力

### 🌍 全球市场覆盖：6 个主要市场 + 衍生品
- **主要市场**：USA / Europe / Japan / China / India / Australia，涵盖股指、行业 ETF 与 ADR。
- **衍生品支持**：期权、期货、CFD、外汇对与大宗商品价格联动场景。
- **跨市场特征库**：自动同步宏观日程、突发新闻、监管事件等外生变量，供策略引擎调用。

### 🔗 数据获取与处理
- **多源抓取**：Firecrawl、NewsAPI、WSJ、Bloomberg、FT、CNBC、CNN 等权威媒体 + 自建 RSS + X(Twitter)/Reddit 舆情监听。
- **语义过滤**：`utils/keywords.py` 按市场与资产类别维护关键词集并通过 Embedding 去噪。
- **事实校验**：Tavily API 与本地缓存交叉验证，自动剔除谣言或重复事件。
- **多模型共识**：DeepSeek、Claude、GPT、Qwen 等 LLM 投票，降低单模型偏差。

### ⚙️ 底层引擎
- **信号生成**：模式识别 + 主题聚类 + 事件置信度加权输出看涨/看跌/观望信号。
- **T+3 指引**：默认生成 T+3 决策参考，可按市场自定义持仓天数与止盈/止损。
- **资产映射**：地缘事件自动映射到可交易标的（ETF、期货、行业龙头等）。
- **行业影响识别**：评估供应链暴露度、上下游弹性、上市公司名单。

### 🖥️ 全新 UI 体验（HorizonScanner UI）
- **视觉语言**：深色金融主题 + 玻璃拟态卡片，突出关键信号。
- **多维面板**：全球热力图、信号强弱、事件时间轴、执行建议一屏呈现。
- **交互特性**：分屏对比、过滤器、手势/移动适配。
- **部署方式**：`HorizonScanner/frontend` (React + Vite) 单独打包，亦可嵌入任意仪表盘。

### 🔐 安全与合规
- `.env` 统一管理 Firecrawl、NewsAPI、DeepSeek、Tavily 等密钥，通过 `utils/security.py` 加密缓存。
- API Key 仅加载进程内存，日志脱敏，敏感参数可按租户分离。
- 采集/输出均附时间戳与哈希签名，便于审计。

### 📡 数据更新
- 核心新闻源 60s 轮询，舆情流 15s 刷新，宏观日历 30min 刷新。
- `news/pipeline.py` 使用 `ThreadPoolExecutor` + 自适应退避，在高负载场景仍保持稳定。
- `logs/` 下提供流水与异常追踪，可接入 ELK / Loki。

## ⚡ 快速开始（5 分钟上手）

### 系统要求
- Windows / macOS / Linux，建议 4C16G 以上。
- Python 3.10+、Node.js 18+、Git、Redis（可选，用于缓存）。

### 重要提示
- 推荐使用 `python -m venv venv && source venv/bin/activate`（Windows `venv\Scripts\activate`）。
- 首次启动前确认 `.env` 已配置完毕，默认不会提交到版本库。

### 1. 克隆仓库
```bash
git clone https://github.com/example/global-news-market-app.git
cd global-news-market-app
```

### 2. 安装后端依赖
```bash
pip install -r requirements-secure.txt
```
如需 GPU/LLM 本地推理，可在 `venv` 中另行安装相应包。

### 3. 安装前端依赖（可选：HorizonScanner UI）
```bash
cd HorizonScanner/frontend
npm install
```
构建产物位于 `HorizonScanner/frontend/dist`，可反向代理到主域名。

### 4. 快速检查数据抓取
```bash
python news_sources.py --dry-run
python test_news_sources.py
```
用于检测 `news_sources.yaml`、网络连通与限频配置是否正确。

### 5. 配置 `.env`
核心变量：
- `NEWSAPI_API_KEY`
- `FIRECRAWL_API_KEY`
- `DEEPSEEK_API_KEY`
- `TAVILY_API_KEY`
- `OPENAI_API_KEY`（如使用 GPT）
- `REDIS_URL`（可选）
- `LOG_LEVEL`, `PORT`, `UI_BASE_URL` 等运行参数。

### 6. 启动后端（默认 http://localhost:5000）
```bash
python ears_of_fortune_v2.py
# 或
python start_app.py --port 5000
```
控制台将输出爬虫、信号和 API 载入状态。

### 7. 启动前端（可选）
```bash
cd HorizonScanner/frontend
npm start
```
访问 `http://localhost:3000`，前端将通过代理访问 `http://localhost:5000/api/*`。

## 🧭 架构概览
```text
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌──────────────┐   ┌────────────┐
│ 官方媒体源 │→│ news/抓取层 │→│ utils/清洗 │→│ 策略 & 信号层 │→│ REST API 层 │
├────────────┤   ├────────────┤   ├────────────┤   ├──────────────┤   └────┬───────┘
│ 社交舆情   │  │ crawler/    │  │ embeddings │  │ risk engine  │        │
│ 宏观日历   │  │ tavily 校验 │  │ security   │  │ mapping      │        ↓
└────────────┘   └────────────┘   └────────────┘   └──────────────┘   React 前端
```

## 🧱 模块说明
| 路径 | 说明 |
| --- | --- |
| `news/` | 新闻抓取、解析与落地逻辑，含 `news_sources.py`、`pipeline.py` 等。 |
| `crawler/` | 无 API 抓取脚本、反爬策略与缓存。 |
| `utils/` | 关键词、打分、加密、安全、共用工具。 |
| `HorizonScanner/frontend/` | React UI，含组件、hooks、视图与样式。 |
| `templates/` + `static/` | Flask/Jinja 服务端渲染与静态资源。 |
| `hooks/`, `pages/`, `views/` | 后端业务视图、路由、调度器。 |
| `logs/` | 运行日志与诊断文件。 |

## 🔌 API 接口概览
| 方法 | 路径 | 功能 |
| --- | --- | --- |
| `GET` | `/api/connectivity-test` | 自检抓取/LLM/缓存等依赖。 |
| `GET` | `/api/news-secure` | 返回清洗后的新闻 feed（支持分页与来源过滤）。 |
| `GET` | `/api/trading-signals` | 返回当前信号及置信度、建议持仓周期。 |
| `GET` | `/api/data` | 聚合市场指标与情绪得分。 |
| `GET` | `/health` | 供探针使用的健康检查。 |

## 🧪 质量要求
- 使用 `pytest` 运行 `test_news_sources.py` 与后端单元测试。
- 关键脚本（爬虫、信号引擎）需添加 `--dry-run` 与 `--limit` 选项，便于 CI 运行。
- 日志与告警应覆盖抓取失败、模型超时、策略回溯异常等场景。

## 🛡️ 稳定性与监控
- `logs/` 默认生成 rolling file，可挂接 Loki/ELK。
- 通过 `/health` 返回依赖状态、延迟与最近一次信号时间戳。
- 建议在生产环境配套 Prometheus + Alertmanager / Grafana OnCall。

## 🔄 部署策略
1. 构建前端：`npm run build`，将 `dist/` 上传到 CDN 或 OSS。
2. 后端使用 `gunicorn`/`uvicorn` + `nginx`，或打包成 Docker：
   ```bash
   docker build -t horizonscanner:3.0 .
   docker run --env-file .env -p 5000:5000 horizonscanner:3.0
   ```
3. 通过 `supervisor`/`systemd` 维持爬虫与 API 常驻。

## 🚀 未来规划（V3.1+）
- 策略插件市场：允许自定义回测与执行模块。
- 全量多语种 UI（EN/JA/ES），强化本地化资讯。
- 事件回溯 & 可视化回放，方便投研复盘。
- 引入 AutoGen/Agentic 流程，实现更高阶的任务拆解与执行。

## 🙋 支持
- 通过 Issues/Discussions 反馈需求或 Bug。
- 发送邮件至 `support@horizonscanner.ai` 获取企业支持与私有化部署方案。

## 📄 版权
本项目以 MIT License 开源，若在商业环境部署，请遵守目标市场的数据使用条例与合规要求。
# global-news-market-app


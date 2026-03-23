# Balance Monitor

API 余额监控脚本，定期查询各服务的剩余额度并通过 Telegram 机器人推送日报。

## 支持的服务

- **OpenRouter** - AI 模型 API 调用额度
- **DeepSeek** - AI 模型 API 调用额度
- **Tavily** - 搜索 API credits（每月免费 1000 credits）

## 环境配置

创建 `.env` 文件：

```env
# Telegram 配置
TG_BOT_TOKEN="your-telegram-bot-token"
TG_CHAT_ID="your-chat-id"

# API Keys
OPENROUTER_API_KEY="your-openrouter-api-key"
DEEPSEEK_API_KEY="your-deepseek-api-key"
TAVILY_API_KEY="your-tavily-api-key"
```

## 运行

```bash
python main.py
```

## 数据库

余额历史记录存储在 `balance.db`（SQLite），包含每次查询的时间、服务、余额和消耗量。

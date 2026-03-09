# main.py
import os
import requests
import sys
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 获取配置
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

def send_tg_msg(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("❌ 缺少 Telegram 配置")
        return

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"发送失败: {e}")


def check_openrouter():
    url = "https://openrouter.ai/api/v1/credits"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://github.com/your-username/balance-monitor",
        "X-Title": "Balance Monitor"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", {})

            # 获取历史总充/送金额
            total_purchased = float(data.get("total_credits", 0))
            # 获取历史总消耗金额
            total_used = float(data.get("total_usage", 0))

            # 手动计算剩余余额
            remaining_balance = total_purchased - total_used

            return (
                f"🟢 *OpenRouter*\n"
                f"当前余额: `${remaining_balance:.4f}`\n"
                f"------------------\n"
                f"总充值: `${total_purchased:.2f}`\n"
                f"总消耗: `${total_used:.2f}`"
            )
        else:
            return f"❌ OpenRouter 错误: {resp.status_code}"
    except Exception as e:
        return f"❌ OpenRouter 异常: {str(e)}"

def check_deepseek():
    # ... (保持 DeepSeek 代码不变) ...
    if not DEEPSEEK_KEY:
        return "⚠️ DeepSeek Key 未配置"

    url = "https://api.deepseek.com/user/balance"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Accept": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()

        if resp.status_code == 200 and data.get("is_available") is not None:
             # DeepSeek 余额包含多种货币 (CNY/USD)
             balance_infos = data.get("balance_infos", [])
             details = []
             for info in balance_infos:
                 currency = info.get("currency", "CNY")
                 amount = info.get("total_balance", 0)
                 details.append(f"`{amount} {currency}`")

             balance_str = " | ".join(details)
             return f"🔵 *DeepSeek*\n余额: {balance_str}"
        else:
             return f"❌ DeepSeek 查询失败: {resp.status_code}"

    except Exception as e:
        return f"❌ DeepSeek 异常: {str(e)}"

def main():
    print("正在查询 API...")
    msg_or = check_openrouter()
    msg_ds = check_deepseek()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"📅 *API 余额日报* ({now})\n\n{msg_or}\n\n{msg_ds}"

    print(report)
    send_tg_msg(report)

if __name__ == "__main__":
    main()

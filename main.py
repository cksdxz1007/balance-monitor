# main.py
import os
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 获取配置
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")
SILICONFLOW_KEY = os.getenv("SILICONFLOW_API_KEY")

DB_PATH = os.path.join(os.path.dirname(__file__), "balance.db")


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            service TEXT NOT NULL,
            balance REAL NOT NULL,
            total_used REAL DEFAULT 0,
            currency TEXT DEFAULT 'CNY'
        )
    """)
    conn.commit()
    conn.close()


def save_balance(service, balance, total_used=0, currency="CNY"):
    """保存余额记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO balance_log (timestamp, service, balance, total_used, currency) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), service, balance, total_used, currency)
    )
    conn.commit()
    conn.close()


def get_last_balance(service):
    """获取上一次的余额记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT balance, total_used FROM balance_log WHERE service = ? ORDER BY id DESC LIMIT 1",
        (service,)
    )
    result = cursor.fetchone()
    conn.close()
    return result  # (balance, total_used) or None


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
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", {})

            total_purchased = float(data.get("total_credits", 0))
            total_used = float(data.get("total_usage", 0))
            remaining_balance = total_purchased - total_used

            # 先获取上次记录（计算差额后再保存）
            last = get_last_balance("openrouter")
            if last:
                prev_total_used = last[1]
                delta = total_used - prev_total_used
                if delta > 0:
                    usage_delta = f"\n📉 本次消耗: `-${delta:.4f}`"
                else:
                    usage_delta = f"\n📉 本次消耗: `$0.0000`"
            else:
                usage_delta = ""

            # 保存到数据库
            save_balance("openrouter", remaining_balance, total_used, "USD")

            return (
                f"🟢 *OpenRouter*\n"
                f"当前余额: `${remaining_balance:.4f}`\n"
                f"------------------\n"
                f"总充值: `${total_purchased:.2f}`\n"
                f"总消耗: `${total_used:.2f}`{usage_delta}"
            )
        else:
            return f"❌ OpenRouter 错误: {resp.status_code}"
    except Exception as e:
        return f"❌ OpenRouter 异常: {str(e)}"


def check_deepseek():
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
            balance_infos = data.get("balance_infos", [])
            details = []
            for info in balance_infos:
                currency = info.get("currency", "CNY")
                amount = float(info.get("total_balance", 0))

                # 先获取上次记录（计算差额后再保存）
                last = get_last_balance("deepseek")
                if last and last[0] is not None:
                    prev_balance = last[0]
                    delta = prev_balance - amount
                    if delta > 0:
                        usage_delta = f"\n📉 本次消耗: `-{delta:.2f} {currency}`"
                    else:
                        usage_delta = f"\n📉 本次消耗: `0.00 {currency}`"
                else:
                    usage_delta = ""

                # 保存到数据库
                save_balance("deepseek", amount, 0, currency)

                details.append(f"`{amount:.2f} {currency}`{usage_delta}")

            balance_str = " | ".join(details)
            return f"🔵 *DeepSeek*\n余额: {balance_str}"
        else:
            return f"❌ DeepSeek 查询失败: {resp.status_code}"

    except Exception as e:
        return f"❌ DeepSeek 异常: {str(e)}"


def check_tavily():
    if not TAVILY_KEY:
        return "⚠️ Tavily Key 未配置"

    url = "https://api.tavily.com/usage"
    headers = {
        "Authorization": f"Bearer {TAVILY_KEY}"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()

            # API key 级别用量
            key_data = data.get("key", {})
            key_usage = key_data.get("usage", 0)
            key_limit = key_data.get("limit")
            key_remaining = key_limit - key_usage if key_limit else None

            # 账户级别用量
            account_data = data.get("account", {})
            plan_name = account_data.get("current_plan", "未知")
            plan_usage = account_data.get("plan_usage", 0)
            plan_limit = account_data.get("plan_limit", 0)
            plan_remaining = plan_limit - plan_usage if plan_limit else None

            # 先获取上次记录（计算差额后再保存）
            last = get_last_balance("tavily")
            if last and last[1] is not None:
                prev_usage = last[1]
                delta = key_usage - prev_usage
                if delta > 0:
                    usage_delta = f"\n📉 本次消耗: `-{delta}` credits"
                else:
                    usage_delta = f"\n📉 本次消耗: `0` credits"
            else:
                usage_delta = ""

            # 保存到数据库（无限额度时保存 -1）
            save_balance("tavily", key_remaining if key_remaining is not None else -1, key_usage, "credits")

            if key_limit:
                return (
                    f"🟡 *Tavily*\n"
                    f"当前计划: `{plan_name}`\n"
                    f"------------------\n"
                    f"Key 剩余: `{key_remaining}` / `{key_limit}`\n"
                    f"计划剩余: `{plan_remaining}` / `{plan_limit}`{usage_delta}"
                )
            else:
                return (
                    f"🟡 *Tavily*\n"
                    f"当前计划: `{plan_name}`\n"
                    f"------------------\n"
                    f"Key 剩余: `无限`\n"
                    f"计划剩余: `{plan_remaining}` / `{plan_limit}`{usage_delta}"
                )
        else:
            return f"❌ Tavily 错误: {resp.status_code}"
    except Exception as e:
        return f"❌ Tavily 异常: {str(e)}"


def check_siliconflow():
    if not SILICONFLOW_KEY:
        return "⚠️ SiliconFlow Key 未配置"

    url = "https://api.siliconflow.cn/v1/user/info"
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_KEY}"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") is True:
                info = data.get("data", {})
                balance = float(info.get("balance", 0))
                charge_balance = float(info.get("chargeBalance", 0))
                total_balance = float(info.get("totalBalance", 0))

                # 先获取上次记录（计算差额后再保存）
                last = get_last_balance("siliconflow")
                if last and last[0] is not None:
                    prev_balance = last[0]
                    delta = prev_balance - charge_balance
                    if delta > 0:
                        usage_delta = f"\n📉 本次消耗: `-{delta:.2f}`"
                    else:
                        usage_delta = f"\n📉 本次消耗: `0.00`"
                else:
                    usage_delta = ""

                # 保存到数据库
                save_balance("siliconflow", charge_balance, 0, "CNY")

                return (
                    f"🟣 *SiliconFlow*\n"
                    f"余额: `{charge_balance:.2f}`\n"
                    f"------------------\n"
                    f"赠送余额: `{balance:.2f}`\n"
                    f"总余额: `{total_balance:.2f}`{usage_delta}"
                )
            else:
                return f"❌ SiliconFlow 查询失败"
        else:
            return f"❌ SiliconFlow 错误: {resp.status_code}"
    except Exception as e:
        return f"❌ SiliconFlow 异常: {str(e)}"


def main():
    print("正在查询 API...")
    init_db()

    msg_or = check_openrouter()
    msg_ds = check_deepseek()
    msg_tavily = check_tavily()
    msg_sf = check_siliconflow()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"📅 *API 余额日报* ({now})\n\n{msg_or}\n\n{msg_ds}\n\n{msg_tavily}\n\n{msg_sf}"

    print(report)
    send_tg_msg(report)


if __name__ == "__main__":
    main()

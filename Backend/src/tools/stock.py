from langchain_core.tools import tool
import logging
import akshare as ak
import pandas as pd
import re
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_trading_calendar() -> set:
    """
    从 AkShare 动态拉取完整的 A 股交易日历（新浪数据源）。
    使用 lru_cache 缓存结果，整个进程生命周期内只请求一次，避免重复网络开销。
    返回: YYYYMMDD 格式字符串的 set 集合
    """
    try:
        logger.info("Fetching A-share trading calendar from AkShare...")
        df = ak.tool_trade_date_hist_sina()
        # 返回的列名为 'trade_date'，格式为 date 对象
        trading_days = set(pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d").tolist())
        logger.info(f"Trading calendar loaded: {len(trading_days)} trading days found.")
        return trading_days
    except Exception as e:
        logger.error(f"Failed to fetch trading calendar: {e}", exc_info=True)
        return set()


def _is_trading_day(date_str: str) -> bool:
    """
    判断指定的 YYYYMMDD 日期是否是 A 股交易日。
    """
    calendar = _get_trading_calendar()
    if not calendar:
        # 若获取日历失败，退回到仅判断周末的简单策略
        dt = datetime.strptime(date_str, "%Y%m%d")
        return dt.weekday() < 5
    return date_str in calendar


def _find_previous_trading_day(date_str: str) -> tuple:
    """
    从指定日期往前找，返回最近一个 A 股交易日 (日期字符串, 回退的天数)
    """
    dt = datetime.strptime(date_str, "%Y%m%d")
    for i in range(1, 30):
        dt -= timedelta(days=1)
        candidate = dt.strftime("%Y%m%d")
        if _is_trading_day(candidate):
            return candidate, i
    return None, -1


# 中文星期 -> Python weekday() 映射
_WEEKDAY_MAP = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "天": 6, "日": 6}


def _parse_date_query(query: str) -> str:
    """
    将用户自然语言日期（含冗余文字的完整句子）转换成 YYYYMMDD 格式字符串。
    支持:
      - 相对日期: 今天/今日, 昨天/昨日, 前天, 大前天, 明天/明日, 后天
      - 上周 X:   上周一~上周日
      - 上上周 X: 上上周一~上上周日
      - 本周 X:   本周一~本周日
      - N 天前/后: 3天前、5天后
      - 中文月日: 3月15日、3月15号
      - 标准格式: 20231010、2023-10-10、2023/10/10
    """
    today = datetime.today()

    # 1. 相对天数关键字（优先匹配）
    relative_map = [
        (["今天", "今日"], 0),
        (["明天", "明日"], 1),
        (["后天"], 2),
        (["大前天"], -3),
        (["前天"], -2),
        (["昨天", "昨日"], -1),
    ]
    for keywords, delta in relative_map:
        if any(k in query for k in keywords):
            return (today + timedelta(days=delta)).strftime("%Y%m%d")

    # 2. 上上周 X
    m = re.search(r"上上周([一二三四五六天日])", query)
    if m:
        target_wd = _WEEKDAY_MAP[m.group(1)]
        last2_monday = today - timedelta(days=today.weekday() + 14)
        return (last2_monday + timedelta(days=target_wd)).strftime("%Y%m%d")

    # 3. 上周 X
    m = re.search(r"上周([一二三四五六天日])", query)
    if m:
        target_wd = _WEEKDAY_MAP[m.group(1)]
        last_monday = today - timedelta(days=today.weekday() + 7)
        return (last_monday + timedelta(days=target_wd)).strftime("%Y%m%d")

    # 4. 本周 X
    m = re.search(r"本周([一二三四五六天日])", query)
    if m:
        target_wd = _WEEKDAY_MAP[m.group(1)]
        this_monday = today - timedelta(days=today.weekday())
        return (this_monday + timedelta(days=target_wd)).strftime("%Y%m%d")

    # 5. N 天前 / N 天后
    m = re.search(r"(\d+)\s*天\s*(前|后)", query)
    if m:
        n = int(m.group(1))
        direction = -1 if m.group(2) == "前" else 1
        return (today + timedelta(days=n * direction)).strftime("%Y%m%d")

    # 6. X月X日 / X月X号
    m = re.search(r"(\d{1,2})[月/](\d{1,2})[日号]?", query)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            return datetime(today.year, month, day).strftime("%Y%m%d")
        except ValueError:
            pass

    # 7. 标准数字格式（从句子中提取）
    m = re.search(r"(\d{4})([-/.]?)(\d{2})\2(\d{2})", query)
    if m:
        return f"{m.group(1)}{m.group(3)}{m.group(4)}"

    return None


@tool
def get_stock(query: str) -> str:
    """
    查询某天 A 股的涨停板股票数据。支持自然语言日期，如 "今天"、"昨天"、"前天"、"上周五"，或日期字符串 "20231010"、"2023-10-10"。
    如果指定日期是非交易日（节假日或周末），会自动回退到最近的上一个交易日并给出提醒。
    """
    try:
        logger.info(f"Tool 'get_stock' called with input: {query}")

        # 1. 解析用户输入的日期
        date_str = _parse_date_query(query)
        if not date_str:
            return (
                f"无法识别日期：'{query}'。\n"
                "请用自然语言描述（如 '今天'、'昨天'、'上周五'）或日期字符串（如 '20231010'）来查询。"
            )

        hint = ""

        # 2. 动态校验是否是交易日，若不是则自动回退
        if not _is_trading_day(date_str):
            target_dt = datetime.strptime(date_str, "%Y%m%d")
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            weekday_name = weekday_names[target_dt.weekday()]
            date_display = target_dt.strftime("%Y年%m月%d日")

            reason = f"周末（{weekday_name}）" if target_dt.weekday() >= 5 else "非交易日（法定节假日或休市）"

            prev_date, skipped = _find_previous_trading_day(date_str)
            if not prev_date:
                return f"{date_display} 是{reason}，且无法找到最近的历史交易日，请稍后重试。"

            prev_dt = datetime.strptime(prev_date, "%Y%m%d")
            prev_display = prev_dt.strftime("%Y年%m月%d日")
            hint = f"⚠️  {date_display} 是{reason}，A 股当日休市。\n✅ 已自动为您查询最近的上一交易日（{prev_display}）的行情：\n\n"
            date_str = prev_date
            logger.info(f"Date {date_str} is not a trading day, falling back to: {prev_date}")

        # 3. 拉取涨停板数据
        logger.info(f"Fetching limit-up pool for: {date_str}")
        df = ak.stock_zt_pool_em(date=date_str)

        if df is None or df.empty:
            display_date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y年%m月%d日")
            return f"{hint}⚠️ {display_date} 暂无涨停板数据（可能数据尚未生成，请盘后再试）。"

        # 4. 全量输出所有涨停股
        display_date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y年%m月%d日")
        total = len(df)
        result = f"{hint}📈 {display_date} 共有 {total} 支股票涨停，完整名单如下：\n"
        result += "-" * 55 + "\n"

        for idx, row in df.iterrows():
            num = idx + 1
            name = row.get("名称", "未知")
            code = row.get("代码", "未知")
            pct = row.get("涨跌幅", "未知")
            price = row.get("最新价", "未知")
            boards = row.get("连板数", 1)
            result += f"[{num:>3}] {name}（{code}）| 涨幅: {pct}% | 价格: {price}元 | 连板: {boards}板\n"

        result += "-" * 55 + "\n"
        result += f"✅ 合计 {total} 只涨停股 | 数据来源：东方财富"
        return result

    except Exception as e:
        logger.error(f"Error in 'get_stock' tool: {str(e)}", exc_info=True)
        return f"查询涨停板数据时遇到问题：{str(e)}"
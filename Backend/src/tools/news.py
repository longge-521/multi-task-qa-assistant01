from langchain_core.tools import tool
import logging
import time
from ddgs import DDGS

logger = logging.getLogger(__name__)

@tool
def search_news(query: str) -> str:
    """
    根据关键词搜索最新的新闻资讯。
    当用户询问新闻、时事、头条或任何近期发生的事件时，使用此工具。
    具备深度搜索机制，若专门的 NEWS 渠道受限会自动切换到全网实时搜索模式。
    """
    max_retries = 2
    wait_seconds = 1
    
    # 清理一下 query，移除一些大模型可能会加的冗余关键词
    clean_query = query.replace("Top10", "").replace("热门新闻", "").replace("最新资讯", "").strip() or query

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Tool 'search_news' called with: {clean_query} (attempt {attempt})")
            
            with DDGS() as ddgs:
                # 策略 1: 尝试专门的新闻搜索引擎 (DuckDuckGo News)
                try:
                    logger.info(f"Attempting DDGS News search for: {clean_query}")
                    news_items = list(ddgs.news(clean_query, max_results=8))
                    
                    if news_items:
                        results = "根据新闻中心为您找到以下最新资讯：\n"
                        for i, item in enumerate(news_items):
                            title  = item.get('title', '无标题')
                            source = item.get('source', '未知来源')
                            date   = item.get('date',   '未知日期')
                            results += f"[{i+1}] {title} (来源: {source}, 日期: {date})\n"
                        return results
                except Exception as news_err:
                    logger.warning(f"DDGS News endpoint failed, falling back to Web Search: {news_err}")
                
                # 策略 2 (Fallback): 使用通用 Web 搜索并开启 'd' (最近24小时) 过滤
                # 通用搜索通常比专门的新闻搜索抗封锁能力更强
                logger.info(f"Attempting DDGS Web Search fallback (timelimit='d') for: {clean_query}")
                web_news = list(ddgs.text(clean_query, max_results=8, timelimit='d'))
                
                if not web_news:
                    # 如果 24 小时没结果，放宽到一周
                    logger.info("No news in past 24h, widening to past week...")
                    web_news = list(ddgs.text(clean_query, max_results=8, timelimit='w'))

                if web_news:
                    results = "根据实时全网搜索为您找到以下最新动态：\n"
                    for i, item in enumerate(web_news):
                        title = item.get('title', '无标题')
                        body  = item.get('body', '')
                        # 截取 body 前 60 个字作为摘要
                        desc  = (body[:60] + '...') if len(body) > 60 else body
                        results += f"[{i+1}] {title}\n    摘要: {desc}\n"
                    return results

            return f"暂时未能找到关于 '{clean_query}' 的相关新闻资讯。"

        except Exception as e:
            err_msg = str(e).lower()
            logger.warning(f"search_news attempt {attempt} total failure: {err_msg}")
            
            if "403" in err_msg or "ratelimit" in err_msg or "decodeerror" in err_msg:
                if attempt < max_retries:
                    time.sleep(wait_seconds)
                    wait_seconds *= 2
                    continue
            
            return f"抱歉，由于新闻源接口（DuckDuckGo）当前访问负载过高（403/Ratelimit），暂时无法获取实时新闻。建议您稍后尝试，或问我一些关于 A 股涨停或天气的内容。"

    return "搜索超时，请稍后刷新重试。"

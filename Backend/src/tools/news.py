from langchain_core.tools import tool
import logging
import time
from duckduckgo_search import DDGS

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
            
            # Using a single DDGS instance for search attempts
            with DDGS(timeout=10) as ddgs:
                # Strategy 1: DDGS News (Specifically for news articles)
                try:
                    news_items = list(ddgs.news(clean_query, max_results=5))
                    if news_items:
                        results = f"找到关于 '{clean_query}' 的最新新闻：\n"
                        for i, item in enumerate(news_items):
                            results += f"[{i+1}] {item.get('title')} (来源: {item.get('source')})\n"
                        return results
                except Exception as e:
                    if "403" in str(e):
                        logger.warning(f"News endpoint 403 during attempt {attempt}")
                    else:
                        logger.error(f"News search error: {e}")

                # Strategy 2: Web search with time limit (Fallback for news)
                logger.info("Falling back to general web search with 'past week' filter...")
                web_results = list(ddgs.text(clean_query, max_results=5, timelimit='w'))
                if web_results:
                    results = f"为您全网搜索到以下最新动态：\n"
                    for i, item in enumerate(web_results):
                        results += f"[{i+1}] {item.get('title')}\n    {item.get('body')[:80]}...\n"
                    return results

            return f"暂时未能找到关于 '{clean_query}' 的相关新闻资讯。"

        except Exception as e:
            err_str = str(e).lower()
            if "403" in err_str or "ratelimit" in err_str:
                logger.warning(f"Rate limit hit in search_news (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(wait_seconds * attempt)
                    continue
            return f"抱歉，搜索服务（DDG）由于访问频繁暂时受限 (403)，请稍后再试，或询问天气、A股等其他信息。"

    return "搜索超时，请稍后刷新重试。"

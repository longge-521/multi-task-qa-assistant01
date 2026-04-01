from .weather import get_weather
from .news import search_news
from .stock import get_stock

# A list to easily import into agent setup
get_agent_tools = [get_weather, search_news, get_stock]

import os
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables, overriding system ones if existing in .env
load_dotenv(override=True)

from src.agent import get_agent_response
from src.tools import get_agent_tools

app = Flask(__name__)
# Enable CORS for cross-origin requests from the Vue frontend
CORS(app)

@app.route('/api/tools', methods=['GET'])
def get_tools():
    """
    Returns dynamically the list of all registered agent tools with their metadata.
    The frontend uses this to build the welcome message at startup.
    """
    # Human-readable Chinese display labels for each tool name
    tool_labels = {
        "get_weather": "实时天气",
        "search_news": "新闻搜索",
        "get_stock":   "A股涨停",
    }
    # Icon identifiers for each tool (interpreted by the frontend)
    tool_icons = {
        "get_weather": "weather",
        "search_news": "news",
        "get_stock":   "stock",
    }

    tools_info = []
    for tool in get_agent_tools:
        # LangChain tool.description includes function signature like:
        # "get_weather(location: str) -> str - 获取指定城市..."
        # We strip everything before ' - ' to get just the clean docstring.
        raw_desc = tool.description or ""
        if " - " in raw_desc:
            clean_desc = raw_desc.split(" - ", 1)[1].strip()
        else:
            clean_desc = raw_desc.strip()

        tools_info.append({
            "name": tool.name,
            "label": tool_labels.get(tool.name, tool.name),
            "icon":  tool_icons.get(tool.name, "default"),
            "description": clean_desc,
        })

    logger.info(f"Serving tools list: {[t['name'] for t in tools_info]}")
    return jsonify({"tools": tools_info})

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main endpoint for the multi-task QA assistant.
    Expected JSON: { "session_id": "user123", "query": "...", "model": "deepseek-chat" }
    """
    data = request.json
    session_id = data.get("session_id", "default_session")
    query = data.get("query")
    model = data.get("model", "deepseek-chat") # Default to chat model
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    logger.info(f"Received query from session_id: {session_id} - Query: {query} - Model: {model}")

    try:
        # Pass the selected model to the agent logic
        result = get_agent_response(session_id, query, model=model)
        logger.info(f"Successfully generated response for session: {session_id}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error handling /api/chat request: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', '1') == '1'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)

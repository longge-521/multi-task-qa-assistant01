from .config import settings
from langchain_community.chat_message_histories import SQLChatMessageHistory

def get_session_history(session_id: str):
    """
    Retrieves or creates a chat message history for a specific session ID
    from the local SQLite database.
    """
    db_url = settings.SQLITE_URL
    
    # LangChain provides SQLChatMessageHistory out of the box to store messages
    return SQLChatMessageHistory(
        session_id=session_id,
        connection_string=db_url
    )

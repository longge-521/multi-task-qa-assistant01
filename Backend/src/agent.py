from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory

import logging
from .llm import init_llm
from .tools import get_agent_tools
from .memory import get_session_history

logger = logging.getLogger(__name__)

def build_agent(model_name="deepseek-chat"):
    # 1. Init DeepSeek LLM with specific model
    llm = init_llm(model_name=model_name)
    
    # 2. Get tools
    tools = get_agent_tools
    
    # 3. Create the prompt tailored for tool usage
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个非常有用、聪明的多任务问答助手。你可以并且应该在需要时使用工具。你的目标是提供准确且易于理解的结构化自然语言回答。当工具返回异常时，请礼貌地告知用户无法获取信息。"),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    # 4. Create tool calling agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # 5. Create executor
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        max_iterations=5,
        return_intermediate_steps=True
    )
    
    # 6. Wrap with memory
    agent_with_history = RunnableWithMessageHistory(
        agent_executor,
        get_session_history=get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
    return agent_with_history

# Cache for initialized agents per model
_agents = {}

def get_agent_response(session_id: str, query: str, model: str = "deepseek-chat"):
    """
    Drives the agent with history logic and extracts structured output.
    Uses the requested model for inference.
    """
    global _agents
    
    # Lazy init agent for the requested model
    if model not in _agents:
        logger.info(f"Initializing multi-task agent for model: {model}")
        _agents[model] = build_agent(model_name=model)
        
    system_agent = _agents[model]
    
    logger.info(f"Agent ({model}) invoking with query: '{query}'")
    
    response = system_agent.invoke(
        {"input": query},
        config={"configurable": {"session_id": session_id}}
    )
    
    # Extract intermediate steps (tools used)
    tools_used = []
    if "intermediate_steps" in response:
        for action, observation in response["intermediate_steps"]:
            tools_used.append({
                "tool": action.tool,
                "tool_input": action.tool_input
            })
            
    return {
        "answer": response["output"],
        "tools_used": tools_used
    }

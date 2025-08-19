# Reference - Official documentation: https://github.com/langchain-ai/langchain-mcp-adapters


from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import asyncio
import os

import dotenv
dotenv.load_dotenv()

client = MultiServerMCPClient(
    {
        "math": {
            "command": "python",
            # Make sure to update to the full absolute path to your math_server.py file
            "args": ["./mcp-using-langchain/mathserver.py"],
            "transport": "stdio",
        },
        "weather": {
            # Make sure you start your weather server on port 8000
            "url": "http://localhost:8000/mcp/",
            "transport": "streamable_http",
        }
    }
)

async def main():
    # Wait for the tools to be available
    try:
        tools = await asyncio.wait_for(client.get_tools(), timeout=10)
    except asyncio.TimeoutError:
        print("Timeout: One of the MCP servers is not responding.")
        return

    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

    # Create an agent with the available tools
    agent = create_react_agent("openai:gpt-4o", tools)

    # Invoke the agent with a math question
    math_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
    print(f"Math Response: {math_response['messages'][-1].content}")

    # Invoke the agent with a weather question
    weather_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
    print(f"Weather Response: {weather_response['messages'][-1].content}")

if __name__ == "__main__":
    asyncio.run(main())
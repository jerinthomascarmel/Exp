
import anyio

# from mcp.client.stdio import StdioServerParameters
from exp.importer import MCPClient
from exp.importer.stdio import StdioServerParameters


# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="uv",  # Using uv to run the server
    # Server with completion support
    args=["run", "./server.py"],

)


async def main():
    """Run the completion client example."""

    mcp_client = MCPClient(
        server=server_params
    )
    await mcp_client.run()
    print("MCP client running.")

    # must to initialize before calling anything
    # please not about cwd . the process must be started in the directory where server.py is located.
    # await mcp_client.initialize()
    # print("MCP client initialized.")

    print('.............')
    print(mcp_client._session._server_capabilities)
    print('.............')

    result = await mcp_client.call_function(
        "add",
        {"a": 5, "b": 7}
    )
    print('.............')
    print(mcp_client._session._server_capabilities.functions)
    print('.............')
    print(f"Result of add(5, 7): {result}")
    print(type(result.structuredContent))
    print(type(result.structuredContent['result']))

    await mcp_client.close()
    print('conn closed !')


if __name__ == "__main__":
    anyio.run(main)

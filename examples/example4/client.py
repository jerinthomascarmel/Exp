import anyio

from exp.importer import Importer
from exp.importer.stdio import StdioParameters


# Create server parameters for stdio connection
server_params = StdioParameters(
    command="node",  # Using uv to run the server
    args=["./dist/server.js"],
)


async def main():
    """Run the completion client example."""

    mcp_client = Importer(
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

    func = mcp_client.get_function("add")
    print(f"Function 'add' info: {func}")
    result = await func(a=5, b=6)

    print(f"Result of add(5, 6): {result}")
    # print(type(result.structuredResult))
    # print(type(result.structuredResult['result']))

    await mcp_client.close()
    print('conn closed !')


if __name__ == "__main__":
    anyio.run(main)

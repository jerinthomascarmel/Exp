import anyio

from exp.importer import Importer
from exp.importer.stdio import StdioParameters


# Create server parameters for stdio connection
server_params = StdioParameters(
    command="uv",  # Using uv to run the server
    args=["run", "./server.py"],
)


async def main():
    """Run the completion client example."""

    mcp_client = Importer(
        server=server_params
    )
    
    await mcp_client.run()

    lists = await mcp_client.list_functions()
    print("Available functions:", lists)

    # func = mcp_client.get_function("add");
    # result =await func(a=5,b=7);
    # print(f"Result of add(5, 7): {result}")

    await mcp_client.close()


if __name__ == "__main__":
    anyio.run(main)

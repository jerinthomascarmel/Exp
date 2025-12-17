from exp.exporter import FastMCP
import traceback


mcp = FastMCP()

@mcp.function()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    try:
        mcp.run()
    except Exception as e:
        with open('log.txt', 'a') as f:
            f.write("Error running MCP server:\n")
            traceback.print_exc(file=f)

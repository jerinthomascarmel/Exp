from exp.exporter import Exporter


mcp = Exporter()


@mcp.function()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    mcp.run()
    

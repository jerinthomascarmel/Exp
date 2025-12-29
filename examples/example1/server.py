from exp.exporter import Exporter


mcp = Exporter()

@mcp.function()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


class CustomClass:
    def __init__(self, value: str):
        self.value = value
        self.just = "an attribute"


    
@mcp.function()
def greet(name: str) -> CustomClass:
    """Greet a person by name."""
    return CustomClass(value=name)

if __name__ == "__main__":
    mcp.run()
    

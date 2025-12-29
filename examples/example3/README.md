# Python to TypeScript Export Example

This example demonstrates how to export a Python function and call it from TypeScript/JavaScript.

## Setup

### Python Environment

```bash
# Initialize and setup Python environment
uv init
uv add Exp
```

Create `server.py` with your Python functions (see code reference below).

### Node.js Environment

```bash
# Initialize npm
npm init -y

# For TypeScript projects
npx tsc --init
npm install export-ts
npm install -D typescript @types/node
```

**Important:** Update `tsconfig.json` compiler target to `ES2022`, `ESNext`, or `ES2014`.

Write a TypeScript file which exports Python functions (see the code `client.ts`).

### Running the Example

In the root folder:

```bash
# Compile TypeScript
npx tsc

# Run
node dist/client.js

# Or use ts-node
npx ts-node client.ts
```

## Code Reference

### server.py
See: `./server.py`
- Uses `Exporter` from `exp.exporter`
- Defines an `add` function decorated with `@mcp.function()`

### client.ts
See: `./client.ts`
- Uses `Importer` from `export-ts`
- Configures `StdioParameters` with command `"uv"` and args `["run", "./server.py"]`
- Calls the Python `add` function with parameters `{a: 10, b: 20}`

## Key Points

- The `args` parameter in `StdioParameters` must include the path to your Python file
- All functions are asynchronous
- Always call `importer.close()` when done
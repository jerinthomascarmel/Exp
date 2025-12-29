# Typescript to Python Export Example

This example demonstrates how to export a Ts/Js function and call it from Python.

## Setup

### Node.js Environment

```bash
# Initialize npm
npm init -y

# For TypeScript projects
npx tsc --init
npm install export-ts
npm install -D typescript @types/node
```

Write a TypeScript file with your ts/js functions. 

**Important:** Update `tsconfig.json` compiler target to `ES2022`, `ESNext`, or `ES2014`.

### Python Environment

```bash
# Initialize and setup Python environment
uv init
uv add Exp
```
Write a python file like `client.py` exporting your typescript/javascript functions.  ( see code reference )


### Running the Example

In the root folder:

```bash

# Run
uv run client.py
```

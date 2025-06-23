# 🧪 Lab 3: Creating an MCP Server with Semantic Kernel

In this lab, you'll create a **Model Context Protocol (MCP)** server using **Semantic Kernel**. This server exposes a chat-based agent that can answer questions about restaurant menus, including:

- 🏢 Listing available restaurants
- 🥗 Recommending daily specials
- 💰 Checking prices for menu items

---

## 📁 Source Code

The full reference code for this lab is located at:

```
/servers/menu_agent_server.py
/servers/restaurant_booking_agent_server.py
```

You can modify and run these files directly from your dev container or workspace.

## 🧩 Code Walkthrough

### 1️⃣ Argument Parsing

The script uses `argparse` to allow switching between `stdio` and `sse` transports:

```python
parser.add_argument(
    "--transport",
    choices=["sse", "stdio"],
    default="stdio",
    help="Transport method to use",
)
```

This lets the server work either through standard input/output (for tools like GitHub Copilot Chat) or over HTTP (for browser-based testing).

### 2️⃣ Plugin Definition

The `RestaurantPlugin` class is a simple Semantic Kernel plugin that has these three functions:

- `list_restaurants`: Returns a hardcoded list of restaurants.
- `get_specials`: Returns daily specials for each restaurant.
- `get_item_price`: Returns a static price based on the restaurant.

The `BookingPlugin` class is a simple Semantic Kernel plugin that has a single functions:

- `book_a_table`: Allows user to book a table in a restaurant and returns 'confirmed' or 'denied'.

Each function includes rich descriptions and type annotations for use with LLM agents

### 3️⃣ Agent Initialization

A `ChatCompletionAgent` is created using Azure OpenAI as the backend, and the plugin is passed to the agent:

```python
async_openai_client = AsyncAzureOpenAI(...)
chat_service = AzureChatCompletion(...)

agent = ChatCompletionAgent(
    service=chat_service,
    name="Host",
    instructions="Answer questions about the menu for different restaurants...",
    plugins=[RestaurantPlugin()],
)
```

The agent can now intelligently call the plugin’s methods to answer user queries.

### 4️⃣ MCP Server Setup

The agent is exposed as an MCP server using:

```python
server = agent.as_mcp_server()
```

Depending on the selected transport:

- If --transport stdio: it uses mcp.server.stdio to integrate with tools like GitHub Copilot Chat.
- If --transport sse: it uses uvicorn and starlette to expose an HTTP endpoint (at /sse) for browser or local network interaction.

## 🚀 Try It Out! (with GitHub Copilot Chat)

You can run this server as a plugin inside GitHub Copilot Chat (Agent Mode).

### ➤ Step-by-step:

1. Open .vscode/mcp.json.

2. Add the following entry:

```
{
  "menu_agent_server": {
    "command": "uv",
    "args": [
      "--directory=/workspace/servers",
      "run",
      "menu_agent_server.py"
    ],
    "env": {
      "AZURE_OPENAI_KEY": "<your key>",
      "AZURE_OPENAI_ENDPOINT": "<your endpoint>",
      "MODEL_DEPLOYMENT_API_VERSION": "<version>",
      "MODEL_DEPLOYMENT_NAME": "<deployment name>"
    }
  }
}
```

3. ✅ Ensure GitHub Copilot Chat is in Agent Mode.
4. Ask Copilot questions like:
   - “List the restaurants.”
   - “What’s the special at The Harbor?”
   - “How much is the Caesar Salad at The Farm?”

## 🔁 Alternative Usage

You can also use this MCP server as a plugin inside another Semantic Kernel agent — like in Lab 2 — to extend agent capabilities modularly.

# Model Context Protocol (MCP) Hands-On Lab

## 🧠 Introduction

This project explores how to use the **Model Context Protocol (MCP)** to extend AI agents with real-world capabilities. You’ll learn how to integrate **external MCP tools** into GitHub Copilot Chat and build custom **Semantic Kernel agents** that can invoke these tools.

By the end of these labs, you'll be able to:

- Use MCP servers within GitHub Copilot Chat
- Connect MCP tools as plugins to Semantic Kernel agents
- Build your own MCP server powered by Semantic Kernel

## ✅ Pre-requisites

Before you begin, ensure you have:

- **Visual Studio Code** with the **Dev Containers extension**
- **Docker** installed and running
- A Github Copilot subscription
- A valid **Azure Subscription** with the following resources provisioned:
  - AzureOpenAI resource with a deployed **Chat Completion Model** (e.g., `gpt-4o`, `gpt-4o-mini`)
- **For Lab 2**: A GitHub account and a **Personal Access Token (PAT)**  
  → [How to create a PAT](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

## 🛠️ Setup Instructions

1. **Clone this repository.**

2. **Open the project in Visual Studio Code** and reopen it inside the provided **Dev Container**.  
   All required dependencies will be installed automatically.

3. **Configure environment variables**:  
   Use the `.envtemplate` file as a guide to create a `.env` file with your Azure credentials and deployment details.

## 🧪 Lab Descriptions

### 🔹 Lab 1: Use an MCP Server in Copilot Chat

Learn how to run a **local MCP server** (e.g., Wikipedia server), and connect it to **GitHub Copilot Chat** through `.vscode/mcp.json`.

### 🔹 Lab 2: Use MCP as a Plugin in Semantic Kernel

Build a **Semantic Kernel agent** that connects to an **MCP server** (e.g., GitHub Plugin) to answer tool-enhanced questions.

### 🔹 Lab 3: Build Your Own MCP Server with Semantic Kernel

Create an MCP server that wraps a Semantic Kernel agent.  
Use it in **GitHub Copilot Chat** or embed it as a plugin in another Semantic Kernel agent.

## 📚 References

- [Introduction to the Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction)
- [odel Context Protocol: Specification and Reference](https://modelcontextprotocol.info/)
- [Model Context Protocol servers](https://github.com/modelcontextprotocol/servers?tab=readme-ov-file#%EF%B8%8F-official-integrations)
- [Semantic Kernel MCP Sample Codes](https://github.com/microsoft/semantic-kernel/tree/44f1253460191e4945abc75ddbba1dd7ba964a32/python/samples/concepts/mcp)

---

## 💬 Contact

For questions or feedback, feel free to open an issue or reach out via email.

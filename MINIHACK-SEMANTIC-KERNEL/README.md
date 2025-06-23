# Semantic Kernel Hands-On Lab

## 🧠 Introduction

Welcome to the **Semantic Kernel Hands-On Lab Repository**! This repository is your gateway to learning **Semantic Kernel**, Microsoft’s open-source SDK that enables developers to build intelligent applications with Large Language Models (LLMs).

This hands-on lab series is designed to help you explore Semantic Kernel through practical, guided exercises. You’ll start by learning the core components of the SDK, then progress to more advanced patterns like agent orchestration.

Each lab is focused, self-contained, and builds toward a deeper understanding of how to develop intelligent, function-driven applications using Semantic Kernel.

## ✅ Pre-requisites

Before you begin, ensure you have:

- **Visual Studio Code** with the **Dev Containers extension**
- **Docker** installed and running
- A valid **Azure Subscription** with the following resources provisioned:
  - **Azure AI Foundry** resource with:
    - A **Foundry Project**
    - A deployed **Chat Completion Model** (e.g., `gpt-4o`, `gpt-4o-mini`)
    - A deployed **Embedding Model** (e.g., `text-embedding-3-small`)
  - **Azure AI Search** service

## 🛠️ Setup Instructions

1. Clone the repository.

2. **Open the project in Visual Studio Code** and reopen it inside the provided **dev container**.  
   All required dependencies will be installed automatically.

3. **Configure environment variables**:  
   Use the provided `.envtemplate` file as a reference and create a `.env` file with your Azure credentials and endpoints.

4. **(Optional)**: Ingest sample data into your Azure AI Search resource.  
   This step only needs to be run once per environment:

```bash
 python scripts/azure_ai_search_ingest.py
```

## 🧪 Lab Descriptions

### 📘 Lab 1: Semantic Kernel Core Concepts ([01_semantic_kernel_core.ipynb](/labs/01_semantic_kernel_core.ipynb))

This lab introduces the foundational building blocks of Semantic Kernel. You'll learn how to assemble a working pipeline by configuring services, plugins, memory, and prompts.

#### 🔧 What You'll Do:

- Initialize and configure the Semantic Kernel
- Add chat completion and embedding services
- Register plugins and custom functions
- Connect a memory store (vector database)
- Apply pre- and post-execution filters
- Use prompt templates to define dynamic instructions

🧠 **Key Goal**: Build a strong understanding of Semantic Kernel’s core components—kernel, functions, plugins, memory, and prompt orchestration.

### 🤖 Lab 2: Agent Framework ([02_agent_framework.ipynb](/labs/02_agent_framework.ipynb))

Dive into Semantic Kernel’s Agent Framework to orchestrate more dynamic, multi-step interactions using agents and tool invocation.

#### 🔧 What You'll Do:

- Create and configure various types of agents
- Implement a simple multi-agent orchestration pattern

🧠 **Key Goal**: Learn how to design flexible, tool-augmented agents and orchestrate intelligent workflows using the Agent Framework.

### 🚧 Lab 3: Challenge – Multi-Agent Report Generator (no starter code)

In this open-ended challenge, you’ll apply everything you’ve learned to build a multi-agent system that analyzes and reports on health plan documents. You'll create a team of four agents that collaborate to search, generate, validate, and orchestrate a structured report.

#### 🔧 Your Task:

- **Search Agent** – Queries an Azure AI Search index for policy information
- **Report Agent** – Generates a detailed summary from search results
- **Validation Agent** – Ensures the report meets key criteria (e.g., includes coverage exclusions)
- **Orchestrator Agent** – Coordinates the flow between all other agents

🧠 **Key Goal**: Design and implement an end-to-end multi-agent solution that mirrors a real-world use case, combining skills in orchestration, validation, and semantic search.

💡 **Hint**: You can register agents as plugins—this allows the orchestrator to invoke other agents just like any other tool or function.

## 📚 References

- [Semantic Kernel Documentation](https://learn.microsoft.com/en-us/semantic-kernel/)
- [Semantic Kernel Python SDK Reference](https://learn.microsoft.com/en-us/python/api/semantic-kernel/semantic_kernel?view=semantic-kernel-python)
- [Semantic Kernel Sample Codes](https://github.com/microsoft/semantic-kernel/tree/44f1253460191e4945abc75ddbba1dd7ba964a32/python/samples)
- [Azure AI Agent labs](https://github.com/Azure/azure-ai-agents-labs)

---

## 💬 Contact

For questions or feedback, feel free to open an issue or reach out via email.

# 🚀 Production RAG MCP Server

A high-performance, production-ready Model Context Protocol (MCP) server built with **FastMCP** and **ChromaDB**. This server enables LLMs (like Claude) to perform semantic search, ingest multiple document formats, and efficiently retrieve context from a persistent knowledge base.

## ✨ Key Features

- **Multi-Format Ingestion**: Native support for PDF, DOCX, Markdown, and TXT files.
- **Smart Chunking**: Automatic recursive text splitting (1000 chars, 100 overlap) using LangChain for optimal LLM context.
- **Persistent Knowledge Base**: Local vector storage using ChromaDB that persists across restarts.
- **Deduplication**: MD5 hashing ensures files are only indexed when modified.
- **Security First**: Absolute path sandboxing to prevent unauthorized file access.
- **Auto-Sync**: Automatically scans and indexes the `data/` folder on startup.

## 🛠️ Tech Stack

- **Framework**: [FastMCP](https://github.com/jlowin/fastmcp)
- **Vector DB**: [ChromaDB](https://www.trychroma.com/)
- **Embeddings**: Sentence-Transformers (Default)
- **Chunking**: LangChain Text Splitters
- **Environment**: [uv](https://github.com/astral-sh/uv)

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have `uv` installed. If not, install it via:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Installation
Clone the repository and install dependencies:
```powershell
uv sync
```

### 3. Usage
Place your documents in the `data/` folder and start the server:
```powershell
uv run main.py
```

---

## 🔌 Claude Desktop Integration

To use this with Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rag-server": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/RAGMCP",
        "run",
        "main.py"
      ]
    }
  }
}
```

---

## 🧰 Available Tools

| Tool | Description |
| :--- | :--- |
| `ingest_file` | Extract and index text from a PDF, DOCX, or TXT file. |
| `add_document` | Manually add a raw string to the knowledge base. |
| `search_documents` | Perform semantic search to find the most relevant context. |
| `list_documents` | View a paginate list of indexed document chunks. |
| `delete_document` | Remove a document or chunk by its unique ID. |
| `ping` | Health check to verify server responsiveness. |

## 📂 Project Structure

```text
RAGMCP/
├── chroma_data/          # Persistent Vector Database
├── data/                 # Knowledge Base (Drop files here!)
├── main.py               # Core Server Logic
├── pyproject.toml        # Dependencies & UV Config
└── README.md             # Documentation
```

## 🛡️ Production Notes
- **Security**: The server restricts file access to the established `data/` directory.
- **Logging**: Full structured logging is implemented for easy debugging and monitoring.
- **Efficiency**: Only changes to files (detected via MD5) trigger re-indexing.

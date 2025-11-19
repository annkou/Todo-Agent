# Todo Agent - Plan & Execute AI System

A prototype AI agent system that automatically breaks down high-level objectives into actionable tasks, executes them sequentially, and maintains persistent session state with resume capabilities.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#📁-project-structure)
- [Technical Details](#technical-details)
- [Examples](#examples)
- [Future Extensions](#future-extensions)
- [References](#references)

---

## Overview

The Todo Agent is a **plan-and-execute AI system** that:

1. **Plans**: Takes a high-level user objective and breaks it into a structured TODO list
2. **Executes**: Runs each task sequentially using AI agents with web search and scraping tools
3. **Persists**: Stores session state in a SQLite database for resumption
4. **Recovers**: Handles interruptions gracefully and allows resuming from where it left off

! Each session is uniquely identified by a **SHA-256 hash of the objective**, ensuring that the same objective always maps to the same session. This enables automatic session resumption - if you run the same objective twice, it will resume the previous session instead of starting from scratch.

---

## Architecture

The system consists of three main components:

### 1. **Planner Agent** (`planner.py`)
- **Role**: Strategic planning
- **Input**: High-level objective (e.g., "Plan a 3-day trip to Rome")
- **Output**: Structured TODO list with numbered tasks
- **Model**: GPT-4o
- **Technology**: LangChain agent with structured output (Pydantic)

### 2. **Executor Agent** (`executor.py`)
- **Role**: Task execution
- **Input**: Single task description + context from completed tasks
- **Output**: Task result, status (completed/failed), and reflection
- **Model**: GPT-4o-mini
- **Tools**: 
  - Tavily Search (web search)
  - Tavily Extract (web scraping)
- **Safety**: ModelCallLimitMiddleware (15 calls max per task)
- **Technology**: LangChain agent with tool calling

### 3. **Session Manager** (`session_manager.py`)
- **Role**: Orchestration and state management
- **Functions**:
  - `start_new_session()`: Creates plan and executes tasks
  - `resume_session()`: Resumes interrupted sessions
  - `handle_user_input()`: Entry point - decides new vs resume

---

## How It Works

### **The Complete Loop**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER INPUT                                               │
│    User provides objective: "Plan a trip to Rome"           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. HASH GENERATION (main.py)                                │
│    thread_id = SHA256(objective)                            │
│    → Same objective = Same thread_id = Same session         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SESSION CHECK (session_manager.py)                       │
│    Does session exist in database?                          │
│    ├─ YES → Resume existing session                         │
│    └─ NO  → Start new session                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. PLANNING PHASE (Planner Agent)                           │
│    Objective → Planner Agent (GPT-4o)                       │
│    ↓                                                         │
│    Structured TODO List:                                    │
│    - Task #1: Research flights                              │
│    - Task #2: Book accommodation                            │
│    - Task #3: Create itinerary                              │
│    ↓                                                         │
│    Store in database (Thread + Tasks tables)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. EXECUTION LOOP (Executor Agent)                          │
│    FOR EACH task in pending_tasks:                          │
│      ├─ Mark task as "in_progress"                          │
│      ├─ Gather context from completed tasks                 │
│      ├─ Execute with Executor Agent (GPT-4o-mini + tools)   │
│      │   ↓                                                   │
│      │   Agent may call tools:                              │
│      │   - TavilySearch (web search)                        │
│      │   - TavilyExtract (web scraping)                     │
│      │   ↓                                                   │
│      │   Returns: {status, result, reflection}              │
│      ├─ Update database with result                         │
│      ├─ Check status:                                       │
│      │   - completed → Continue to next task                │
│      │   - failed → Stop execution                          │
│      └─ Add to completed_steps for next task context        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. COMPLETION                                               │
│    - Mark session as complete                               │
│    - Display final result from last completed task          │
└─────────────────────────────────────────────────────────────┘
```

### **Detailed Execution Flow**

#### **Phase 1: Planning (Planner Agent)**

```python
# User objective
objective = "Gather the latest news about Microsoft and draft a short blog post"

# Planner Agent receives this and produces:
{
  "tasks": [
    {
      "id": 1,
      "title": "Identify Reliable News Sources",
      "content": "Search for the latest news articles and updates about Microsoft from reliable sources.",
      "status": "pending"
    },
    {
      "id": 2,
      "title": "Search for Latest News on Microsoft",
      "content": "Use the identified sources to search for the latest news articles about Microsoft.",
      "status": "pending"
    },
    {
      "id": 3,
      "title": "Select Relevant News Articles",
      "content": "Choose the most relevant and recent news articles about Microsoft that would be of interest to the blog's audience.",
      "status": "pending"
    },
    {
      "id": 4,
      "title": "Summarize Key Points",
      "content": "Summarize the key points from the selected news articles to include in the blog post.",
      "status": "pending"
    },
    {
      "id": 5,
      "title": "Draft Blog Post",
      "content": "Write a short blog post using the summarized key points, ensuring it is engaging and informative.",
      "status": "pending"
    }
  ]
}
```

This structured output is stored in the database with the session.

#### **Phase 2: Execution (Executor Agent)**

For **each task**, the Executor Agent:

1. **Receives context**:
   ```python
   input_text = """
   Context from previous steps:
   Step #1: Identify Reliable News Sources
   Description: Search for the latest news articles...
   Result: ...
   
   Current task to execute: Search for Latest News on Microsoft
   """
   ```

2. **Agent processes** using:
   - Internal reasoning (GPT-4o-mini)
   - Tool calls when needed (searches web, scrapes URLs)

3. **Returns structured result**:
   ```python
   {
     "task": "Search for Latest News on Microsoft",
     "status": "completed",
     "reflection": "Utilizing reliable sources like TechCrunch..."
   }
   ```

4. **Updates database** and continues to next task

#### **Phase 3: Context Accumulation**

Each completed task becomes context for the next:

```python
completed_steps = [
  {
    "id": 1,
    "title": "Identify Reliable News Sources",
    "description": "Search for the latest news articles...",
    "result": 
  },
  {
    "id": 2,
    "title": "Search for Latest News on Microsoft",
    "description": "Use the identified sources to search...",
    "result": 
  }
]

# Task #3 receives ALL previous results as context
```

This ensures that later tasks have all the information they need from earlier work.

---

## Installation

### Prerequisites

- Python 3.11+
- OpenAI API key
- Tavily API key

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Todo-Agent
   ```

2. **Install dependencies** (using uv):
   ```bash
   uv sync
   ```

3. **Create `.env` file**:
   ```bash
   # .env
   OPENAI_API_KEY=sk-...
   TAVILY_API_KEY=tvly-...
   DATABASE_DSN=sqlite:///todo_agent.db
   ```

4. **Initialize database**:
   The database will be automatically created on first run.

---

## Configuration

Configuration is managed through `config.py` using Pydantic Settings:

```python
# todo_agent/config.py
class Settings(BaseSettings):
    openai_api_key: str
    tavily_api_key: str
    database_dsn: str

    model_config = SettingsConfigDict(env_file=".env")
```

**Environment variables**:
- `OPENAI_API_KEY`: OpenAI API key for agents
- `TAVILY_API_KEY`: Tavily API key for web search/scraping
- `DATABASE_DSN`: Database connection string (default: SQLite)

---

## Usage

### Basic Usage

```bash
uv run -m todo_agent.main 
```

You'll be prompted:
```
Enter your objective: Gather the latest news about Microsoft and draft a short blog post
```

## 📁 Project Structure

```
Todo-Agent/
├── todo_agent/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration & settings
│   ├── db.py                # Database setup (SQLAlchemy)
│   ├── crud.py              # Database models & operations
│   ├── session_manager.py   # Session orchestration logic
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planner.py       # Planner Agent (GPT-4o)
│   │   └── executor.py      # Executor Agent (GPT-4o-mini)
│   │
│   └── tools/
│       ├── search.py        # Tavily Search tool
│       └── web_scraper.py   # Tavily Extract tool
│
├── pyproject.toml           # Project dependencies
├── .env                     # Environment variables (not in repo)
├── README.md                # This file
└── agent_state.db           # (auto-created)
```

---

## Technical Details

### Thread ID Generation

```python
import hashlib

objective = "Gather the latest news about Microsoft and draft a short blog post"
thread_id = hashlib.sha256(objective.encode('utf-8')).hexdigest()
```

**Why SHA-256?**
- **Deterministic**: Same input always produces same output
- **Unique**: Different objectives produce different hashes
- **Collision-resistant**: Extremely unlikely for two objectives to produce the same hash


### LangGraph Checkpoints

The system uses LangGraph's checkpoint system to maintain agent conversation state:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("agent_state.db")
```

This allows agents to maintain conversation history across invocations within the same thread.

---


## Examples

### Example 1: First Run (New Session)

**Objective**: "Gather the latest news about Microsoft and draft a blog post"

```
✨ Starting new session...
🔧 Planning tasks...

Proposed TODO List:
- #1 Identify Reliable News Sources: Find reliable and up-to-date news sources that cover technology and business news, such as TechCrunch, The Verge, or Bloomberg.
- #2 Search for Latest News on Microsoft: Use the identified sources to search for the latest news articles about Microsoft.
- #3 Select Relevant News Articles: Choose the most relevant and recent news articles about Microsoft that would be of interest to the blog's audience.
- #4 Summarize Key Points: Summarize the key points from the selected news articles to include in the blog post.
- #5 Draft Blog Post: Write a short blog post using the summarized key points, ensuring it is engaging and informative.

🔄 Executing task #1: Identify Reliable News Sources
→ status: completed
→ reflection: Identified key sources for technology and business news.

🔄 Executing task #2: Search for Latest News on Microsoft
→ status: completed
→ reflection: Utilizing reliable sources like TechCrunch and Bloomberg provides comprehensive insights into Microsoft's latest developments.

🔄 Executing task #3: Select Relevant News Articles
→ status: completed
→ reflection: Selected articles highlight Microsoft's significant investments and innovations in AI, showcasing its strategic direction and market influence.

🔄 Executing task #4: Summarize Key Points
→ status: completed
→ reflection: The summaries provide a concise overview of Microsoft's recent strategic investments and product developments in the AI sector.

🔄 Executing task #5: Draft Blog Post
→ status: completed
→ reflection: The blog post effectively summarizes Microsoft's recent strategic initiatives in AI and cloud computing, making it engaging and informative for readers.

📝 FINAL RESULT:
### Microsoft’s Bold Moves in AI and Cloud Computing

In recent months, Microsoft has made significant strides in the realms of artificial intelligence and cloud computing, showcasing its commitment to innovation and strategic partnerships.        

1. **$9.7 Billion Deal with IREN**
Microsoft has signed a groundbreaking five-year agreement worth approximately **$9.7 billion** with IREN Ltd., an Australian data center firm. This deal positions Microsoft as IREN's largest customer, granting access to advanced Nvidia systems tailored for AI workloads. The agreement includes a prepayment of 20%, underscoring Microsoft's aggressive push into AI computing capacity.     
[Read more here](https://www.bloomberg.com/news/articles/2025-11-03/microsoft-signs-9-7-billion-ai-cloud-deal-with-australia-s-iren).

2. **Investment in Anthropic**
In a strategic move to bolster its AI capabilities, Microsoft, alongside Nvidia, is investing up to **$15 billion** in Anthropic, a prominent AI developer. This partnership will enable Anthropic to purchase **$30 billion** worth of computing capacity from Microsoft’s Azure cloud platform, reinforcing their alliance in the competitive AI landscape.
[Read more here](https://www.bloomberg.com/news/newsletters/2025-11-18/microsoft-nvidia-pump-billions-into-anthropic).

3. **$15.2 Billion Investment in the UAE**
Microsoft is set to invest **$15.2 billion** in the UAE over the next four years, aiming to transform the region into a hub for AI research and development. This ambitious plan includes the first shipments of advanced Nvidia GPUs and a commitment to train **one million residents** by 2027, marking a significant step in US AI diplomacy.
[Read more here](https://techcrunch.com/2025/11/03/microsofts-15-2b-uae-investment-turns-gulf-state-into-test-case-for-us-ai-diplomacy/).

4. **Launch of Copilot Mode in Edge**
In a bid to enhance user experience, Microsoft has introduced **Copilot Mode** in its Edge browser. This AI assistant is designed to summarize information and assist users with tasks such as booking hotels. The launch comes just two days after OpenAI released a similar product, highlighting the fierce competition in the AI development space.
[Read more here](https://techcrunch.com/2025/10/23/two-days-after-openais-atlas-microsoft-launches-a-nearly-identical-ai-browser/).

As Microsoft continues to innovate and expand its influence in AI and cloud computing, these strategic moves not only reflect its commitment to technological advancement but also its role in shaping the future of the industry.
```
### Example 2: Resume Session

Press `Ctrl+C` during execution of one of the tasks

**Objective**: "Gather the latest news about Microsoft and draft a blog post"

```
✨ Starting new session...
🔧 Planning tasks...

Proposed TODO List:
- #1 Identify Reliable News Sources: List reliable news sources for technology and business news, such as TechCrunch, The Verge, Bloomberg, and Reuters.
- #2 Search for Latest News on Microsoft: Use the identified sources to search for the latest news articles about Microsoft.
- #3 Select Relevant News Articles: Choose the most relevant and recent news articles about Microsoft from the search results.
- #4 Summarize News Articles: Write a brief summary of each selected news article, focusing on key points and developments.
- #5 Draft Blog Post: Combine the summaries into a cohesive blog post, ensuring a logical flow and engaging introduction and conclusion.
- #6 Review and Edit Blog Post: Proofread the blog post for clarity, grammar, and style. Make necessary edits to improve readability.

🔄 Executing task #1: Identify Reliable News Sources
→ status: completed
→ reflection: Identified reliable sources for both technology and business news.

🔄 Executing task #2: Search for Latest News on Microsoft


Keyboard interruption detected!
```

**Resume**:
```
🔄 Resuming existing session...

🔄 Resuming objective: Gather the latest news about Microsoft and draft a short blog post
Already completed: 1 tasks

⏳ Resuming execution: 5 pending tasks

🔄 Executing task #2: Search for Latest News on Microsoft
→ status: completed
→ reflection: Utilizing reliable news sources provided comprehensive and current insights on Microsoft.

🔄 Executing task #3: Select Relevant News Articles
→ status: completed
→ reflection: The selected articles provide insights into Microsoft's recent advancements and partnerships in AI technology.

🔄 Executing task #4: Summarize News Articles
→ status: completed
→ reflection: The partnerships between major tech companies and AI developers are reshaping the industry landscape.

🔄 Executing task #5: Draft Blog Post
→ status: completed
→ reflection: The task was successfully completed by synthesizing the summaries into a coherent blog post.

🔄 Executing task #6: Review and Edit Blog Post
→ status: completed
→ reflection: The blog post was successfully proofread for clarity, grammar, and style, improving its overall readability.

📝 FINAL RESULT:
**Title: Microsoft and Nvidia's Strategic Investment in Anthropic: A New Era in AI Collaboration**
In a significant move that underscores the growing importance of artificial intelligence in the tech landscape, Microsoft has announced a strategic partnership with Anthropic, a leading AI startup. This collaboration will bring Anthropic's advanced AI models, including the Claude series, to Microsoft Foundry, enhancing the capabilities available to developers and businesses using Microsoft's cloud services.
As part of this partnership, Anthropic is set to purchase a staggering $30 billion in computing capacity from Microsoft’s Azure platform, with commitments to additional capacity up to one gigawatt. This investment not only solidifies Anthropic's reliance on Azure but also positions Microsoft as a key player in the AI infrastructure market.
Moreover, Nvidia is joining the fray, investing up to $10 billion in Anthropic to optimize its models for future Nvidia architectures. This collaboration highlights the competitive landscape of 
AI development, where major players are vying for dominance.
In a related development, Microsoft and Nvidia are collectively investing up to $15 billion in Anthropic, further intertwining their futures with the AI developer. This investment comes at a time when the tech market is experiencing fluctuations, particularly in AI valuations, making this partnership a strategic move to bolster their positions against rivals like OpenAI.
Microsoft's increasing integration of Anthropic's models into its services, such as the Copilot features in Visual Studio Code and Microsoft 365, indicates a shift in preference towards Anthropic's technology over others, including OpenAI's GPT-5.
As the AI landscape continues to evolve, this partnership between Microsoft, Nvidia, and Anthropic could redefine the future of AI applications, making advanced AI more accessible and powerful for businesses worldwide.
**Conclusion**
The collaboration between Microsoft, Nvidia, and Anthropic marks a pivotal moment in the AI sector, showcasing how strategic investments and partnerships can drive innovation and enhance technological capabilities. As these companies work together to push the boundaries of AI, the implications for developers and businesses are profound, promising a future where AI plays an even more integral role in various industries.
```

### Example 3: Handling Failed Tasks

**Objective**: "Research the top 5 AI coding assistants, compare their features, pricing, and create a recommendation report."

```
 Starting new session...
🔧 Planning tasks...

Proposed TODO List:
- #1 Identify Top 5 AI Coding Assistants: Research and list the top 5 AI coding assistants currently available in the market.
- #2 Research Features of Each Assistant: For each of the top 5 AI coding assistants, gather detailed information about their features.
- #3 Research Pricing of Each Assistant: For each of the top 5 AI coding assistants, gather detailed information about their pricing models.
- #4 Compare Features and Pricing: Create a comparison table or document that outlines the features and pricing of each AI coding assistant.
- #5 Create Recommendation Report: Based on the comparison, write a recommendation report highlighting the best AI coding assistant for different use cases.

🔄 Executing task #1: Identify Top 5 AI Coding Assistants
→ status: completed
→ reflection: The research highlighted the growing diversity and specialization of AI coding assistants, catering to various developer needs.

🔄 Executing task #2: Research Features of Each Assistant
❌ Task #2 failed: Error executing step: Model call limits exceeded: run limit (15/15)
```

**Resume**:
```
 Resuming existing session...
🔄 Resuming objective: Research the top 5 AI coding assistants, compare their features, pricing, and create a recommendation report.
Already completed: 1 tasks

Failed tasks: 1
  Task #2: Research Features of Each Assistant
    → Reason: Executor returned error
```

Session stops at the failure point. User can modify objective or manually handle the failed task.

---

##  Future Extensions

This is a prototype system. Given more time and resources, here are key areas for enhancement:

- **Replanner Agent**: Add a reflection layer that evaluates completed steps and dynamically adjusts the plan based on actual results, enabling adaptive rather than rigid execution
- **Deep Agents Architecture**: Refactor using [LangChain DeepAgents](https://docs.langchain.com/oss/python/deepagents/subagents) with specialized planner and executor subagents
- **To-Do List Middleware**: Integrate LangChain's [built-in To-Do List middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in#to-do-list) for native task tracking
- **Enhanced Guardrails**: PII detection/redaction, automatic retry logic for failed tool calls
- **Context Window Management**: Handle long conversations that exceed LLM context limits using `before_model` middleware to automatically summarize or truncate conversation history
- **Token Usage & Cost Tracking**: Implement comprehensive logging to track token consumption, API costs per session/task, and generate cost analytics dashboards
- **PostgreSQL Migration**: Replace SQLite for better concurrency, scalability, and production reliability
- **Web UI**: Dashboard for real-time session monitoring and manual intervention
- **Human-in-the-Loop**: Add approval checkpoints for critical tasks

---

## References

- [LangChain Documentation](https://docs.langchain.com/oss/python/langchain/overview)
- [Tavily API](https://tavily.com/)
- [OpenAI API](https://platform.openai.com/)
- [Plan and execute with Langgraph](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/plan-and-execute/plan-and-execute.ipynb)
- [SQLAlchemy](https://www.sqlalchemy.org/)

---

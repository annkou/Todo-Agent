from typing import List, Literal, Optional

from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from todo_agent.config import settings


class Task(BaseModel):
    id: int
    title: str
    content: str
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    result: Optional[str] = None
    reflection: Optional[str] = None


class TodoList(BaseModel):
    tasks: List[Task]


class Planner:
    def __init__(self, model: str = "gpt-4"):
        self.llm = ChatOpenAI(
            model=model, temperature=0, api_key=settings.openai_api_key
        )

        self.system_msg = """You are an expert planner. Break down the user's objective into clear, sequential steps.
Each step should be actionable and specific. Do not add any superfluous steps. The result of the final step should be the final answer.
Before finalizing your plan, reflect on whether the steps are necessary, logical, and sufficient to achieve the objective.

Your task:
1. Convert it into a structured TODO list (JSON).
2. Use fields: id, title, content, status.
3. Do NOT execute the tasks.

Do not include any other text or explanations."""

        self.agent = create_agent(
            model=self.llm,
            response_format=TodoList,
            # middleware=[TodoListMiddleware()],
            system_prompt=self.system_msg,
        )

    def create_todo_list(self, objective: str, config) -> TodoList:
        """Create a plan for the given objective"""
        messages = {"messages": [{"role": "user", "content": objective}]}
        result = self.agent.invoke(messages, config)
        return result

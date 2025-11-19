from typing import Dict, List, Literal

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from todo_agent.config import settings


class TaskResult(BaseModel):
    """Contact information for a person."""

    task: str = Field(description="The title of the task")
    status: Literal["completed", "failed"]
    result: str = Field(description="The result returned for the task")
    reflection: str = Field(description="One-line insight, lesson learned,")


class Executor:
    def __init__(self, tools: List[BaseTool], model: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(
            model=model, temperature=0, api_key=settings.openai_api_key
        )
        self.tools = tools

        self.system_msg = """You are a helpful AI assistant that executes tasks step by step.
Use the available tools to complete the given task.
Be concise and focus on getting actionable results. Provide direct answers only. Do not ask follow-up questions or request additional information."""

        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            middleware=[
                ModelCallLimitMiddleware(
                    run_limit=15,
                    exit_behavior="error",
                ),
            ],
            response_format=TaskResult,
            system_prompt=self.system_msg,
        )

    def execute_step(
        self, step_description: str, previous_steps: List[Dict], config
    ) -> Dict:
        """Execute a single step with context from previous steps.

        Args:
            step_description: The current task to execute
            previous_steps: List of completed steps with format:
                [
                    {
                        "id": 1,
                        "title": "Task title",
                        "description": "Task description",
                        "result": "Task result"
                    },
                    ...
                ]
            config: LangGraph configuration dictionary with thread_id

        Returns:
            Dict containing the agent's response with structured_response field
        """
        # Build context from previous steps
        if previous_steps:
            input_text = "Context from previous steps:\n"
            for step in previous_steps:
                input_text += f"Step #{step['id']}: {step['title']}\n"
                input_text += f"Description: {step['description']}\n"
                input_text += f"Result: {step['result']}\n\n"
            input_text += f"Current task to execute: {step_description}"
            # input_text = f"Context from previous steps:\n{context}\n\nCurrent task: {step_description}"
        else:
            input_text = f"Task to execute: {step_description}"
        try:
            messages = {"messages": [{"role": "user", "content": input_text}]}
            result = self.agent.invoke(messages, config)
            return result

        except Exception as e:
            return f"Error executing step: {str(e)}"

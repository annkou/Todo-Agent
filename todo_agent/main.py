import hashlib

from todo_agent.agents.executor import Executor
from todo_agent.agents.planner import Planner
from todo_agent.db import Base, engine
from todo_agent.session_manager import handle_user_input
from todo_agent.tools.search import create_search_tool
from todo_agent.tools.web_scraper import web_scraper


def main():
    # Initialize components
    # db_manager = DatabaseManager("agent_state.db")
    Base.metadata.create_all(engine)
    planner = Planner(model="gpt-4o")
    executor = Executor(model="gpt-4o", tools=[create_search_tool(), web_scraper()])
    objective = input("\n🎯 Enter your objective: ").strip()

    # Encode the string to bytes and create SHA-256 hash
    hash_object = hashlib.sha256(objective.encode("utf-8"))
    # Return the hexadecimal representation
    thread_id = hash_object.hexdigest()
    handle_user_input(
        thread_id=thread_id,
        objective=objective,
        planner_agent=planner,
        executor_agent=executor,
    )


if __name__ == "__main__":
    main()

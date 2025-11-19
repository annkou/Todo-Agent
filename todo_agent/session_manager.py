from typing import Optional

from todo_agent import crud
from todo_agent.agents.executor import Executor
from todo_agent.agents.planner import Planner


def start_new_session(
    thread_id: str, objective: str, planner_agent: Planner, executor_agent: Executor
):
    """
    Start a new session: create plan and store in database.

    Args:
        thread_id: Unique thread identifier
        objective: User's high-level goal
        planner_agent: LangChain planner agent
        executor_agent: LangChain executor agent
    """
    session_id = thread_id
    planner_thread = f"planner-{session_id}"
    executor_thread = f"executor-{session_id}"
    print("🔧 Planning tasks...")

    # Use planner agent to create TODO list
    planner_config = {"configurable": {"thread_id": planner_thread}}
    planner_response = planner_agent.create_todo_list(objective, planner_config)
    todo_list = planner_response["structured_response"].tasks
    print("\nProposed TODO List:")
    tasks = []
    for task in todo_list:
        print(f"- #{task.id} {task.title}: {task.content}")
        tasks.append({"id": task.id, "title": task.title, "content": task.content})

    # Store session and plan in database
    session_data = crud.create_session(thread_id, objective, tasks)
    failed = False
    # Execute each pending task
    for task in todo_list:
        task_id = task.id
        title = task.title

        print(f"\n🔄 Executing task #{task_id}: {title}")

        # Mark as in progress
        crud.update_task_status(thread_id, task_id, "in_progress")

        # Prepare executor config
        executor_config = {"configurable": {"thread_id": executor_thread}}
        # Get completed tasks for context
        completed_steps = crud.get_completed_tasks(thread_id)

        # Execute task with executor agent
        try:
            # Execute with previous steps context
            task_result = executor_agent.execute_step(
                step_description=task.content,
                previous_steps=completed_steps,
                config=executor_config,
            )
            # Only proceed if it's a dict
            if isinstance(task_result, str):
                # It's an error string
                crud.update_task_status(
                    thread_id,
                    task_id,
                    "failed",
                    result=task_result,  # The error message
                    reflection="Executor returned error",
                )
                failed = True
                print(f"❌ Task #{task_id} failed: {task_result}")
                break
            # Update task as completed
            crud.update_task_status(
                thread_id,
                task_id,
                str(task_result["structured_response"].status),
                result=task_result["structured_response"].result,
                reflection=task_result["structured_response"].reflection,
            )

            print(f"→ status: {task_result['structured_response'].status}")
            # print(f"→ result: {task_result['structured_response'].result}")
            print(f"→ reflection: {task_result['structured_response'].reflection}")
            if str(task_result["structured_response"].status) == "failed":
                failed = True
                print("Ending processing objective ...")
                break

        except KeyboardInterrupt:
            # Handle keyboard interruption
            print("\n\nKeyboard interruption detected!")
            failed = True
            # Reset any in_progress tasks back to pending for future resume
            session_data = crud.get_session_by_thread(thread_id)
            for t in session_data["tasks"]:
                if t["status"] == "in_progress":
                    crud.update_task_status(thread_id, t["id"], "pending")
            break

        except Exception as e:
            # Mark as failed
            crud.update_task_status(
                thread_id,
                task_id,
                "failed",
                result=str(e),
                reflection="Task execution failed",
            )
            failed = True
            print(f"Task #{task_id} failed: {str(e)}")
            break

    if not failed:
        # Print final result
        all_completed = crud.get_completed_tasks(thread_id)
        if all_completed:
            last_task = all_completed[-1]
            print("\n📝 FINAL RESULT:")
            print(last_task.get("result", "No result available"))

    # Mark session as complete
    crud.mark_session_complete(thread_id)


def resume_session(thread_id: str, executor_agent: Executor):
    """
    Resume an existing session from database.

    Args:
        thread_id: Existing thread identifier
        executor_agent: Executor agent to continue execution
    """

    session_id = thread_id
    executor_thread = f"executor-{session_id}"
    # Retrieve session from database
    session_data = crud.get_session_by_thread(thread_id)

    print(f"🔄 Resuming objective: {session_data['session']['objective']}")

    # Get tasks by status
    completed = [t for t in session_data["tasks"] if t["status"] == "completed"]
    failed = [t for t in session_data["tasks"] if t["status"] == "failed"]
    pending = [t for t in session_data["tasks"] if t["status"] == "pending"]

    if completed:
        print(f"Already completed: {len(completed)} tasks")

    # Report failed tasks
    if failed:
        print(f"\nFailed tasks: {len(failed)}")
        for task in failed:
            print(f"  Task #{task['id']}: {task['title']}")
            print(f"    → Reason: {task.get('reflection', 'No reflection available')}")
        return

    # Check if all tasks are completed
    if not pending and not failed:
        print("\nAll tasks already completed!")

        # Print final result from last completed task
        if completed:
            last_task = completed[-1]
            print("\n📝 FINAL RESULT:")
            print(last_task.get("result", "No result available"))

    # If there are pending tasks, continue execution
    if pending:
        print(f"\n⏳ Resuming execution: {len(pending)} pending tasks")
        failed = False
        # Execute each pending task
        for task in pending:
            task_id = task["id"]
            title = task["title"]

            print(f"\n🔄 Executing task #{task_id}: {title}")
            # Mark as in progress
            crud.update_task_status(thread_id, task_id, "in_progress")

            # Prepare executor config
            executor_config = {"configurable": {"thread_id": executor_thread}}
            # Get completed tasks for context
            completed_steps = crud.get_completed_tasks(thread_id)
            # Execute task with executor agent
            try:
                # Execute with previous steps context
                task_result = executor_agent.execute_step(
                    step_description=task["content"],
                    previous_steps=completed_steps,
                    config=executor_config,
                )
                # Only proceed if it's a dict
                if isinstance(task_result, str):
                    # It's an error string
                    crud.update_task_status(
                        thread_id,
                        task_id,
                        "failed",
                        result=task_result,  # The error message
                        reflection="Executor returned error",
                    )
                    failed = True
                    print(f"❌ Task #{task_id} failed: {task_result}")
                    break

                # Update task as completed
                crud.update_task_status(
                    thread_id,
                    task_id,
                    str(task_result["structured_response"].status),
                    result=task_result["structured_response"].result,
                    reflection=task_result["structured_response"].reflection,
                )

                print(f"→ status: {task_result['structured_response'].status}")
                # print(f"→ result: {task_result.result}")
                print(f"→ reflection: {task_result['structured_response'].reflection}")
                if str(task_result["structured_response"].status) == "failed":
                    failed = True
                    print("Ending processing objective ...")
                    break

            except KeyboardInterrupt:
                # Handle keyboard interruption
                print("\n\nKeyboard interruption detected!")
                failed = True
                # Reset any in_progress tasks back to pending for future resume
                session_data = crud.get_session_by_thread(thread_id)
                for t in session_data["tasks"]:
                    if t["status"] == "in_progress" and t["id"] != task_id:
                        crud.update_task_status(thread_id, t["id"], "pending")
                break

            except Exception as e:
                # Mark as failed
                crud.update_task_status(
                    thread_id,
                    task_id,
                    "failed",
                    result=str(e),
                    reflection="Task execution failed",
                )
                failed = True
                print(f"Task #{task_id} failed: {str(e)}")
                break

        if not failed:
            # Print final result
            all_completed = crud.get_completed_tasks(thread_id)
            if all_completed:
                last_task = all_completed[-1]
                print("\n📝 FINAL RESULT:")
                print(last_task.get("result", "No result available"))

        crud.mark_session_complete(thread_id)


def handle_user_input(
    thread_id: str, objective: str, planner_agent: Planner, executor_agent: Executor
):
    """
    Main entry point: decide whether to start new or resume session.

    Args:
        thread_id: Thread identifier (can be user-provided or generated)
        objective: User's high-level goal
        planner_agent: LangChain planner agent
        executor_agent: LangChain executor agent
    """
    # Check if session exists
    existing_session = crud.get_session_by_thread(thread_id)

    if existing_session:
        # Session exists
        print("🔄 Resuming existing session...")
        resume_session(thread_id, executor_agent)
    else:
        # New session
        print("✨ Starting new session...")
        start_new_session(thread_id, objective, planner_agent, executor_agent)

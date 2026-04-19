"""
Distributed execution support for AgentMind
Enables running agents across multiple workers using Celery
"""

from typing import Any, Dict, List, Optional
from celery import Celery, Task
from celery.result import AsyncResult
from datetime import datetime


class AgentTask(Task):
    """Custom Celery task for agent execution"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        print(f"Task {task_id} failed: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        print(f"Task {task_id} completed successfully")


def create_celery_app(
    broker_url: str = "redis://localhost:6379/0",
    backend_url: str = "redis://localhost:6379/1",
) -> Celery:
    """Create and configure Celery application"""
    app = Celery(
        "agentmind",
        broker=broker_url,
        backend=backend_url,
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minutes
        task_soft_time_limit=240,  # 4 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=100,
    )

    return app


# Create default Celery app
celery_app = create_celery_app()


@celery_app.task(base=AgentTask, bind=True)
def execute_agent_task(
    self,
    agent_config: Dict[str, Any],
    task_input: str,
    llm_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute an agent task in a distributed worker"""
    from agentmind import Agent, AgentMind
    from agentmind.llm import OllamaProvider, LiteLLMProvider

    try:
        # Initialize LLM provider
        provider_type = llm_config.get("provider", "ollama")
        if provider_type == "ollama":
            llm = OllamaProvider(
                model=llm_config.get("model", "llama3.2"),
                temperature=llm_config.get("temperature", 0.7),
            )
        else:
            llm = LiteLLMProvider(
                model=llm_config.get("model", "gpt-4"),
                temperature=llm_config.get("temperature", 0.7),
            )

        # Create agent
        agent = Agent(
            name=agent_config["name"],
            role=agent_config["role"],
            system_prompt=agent_config["system_prompt"],
        )

        # Create mind and add agent
        mind = AgentMind(llm_provider=llm)
        mind.add_agent(agent)

        # Execute task
        import asyncio

        result = asyncio.run(mind.collaborate(task_input, max_rounds=1))

        return {
            "success": True,
            "result": result,
            "agent": agent_config["name"],
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "agent": agent_config.get("name", "unknown"),
            "timestamp": datetime.now().isoformat(),
        }


@celery_app.task(base=AgentTask)
def execute_collaboration(
    agents_config: List[Dict[str, Any]],
    task_input: str,
    llm_config: Dict[str, Any],
    max_rounds: int = 3,
) -> Dict[str, Any]:
    """Execute multi-agent collaboration in distributed environment"""
    from agentmind import Agent, AgentMind
    from agentmind.llm import OllamaProvider

    try:
        # Initialize LLM
        llm = OllamaProvider(
            model=llm_config.get("model", "llama3.2"),
            temperature=llm_config.get("temperature", 0.7),
        )

        # Create mind
        mind = AgentMind(llm_provider=llm)

        # Add all agents
        for agent_config in agents_config:
            agent = Agent(
                name=agent_config["name"],
                role=agent_config["role"],
                system_prompt=agent_config["system_prompt"],
            )
            mind.add_agent(agent)

        # Execute collaboration
        import asyncio

        result = asyncio.run(mind.collaborate(task_input, max_rounds=max_rounds))

        return {
            "success": True,
            "result": result,
            "agents": [a["name"] for a in agents_config],
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


class DistributedMind:
    """Distributed AgentMind orchestrator using Celery"""

    def __init__(
        self,
        celery_app: Optional[Celery] = None,
        broker_url: str = "redis://localhost:6379/0",
        backend_url: str = "redis://localhost:6379/1",
    ):
        """Initialize distributed mind"""
        self.celery_app = celery_app or create_celery_app(broker_url, backend_url)
        self.tasks: Dict[str, AsyncResult] = {}

    def submit_agent_task(
        self,
        agent_config: Dict[str, Any],
        task_input: str,
        llm_config: Dict[str, Any],
    ) -> str:
        """Submit an agent task for distributed execution"""
        result = execute_agent_task.apply_async(args=[agent_config, task_input, llm_config])
        task_id = result.id
        self.tasks[task_id] = result
        return task_id

    def submit_collaboration(
        self,
        agents_config: List[Dict[str, Any]],
        task_input: str,
        llm_config: Dict[str, Any],
        max_rounds: int = 3,
    ) -> str:
        """Submit a collaboration task for distributed execution"""
        result = execute_collaboration.apply_async(
            args=[agents_config, task_input, llm_config, max_rounds]
        )
        task_id = result.id
        self.tasks[task_id] = result
        return task_id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a submitted task"""
        if task_id not in self.tasks:
            return {"status": "unknown", "task_id": task_id}

        result = self.tasks[task_id]

        return {
            "task_id": task_id,
            "status": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "result": result.result if result.ready() else None,
        }

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Wait for a task to complete and return result"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        result = self.tasks[task_id]
        return result.get(timeout=timeout)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id not in self.tasks:
            return False

        result = self.tasks[task_id]
        result.revoke(terminate=True)
        return True

    def get_all_tasks_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all submitted tasks"""
        return {task_id: self.get_task_status(task_id) for task_id in self.tasks}

    def parallel_execute(
        self,
        agents_config: List[Dict[str, Any]],
        task_input: str,
        llm_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Execute multiple agents in parallel"""
        # Submit all tasks
        task_ids = []
        for agent_config in agents_config:
            task_id = self.submit_agent_task(agent_config, task_input, llm_config)
            task_ids.append(task_id)

        # Wait for all results
        results = []
        for task_id in task_ids:
            try:
                result = self.wait_for_task(task_id, timeout=300)
                results.append(result)
            except Exception as e:
                results.append(
                    {
                        "success": False,
                        "error": str(e),
                        "task_id": task_id,
                    }
                )

        return results


class LoadBalancer:
    """Load balancer for distributing tasks across workers"""

    def __init__(self, distributed_mind: DistributedMind):
        self.mind = distributed_mind
        self.task_queue: List[Dict[str, Any]] = []
        self.active_tasks: Dict[str, str] = {}  # task_id -> agent_name

    def add_task(
        self,
        agent_config: Dict[str, Any],
        task_input: str,
        llm_config: Dict[str, Any],
    ):
        """Add task to queue"""
        self.task_queue.append(
            {
                "agent_config": agent_config,
                "task_input": task_input,
                "llm_config": llm_config,
            }
        )

    def process_queue(self, max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """Process queued tasks with concurrency limit"""
        results = []

        while self.task_queue or self.active_tasks:
            # Submit new tasks up to concurrency limit
            while len(self.active_tasks) < max_concurrent and self.task_queue:
                task = self.task_queue.pop(0)
                task_id = self.mind.submit_agent_task(
                    task["agent_config"], task["task_input"], task["llm_config"]
                )
                self.active_tasks[task_id] = task["agent_config"]["name"]

            # Check for completed tasks
            completed = []
            for task_id in list(self.active_tasks.keys()):
                status = self.mind.get_task_status(task_id)
                if status["ready"]:
                    results.append(status["result"])
                    completed.append(task_id)

            # Remove completed tasks
            for task_id in completed:
                del self.active_tasks[task_id]

            # Small delay to avoid busy waiting
            if self.active_tasks:
                import time

                time.sleep(0.1)

        return results


def start_worker(
    broker_url: str = "redis://localhost:6379/0",
    backend_url: str = "redis://localhost:6379/1",
    concurrency: int = 4,
):
    """Start a Celery worker"""
    app = create_celery_app(broker_url, backend_url)

    worker = app.Worker(
        concurrency=concurrency,
        loglevel="INFO",
        logfile="celery_worker.log",
    )

    worker.start()


if __name__ == "__main__":
    # Start worker
    print("Starting AgentMind Celery worker...")
    start_worker()

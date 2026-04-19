"""
Ray-based distributed execution for AgentMind
Enables parallel agent execution using Ray
"""

from typing import Any, Dict, List, Optional, Callable
import asyncio
from datetime import datetime

try:
    import ray
    from ray import remote
    from ray.util.queue import Queue

    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    print("Ray not installed. Install with: pip install ray")


class RayDistributedMind:
    """Distributed AgentMind orchestrator using Ray"""

    def __init__(
        self,
        num_cpus: Optional[int] = None,
        num_gpus: Optional[int] = None,
        address: Optional[str] = None,
    ):
        """Initialize Ray distributed mind"""
        if not RAY_AVAILABLE:
            raise ImportError("Ray is required for distributed execution")

        # Initialize Ray
        if not ray.is_initialized():
            if address:
                ray.init(address=address)
            else:
                ray.init(num_cpus=num_cpus, num_gpus=num_gpus)

        self.futures: Dict[str, ray.ObjectRef] = {}

    def shutdown(self):
        """Shutdown Ray"""
        if ray.is_initialized():
            ray.shutdown()

    @staticmethod
    @remote
    def execute_agent_remote(
        agent_config: Dict[str, Any],
        task_input: str,
        llm_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute agent task remotely using Ray"""
        from agentmind import Agent, AgentMind
        from agentmind.llm import OllamaProvider

        try:
            # Initialize LLM
            llm = OllamaProvider(
                model=llm_config.get("model", "llama3.2"),
                temperature=llm_config.get("temperature", 0.7),
            )

            # Create agent
            agent = Agent(
                name=agent_config["name"],
                role=agent_config["role"],
                system_prompt=agent_config["system_prompt"],
            )

            # Create mind
            mind = AgentMind(llm_provider=llm)
            mind.add_agent(agent)

            # Execute
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

    @staticmethod
    @remote
    def execute_collaboration_remote(
        agents_config: List[Dict[str, Any]],
        task_input: str,
        llm_config: Dict[str, Any],
        max_rounds: int = 3,
    ) -> Dict[str, Any]:
        """Execute collaboration remotely using Ray"""
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

            # Add agents
            for agent_config in agents_config:
                agent = Agent(
                    name=agent_config["name"],
                    role=agent_config["role"],
                    system_prompt=agent_config["system_prompt"],
                )
                mind.add_agent(agent)

            # Execute
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

    def submit_agent_task(
        self,
        agent_config: Dict[str, Any],
        task_input: str,
        llm_config: Dict[str, Any],
    ) -> str:
        """Submit agent task for distributed execution"""
        future = self.execute_agent_remote.remote(agent_config, task_input, llm_config)
        task_id = str(future)
        self.futures[task_id] = future
        return task_id

    def submit_collaboration(
        self,
        agents_config: List[Dict[str, Any]],
        task_input: str,
        llm_config: Dict[str, Any],
        max_rounds: int = 3,
    ) -> str:
        """Submit collaboration task for distributed execution"""
        future = self.execute_collaboration_remote.remote(
            agents_config, task_input, llm_config, max_rounds
        )
        task_id = str(future)
        self.futures[task_id] = future
        return task_id

    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Get result of a submitted task"""
        if task_id not in self.futures:
            raise ValueError(f"Task {task_id} not found")

        future = self.futures[task_id]
        return ray.get(future, timeout=timeout)

    def parallel_execute(
        self,
        agents_config: List[Dict[str, Any]],
        task_input: str,
        llm_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Execute multiple agents in parallel"""
        # Submit all tasks
        futures = []
        for agent_config in agents_config:
            future = self.execute_agent_remote.remote(agent_config, task_input, llm_config)
            futures.append(future)

        # Wait for all results
        results = ray.get(futures)
        return results

    def map_reduce(
        self,
        agents_config: List[Dict[str, Any]],
        tasks: List[str],
        llm_config: Dict[str, Any],
        reduce_fn: Optional[Callable] = None,
    ) -> Any:
        """Map tasks to agents and optionally reduce results"""
        # Map phase: distribute tasks to agents
        futures = []
        for i, task in enumerate(tasks):
            agent_config = agents_config[i % len(agents_config)]
            future = self.execute_agent_remote.remote(agent_config, task, llm_config)
            futures.append(future)

        # Get all results
        results = ray.get(futures)

        # Reduce phase (optional)
        if reduce_fn:
            return reduce_fn(results)

        return results


class RayActorPool:
    """Pool of Ray actors for persistent agent workers"""

    def __init__(
        self,
        num_actors: int = 4,
        llm_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize actor pool"""
        if not RAY_AVAILABLE:
            raise ImportError("Ray is required for actor pool")

        self.num_actors = num_actors
        self.llm_config = llm_config or {"model": "llama3.2", "temperature": 0.7}
        self.actors = []
        self.task_queue = Queue()

        # Create actors
        for i in range(num_actors):
            actor = AgentActor.remote(self.llm_config)
            self.actors.append(actor)

    def submit_task(self, agent_config: Dict[str, Any], task_input: str) -> ray.ObjectRef:
        """Submit task to actor pool"""
        # Simple round-robin scheduling
        actor = self.actors[len(self.futures) % len(self.actors)]
        future = actor.execute.remote(agent_config, task_input)
        return future

    def shutdown(self):
        """Shutdown all actors"""
        for actor in self.actors:
            ray.kill(actor)


@remote
class AgentActor:
    """Ray actor for persistent agent execution"""

    def __init__(self, llm_config: Dict[str, Any]):
        """Initialize actor with LLM"""
        from agentmind.llm import OllamaProvider

        self.llm = OllamaProvider(
            model=llm_config.get("model", "llama3.2"),
            temperature=llm_config.get("temperature", 0.7),
        )

    def execute(self, agent_config: Dict[str, Any], task_input: str) -> Dict[str, Any]:
        """Execute agent task"""
        from agentmind import Agent, AgentMind

        try:
            # Create agent
            agent = Agent(
                name=agent_config["name"],
                role=agent_config["role"],
                system_prompt=agent_config["system_prompt"],
            )

            # Create mind
            mind = AgentMind(llm_provider=self.llm)
            mind.add_agent(agent)

            # Execute
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


class FaultTolerantExecutor:
    """Fault-tolerant distributed executor with automatic retry"""

    def __init__(
        self,
        distributed_mind: RayDistributedMind,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize fault-tolerant executor"""
        self.mind = distributed_mind
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def execute_with_retry(
        self,
        agent_config: Dict[str, Any],
        task_input: str,
        llm_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute task with automatic retry on failure"""
        import time

        for attempt in range(self.max_retries):
            try:
                task_id = self.mind.submit_agent_task(agent_config, task_input, llm_config)
                result = self.mind.get_result(task_id, timeout=300)

                if result.get("success"):
                    return result

                # Task failed, retry
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2**attempt))  # Exponential backoff

            except Exception as e:
                if attempt == self.max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Failed after {self.max_retries} attempts: {str(e)}",
                        "agent": agent_config.get("name", "unknown"),
                    }
                time.sleep(self.retry_delay * (2**attempt))

        return {
            "success": False,
            "error": "Max retries exceeded",
            "agent": agent_config.get("name", "unknown"),
        }


def create_distributed_mind(
    backend: str = "ray",
    **kwargs,
) -> Any:
    """Factory function to create distributed mind with specified backend"""
    if backend == "ray":
        return RayDistributedMind(**kwargs)
    elif backend == "celery":
        from .celery_backend import DistributedMind

        return DistributedMind(**kwargs)
    else:
        raise ValueError(f"Unknown backend: {backend}")


if __name__ == "__main__":
    # Example usage
    print("Initializing Ray distributed mind...")

    mind = RayDistributedMind()

    # Example agent config
    agent_config = {
        "name": "Researcher",
        "role": "research",
        "system_prompt": "You are a thorough researcher.",
    }

    llm_config = {"model": "llama3.2", "temperature": 0.7}

    # Submit task
    task_id = mind.submit_agent_task(agent_config, "What is AI?", llm_config)
    print(f"Submitted task: {task_id}")

    # Get result
    result = mind.get_result(task_id)
    print(f"Result: {result}")

    # Shutdown
    mind.shutdown()

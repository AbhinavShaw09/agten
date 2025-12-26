from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
import asyncio
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import signal
import sys

from .core import Agent, Message, MessageType, AgentStatus, AgentContext
from .communication import MessageBus, CommunicationProtocol
from .tools import ToolExecutor

logger = logging.getLogger(__name__)


class LifecycleEvent(Enum):
    CREATED = "created"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


@dataclass
class LifecycleState:
    agent_id: str
    event: LifecycleEvent
    timestamp: datetime
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AgentManager:
    def __init__(self, message_bus: Optional[MessageBus] = None):
        self.message_bus = message_bus or MessageBus()
        self.communication = CommunicationProtocol(self.message_bus)
        self.agents: Dict[str, Agent] = {}
        self.agent_contexts: Dict[str, AgentContext] = {}
        self.lifecycle_handlers: Dict[LifecycleEvent, List[Callable]] = {
            event: [] for event in LifecycleEvent
        }
        self._running = False
        self._shutdown_event = asyncio.Event()

    def add_lifecycle_handler(self, event: LifecycleEvent, handler: Callable) -> None:
        self.lifecycle_handlers[event].append(handler)

    async def _emit_lifecycle_event(self, state: LifecycleState) -> None:
        handlers = self.lifecycle_handlers.get(state.event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(state)
                else:
                    handler(state)
            except Exception as e:
                logger.error(f"Lifecycle handler failed for {state.event}: {e}")

    async def create_agent(
        self,
        agent_class: type,
        name: str,
        context: Optional[AgentContext] = None,
        **kwargs,
    ) -> Agent:
        agent = agent_class(name=name, **kwargs)

        if context is None:
            context = AgentContext(session_id=f"session_{agent.id}", tools={})

        await self._emit_lifecycle_event(
            LifecycleState(
                agent_id=agent.id,
                event=LifecycleEvent.CREATED,
                timestamp=datetime.now(),
            )
        )

        await agent.initialize(context)
        self.agents[agent.id] = agent
        self.agent_contexts[agent.id] = context

        await self._emit_lifecycle_event(
            LifecycleState(
                agent_id=agent.id,
                event=LifecycleEvent.INITIALIZED,
                timestamp=datetime.now(),
            )
        )

        self.message_bus.subscribe(agent)

        logger.info(f"Created and initialized agent: {name} ({agent.id})")
        return agent

    async def start_agent(self, agent_id: str) -> None:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

        agent = self.agents[agent_id]
        await agent.start()

        await self._emit_lifecycle_event(
            LifecycleState(
                agent_id=agent_id,
                event=LifecycleEvent.STARTED,
                timestamp=datetime.now(),
            )
        )

        logger.info(f"Started agent: {agent.name}")

    async def stop_agent(self, agent_id: str) -> None:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

        agent = self.agents[agent_id]
        await agent.stop()

        await self._emit_lifecycle_event(
            LifecycleState(
                agent_id=agent_id,
                event=LifecycleEvent.STOPPED,
                timestamp=datetime.now(),
            )
        )

        logger.info(f"Stopped agent: {agent.name}")

    async def destroy_agent(self, agent_id: str) -> None:
        if agent_id not in self.agents:
            return

        await self.stop_agent(agent_id)

        agent = self.agents[agent_id]
        self.message_bus.unsubscribe(agent)

        del self.agents[agent_id]
        del self.agent_contexts[agent_id]

        await self._emit_lifecycle_event(
            LifecycleState(
                agent_id=agent_id,
                event=LifecycleEvent.DESTROYED,
                timestamp=datetime.now(),
            )
        )

        logger.info(f"Destroyed agent: {agent.name}")

    async def start_manager(self) -> None:
        self._running = True

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Agent manager started")

        try:
            await self._run_manager_loop()
        except asyncio.CancelledError:
            logger.info("Agent manager cancelled")
        finally:
            await self.shutdown()

    async def _run_manager_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(0.1)

                for agent_id, agent in list(self.agents.items()):
                    message = await agent.receive_message()
                    if message:
                        await self._handle_agent_message(agent, message)

            except Exception as e:
                logger.error(f"Error in manager loop: {e}")

    async def _handle_agent_message(self, agent: Agent, message: Message) -> None:
        try:
            response = await agent.process_message(message)
            if response:
                await self.communication.publish(response)
        except Exception as e:
            logger.error(f"Error handling message for agent {agent.name}: {e}")

            error_message = Message(
                type=MessageType.ERROR,
                content=f"Message processing failed: {str(e)}",
                sender=agent.id,
                recipient=message.sender,
            )
            await self.communication.publish(error_message)

    async def run_agent_task(
        self, agent_id: str, input_message: str
    ) -> AsyncGenerator[Message, None]:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

        agent = self.agents[agent_id]

        try:
            async for message in agent.run(input_message):
                yield message
        except Exception as e:
            logger.error(f"Agent task failed for {agent.name}: {e}")

            error_message = Message(
                type=MessageType.ERROR,
                content=f"Task execution failed: {str(e)}",
                sender=agent.id,
            )
            yield error_message

    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        if agent_id not in self.agents:
            return None

        agent = self.agents[agent_id]
        return await agent.get_status()

    async def get_all_agents_status(self) -> Dict[str, Dict[str, Any]]:
        status = {}
        for agent_id in self.agents:
            status[agent_id] = await self.get_agent_status(agent_id)
        return status

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.shutdown())

    async def shutdown(self) -> None:
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        logger.info("Shutting down agent manager...")

        tasks = []
        for agent_id in list(self.agents.keys()):
            task = asyncio.create_task(self.destroy_agent(agent_id))
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Agent manager shutdown complete")

    def is_running(self) -> bool:
        return self._running


class AgentOrchestrator:
    def __init__(self, manager: AgentManager):
        self.manager = manager
        self.workflows: Dict[str, Dict[str, Any]] = {}

    def register_workflow(self, name: str, steps: List[Dict[str, Any]]) -> None:
        self.workflows[name] = {"steps": steps, "created_at": datetime.now()}
        logger.info(f"Registered workflow: {name}")

    async def execute_workflow(
        self, workflow_name: str, initial_input: str
    ) -> AsyncGenerator[Message, None]:
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow {workflow_name} not found")

        workflow = self.workflows[workflow_name]
        current_input = initial_input

        for i, step in enumerate(workflow["steps"]):
            agent_name = step["agent"]
            agent_type = step.get("type", "single")

            if agent_type == "single":
                async for message in self.manager.run_agent_task(
                    agent_name, current_input
                ):
                    yield message
                    if message.type == MessageType.RESPONSE:
                        current_input = message.content
                        break
            elif agent_type == "parallel":
                agents = step["agents"]
                tasks = []

                for agent_name in agents:
                    task = asyncio.create_task(
                        self._collect_agent_response(agent_name, current_input)
                    )
                    tasks.append(task)

                responses = await asyncio.gather(*tasks)
                for response in responses:
                    yield response

                if responses:
                    current_input = " ".join(
                        [r.content for r in responses if r.content]
                    )

    async def _collect_agent_response(
        self, agent_id: str, input_message: str
    ) -> Message:
        async for message in self.manager.run_agent_task(agent_id, input_message):
            if message.type == MessageType.RESPONSE:
                return message
        return Message(type=MessageType.ERROR, content="No response received")

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


class MessageType(Enum):
    TASK = "task"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TASK
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    sender: Optional[str] = None
    recipient: Optional[str] = None
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ToolResult:
    tool_call_id: str
    result: Any
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentContext:
    session_id: str
    user_id: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Message] = field(default_factory=list)
    tools: Dict[str, "Tool"] = field(default_factory=dict)


class Tool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any], context: AgentContext) -> Any:
        pass

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters_schema(),
        }

    @abstractmethod
    def _get_parameters_schema(self) -> Dict[str, Any]:
        pass


class Agent(ABC):
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.id = str(uuid.uuid4())
        self.status = AgentStatus.IDLE
        self.context: Optional[AgentContext] = None
        self.tools: Dict[str, Tool] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def initialize(self, context: AgentContext) -> None:
        self.context = context
        self.status = AgentStatus.IDLE
        logger.info(f"Agent {self.name} initialized with context {context.session_id}")

    async def start(self) -> None:
        if not self.context:
            raise ValueError("Agent must be initialized before starting")

        self._running = True
        self.status = AgentStatus.IDLE
        logger.info(f"Agent {self.name} started")

    async def stop(self) -> None:
        self._running = False
        self.status = AgentStatus.COMPLETED
        logger.info(f"Agent {self.name} stopped")

    async def send_message(self, message: Message) -> None:
        await self._message_queue.put(message)

    async def receive_message(self) -> Optional[Message]:
        try:
            message = await asyncio.wait_for(self._message_queue.get(), timeout=0.1)
            return message
        except asyncio.TimeoutError:
            return None

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool
        if self.context:
            self.context.tools[tool.name] = tool

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        if tool_call.name not in self.tools:
            return ToolResult(
                tool_call_id=tool_call.id,
                result=None,
                success=False,
                error=f"Tool '{tool_call.name}' not found",
            )

        tool = self.tools[tool_call.name]
        try:
            self.status = AgentStatus.ACTING
            result = await tool.execute(tool_call.arguments, self.context)
            return ToolResult(tool_call_id=tool_call.id, result=result, success=True)
        except Exception as e:
            logger.error(f"Tool {tool_call.name} execution failed: {e}")
            return ToolResult(
                tool_call_id=tool_call.id, result=None, success=False, error=str(e)
            )
        finally:
            self.status = AgentStatus.IDLE

    @abstractmethod
    async def process_message(self, message: Message) -> Optional[Message]:
        pass

    @abstractmethod
    async def run(self, input_message: str) -> AsyncGenerator[Message, None]:
        pass

    async def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "tools": list(self.tools.keys()),
            "context": {
                "session_id": self.context.session_id if self.context else None,
                "history_length": len(self.context.history) if self.context else 0,
            },
        }

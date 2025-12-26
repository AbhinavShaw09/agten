from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

from .core import Agent, Message, MessageType, AgentStatus, AgentContext

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    messages: List[Message] = None
    current_agent: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.metadata is None:
            self.metadata = {}


class MessageBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Agent]] = {}
        self._conversations: Dict[str, ConversationState] = {}
        self._global_subscribers: List[Agent] = []

    def subscribe(self, agent: Agent, topic: Optional[str] = None) -> None:
        if topic:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(agent)
        else:
            self._global_subscribers.append(agent)

        logger.info(
            f"Agent {agent.name} subscribed to {'global' if not topic else topic}"
        )

    def unsubscribe(self, agent: Agent, topic: Optional[str] = None) -> None:
        if topic and topic in self._subscribers:
            self._subscribers[topic].remove(agent)
        else:
            if agent in self._global_subscribers:
                self._global_subscribers.remove(agent)

        logger.info(
            f"Agent {agent.name} unsubscribed from {'global' if not topic else topic}"
        )

    async def publish(self, message: Message, topic: Optional[str] = None) -> None:
        recipients = []

        if topic and topic in self._subscribers:
            recipients.extend(self._subscribers[topic])

        recipients.extend(self._global_subscribers)

        if message.recipient:
            recipients = [
                agent for agent in recipients if agent.id == message.recipient
            ]

        tasks = []
        for agent in recipients:
            task = asyncio.create_task(agent.send_message(message))
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._update_conversation(message)

    def _update_conversation(self, message: Message) -> None:
        conversation_id = message.metadata.get("conversation_id")
        if not conversation_id:
            return

        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationState()

        state = self._conversations[conversation_id]
        state.messages.append(message)

        if message.sender:
            state.current_agent = message.sender

    def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        return self._conversations.get(conversation_id)

    def get_conversation_history(self, conversation_id: str) -> List[Message]:
        state = self.get_conversation(conversation_id)
        return state.messages if state else []


class CommunicationProtocol:
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus

    async def send_task(
        self,
        sender: Agent,
        recipient_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        message = Message(
            type=MessageType.TASK,
            content=content,
            sender=sender.id,
            recipient=recipient_id,
            metadata=metadata or {},
        )

        await self.message_bus.publish(message)
        return message.id

    async def send_response(
        self,
        sender: Agent,
        recipient_id: str,
        content: str,
        original_message_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        metadata = metadata or {}
        metadata["in_response_to"] = original_message_id

        message = Message(
            type=MessageType.RESPONSE,
            content=content,
            sender=sender.id,
            recipient=recipient_id,
            metadata=metadata,
        )

        await self.message_bus.publish(message)
        return message.id

    async def send_error(
        self,
        sender: Agent,
        recipient_id: str,
        error_message: str,
        original_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        metadata = metadata or {}
        if original_message_id:
            metadata["in_response_to"] = original_message_id

        message = Message(
            type=MessageType.ERROR,
            content=error_message,
            sender=sender.id,
            recipient=recipient_id,
            metadata=metadata,
        )

        await self.message_bus.publish(message)
        return message.id

    async def broadcast_status(
        self,
        sender: Agent,
        status: AgentStatus,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        message = Message(
            type=MessageType.STATUS,
            content=status.value,
            sender=sender.id,
            metadata=metadata or {},
        )

        await self.message_bus.publish(message)
        return message.id

    async def create_conversation(
        self,
        initiator: Agent,
        participants: List[str],
        initial_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        import uuid

        conversation_id = str(uuid.uuid4())

        conv_metadata = metadata or {}
        conv_metadata["conversation_id"] = conversation_id
        conv_metadata["participants"] = participants
        conv_metadata["initiator"] = initiator.id

        await self.send_task(initiator, participants[0], initial_message, conv_metadata)

        return conversation_id

    async def reply_to_conversation(
        self,
        sender: Agent,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        state = self.message_bus.get_conversation(conversation_id)
        if not state:
            raise ValueError(f"Conversation {conversation_id} not found")

        last_message = state.messages[-1] if state.messages else None
        if not last_message:
            raise ValueError("No messages in conversation")

        reply_metadata = metadata or {}
        reply_metadata["conversation_id"] = conversation_id

        return await self.send_response(
            sender, last_message.sender, content, last_message.id, reply_metadata
        )

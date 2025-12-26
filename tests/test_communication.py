import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from agten.communication import MessageBus, CommunicationProtocol, ConversationState
from agten.core import Message, MessageType, Agent, AgentStatus


class TestMessageBus:
    def test_message_bus_initialization(self):
        bus = MessageBus()
        assert len(bus._subscribers) == 0
        assert len(bus._global_subscribers) == 0
        assert len(bus._conversations) == 0

    def test_subscribe_agent(self):
        bus = MessageBus()
        agent = SimpleChatAgent("TestAgent")

        bus.subscribe(agent, "test_topic")

        assert "test_topic" in bus._subscribers
        assert agent in bus._subscribers["test_topic"]

    def test_subscribe_global(self):
        bus = MessageBus()
        agent = SimpleChatAgent("TestAgent")

        bus.subscribe(agent)

        assert agent in bus._global_subscribers

    def test_unsubscribe_agent(self):
        bus = MessageBus()
        agent = SimpleChatAgent("TestAgent")

        bus.subscribe(agent, "test_topic")
        bus.unsubscribe(agent, "test_topic")

        assert agent not in bus._subscribers["test_topic"]

    def test_unsubscribe_global(self):
        bus = MessageBus()
        agent = SimpleChatAgent("TestAgent")

        bus.subscribe(agent)
        bus.unsubscribe(agent)

        assert agent not in bus._global_subscribers

    @pytest.mark.asyncio
    async def test_publish_to_subscribers(self):
        bus = MessageBus()

        agent1 = SimpleChatAgent("Agent1")
        agent2 = SimpleChatAgent("Agent2")

        bus.subscribe(agent1, "test_topic")
        bus.subscribe(agent2, "test_topic")

        message = Message(
            type=MessageType.TASK,
            content="Test message",
            metadata={"topic": "test_topic"},
        )

        await bus.publish(message, "test_topic")

        received1 = await agent1.receive_message()
        received2 = await agent2.receive_message()

        assert received1 is not None
        assert received2 is not None
        assert received1.content == "Test message"
        assert received2.content == "Test message"

    @pytest.mark.asyncio
    async def test_publish_to_recipient(self):
        bus = MessageBus()

        agent1 = SimpleChatAgent("Agent1")
        agent2 = SimpleChatAgent("Agent2")

        bus.subscribe(agent1)
        bus.subscribe(agent2)

        message = Message(
            type=MessageType.TASK, content="Targeted message", recipient=agent2.id
        )

        await bus.publish(message)

        received1 = await agent1.receive_message()
        received2 = await agent2.receive_message()

        assert received1 is None
        assert received2 is not None
        assert received2.content == "Targeted message"

    def test_conversation_state(self):
        bus = MessageBus()

        message = Message(
            type=MessageType.TASK,
            content="Test",
            metadata={"conversation_id": "conv_123"},
        )

        bus._update_conversation(message)

        state = bus.get_conversation("conv_123")
        assert state is not None
        assert len(state.messages) == 1
        assert state.messages[0] == message

    def test_get_conversation_history(self):
        bus = MessageBus()

        message1 = Message(
            type=MessageType.TASK,
            content="Message 1",
            metadata={"conversation_id": "conv_123"},
        )

        message2 = Message(
            type=MessageType.RESPONSE,
            content="Message 2",
            metadata={"conversation_id": "conv_123"},
        )

        bus._update_conversation(message1)
        bus._update_conversation(message2)

        history = bus.get_conversation_history("conv_123")

        assert len(history) == 2
        assert history[0] == message1
        assert history[1] == message2


class TestCommunicationProtocol:
    def test_protocol_initialization(self):
        bus = MessageBus()
        protocol = CommunicationProtocol(bus)

        assert protocol.message_bus == bus

    @pytest.mark.asyncio
    async def test_send_task(self):
        bus = MessageBus()
        protocol = CommunicationProtocol(bus)

        sender = SimpleChatAgent("Sender")
        recipient = SimpleChatAgent("Recipient")

        bus.subscribe(recipient)

        message_id = await protocol.send_task(
            sender, recipient.id, "Test task", {"priority": "high"}
        )

        assert message_id is not None

        received = await recipient.receive_message()
        assert received is not None
        assert received.type == MessageType.TASK
        assert received.content == "Test task"
        assert received.metadata["priority"] == "high"

    @pytest.mark.asyncio
    async def test_send_response(self):
        bus = MessageBus()
        protocol = CommunicationProtocol(bus)

        sender = SimpleChatAgent("Sender")
        recipient = SimpleChatAgent("Recipient")

        bus.subscribe(recipient)

        message_id = await protocol.send_response(
            sender, recipient.id, "Test response", "original_msg_123"
        )

        received = await recipient.receive_message()
        assert received is not None
        assert received.type == MessageType.RESPONSE
        assert received.content == "Test response"
        assert received.metadata["in_response_to"] == "original_msg_123"

    @pytest.mark.asyncio
    async def test_send_error(self):
        bus = MessageBus()
        protocol = CommunicationProtocol(bus)

        sender = SimpleChatAgent("Sender")
        recipient = SimpleChatAgent("Recipient")

        bus.subscribe(recipient)

        message_id = await protocol.send_error(
            sender, recipient.id, "Something went wrong", "original_msg_123"
        )

        received = await recipient.receive_message()
        assert received is not None
        assert received.type == MessageType.ERROR
        assert received.content == "Something went wrong"

    @pytest.mark.asyncio
    async def test_broadcast_status(self):
        bus = MessageBus()
        protocol = CommunicationProtocol(bus)

        sender = SimpleChatAgent("Sender")
        listener1 = SimpleChatAgent("Listener1")
        listener2 = SimpleChatAgent("Listener2")

        bus.subscribe(listener1)
        bus.subscribe(listener2)

        message_id = await protocol.broadcast_status(
            sender, AgentStatus.THINKING, {"task": "processing"}
        )

        received1 = await listener1.receive_message()
        received2 = await listener2.receive_message()

        assert received1 is not None
        assert received2 is not None
        assert received1.type == MessageType.STATUS
        assert received1.content == AgentStatus.THINKING.value

    @pytest.mark.asyncio
    async def test_create_conversation(self):
        bus = MessageBus()
        protocol = CommunicationProtocol(bus)

        initiator = SimpleChatAgent("Initiator")
        participant1 = SimpleChatAgent("Participant1")
        participant2 = SimpleChatAgent("Participant2")

        bus.subscribe(participant1)

        conversation_id = await protocol.create_conversation(
            initiator, [participant1.id, participant2.id], "Hello everyone!"
        )

        assert conversation_id is not None

        received = await participant1.receive_message()
        assert received is not None
        assert received.metadata["conversation_id"] == conversation_id
        assert received.metadata["participants"] == [participant1.id, participant2.id]

    @pytest.mark.asyncio
    async def test_reply_to_conversation(self):
        bus = MessageBus()
        protocol = CommunicationProtocol(bus)

        agent1 = SimpleChatAgent("Agent1")
        agent2 = SimpleChatAgent("Agent2")

        bus.subscribe(agent1)
        bus.subscribe(agent2)

        conversation_id = "conv_123"
        initial_message = Message(
            type=MessageType.TASK,
            content="Initial message",
            sender=agent1.id,
            metadata={"conversation_id": conversation_id},
        )

        bus._update_conversation(initial_message)

        reply_id = await protocol.reply_to_conversation(
            agent2, conversation_id, "Reply to initial message"
        )

        received = await agent1.receive_message()
        assert received is not None
        assert received.type == MessageType.RESPONSE
        assert received.content == "Reply to initial message"
        assert received.metadata["conversation_id"] == conversation_id

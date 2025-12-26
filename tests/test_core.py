import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from agten.core import (
    Agent,
    Tool,
    Message,
    MessageType,
    AgentStatus,
    AgentContext,
    ToolCall,
    ToolResult,
)


class MockTool(Tool):
    def __init__(self, name="mock_tool", description="A mock tool for testing"):
        super().__init__(name, description)

    async def execute(self, arguments, context):
        return f"Mock tool executed with args: {arguments}"

    def _get_parameters_schema(self):
        return {"type": "object", "properties": {"test_param": {"type": "string"}}}


class MockAgent(Agent):
    def __init__(self, name="mock_agent", description="A mock agent for testing"):
        super().__init__(name, description)

    async def process_message(self, message):
        if message.type == MessageType.TASK:
            return Message(
                type=MessageType.RESPONSE,
                content=f"Processed: {message.content}",
                sender=self.id,
                recipient=message.sender,
            )
        return None

    async def run(self, input_message):
        yield Message(
            type=MessageType.STATUS, content="Starting mock agent", sender=self.id
        )

        yield Message(
            type=MessageType.RESPONSE,
            content=f"Mock response to: {input_message}",
            sender=self.id,
        )


class TestTool:
    def test_tool_initialization(self):
        tool = MockTool()
        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"

    def test_tool_schema(self):
        tool = MockTool()
        schema = tool.schema
        assert schema["name"] == "mock_tool"
        assert schema["description"] == "A mock tool for testing"
        assert "parameters" in schema

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        tool = MockTool()
        context = AgentContext(session_id="test")

        result = await tool.execute({"test_param": "value"}, context)
        assert result == "Mock tool executed with args: {'test_param': 'value'}"


class TestMessage:
    def test_message_creation(self):
        message = Message(
            type=MessageType.TASK,
            content="Test message",
            sender="agent1",
            recipient="agent2",
        )

        assert message.type == MessageType.TASK
        assert message.content == "Test message"
        assert message.sender == "agent1"
        assert message.recipient == "agent2"
        assert message.id is not None

    def test_message_with_metadata(self):
        metadata = {"priority": "high", "category": "test"}
        message = Message(
            type=MessageType.TASK, content="Test message", metadata=metadata
        )

        assert message.metadata == metadata


class TestAgent:
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        agent = MockAgent()
        context = AgentContext(session_id="test_session")

        await agent.initialize(context)

        assert agent.context == context
        assert agent.status == AgentStatus.IDLE
        assert agent.id is not None

    @pytest.mark.asyncio
    async def test_agent_start_stop(self):
        agent = MockAgent()
        context = AgentContext(session_id="test_session")

        await agent.initialize(context)
        await agent.start()

        assert agent._running is True
        assert agent.status == AgentStatus.IDLE

        await agent.stop()

        assert agent._running is False
        assert agent.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_agent_tool_registration(self):
        agent = MockAgent()
        tool = MockTool()

        agent.register_tool(tool)

        assert tool.name in agent.tools
        assert agent.tools[tool.name] == tool

    @pytest.mark.asyncio
    async def test_agent_tool_execution(self):
        agent = MockAgent()
        tool = MockTool()
        context = AgentContext(session_id="test_session")

        await agent.initialize(context)
        agent.register_tool(tool)

        tool_call = ToolCall(name="mock_tool", arguments={"test_param": "value"})

        result = await agent.execute_tool(tool_call)

        assert result.success is True
        assert result.result == "Mock tool executed with args: {'test_param': 'value'}"

    @pytest.mark.asyncio
    async def test_agent_tool_execution_not_found(self):
        agent = MockAgent()
        context = AgentContext(session_id="test_session")

        await agent.initialize(context)

        tool_call = ToolCall(name="nonexistent_tool", arguments={})

        result = await agent.execute_tool(tool_call)

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_agent_message_processing(self):
        agent = MockAgent()
        context = AgentContext(session_id="test_session")

        await agent.initialize(context)

        message = Message(type=MessageType.TASK, content="Test task", sender="user")

        response = await agent.process_message(message)

        assert response is not None
        assert response.type == MessageType.RESPONSE
        assert "Processed: Test task" in response.content
        assert response.sender == agent.id
        assert response.recipient == "user"

    @pytest.mark.asyncio
    async def test_agent_run_generator(self):
        agent = MockAgent()
        context = AgentContext(session_id="test_session")

        await agent.initialize(context)

        messages = list(agent.run("Test input"))

        assert len(messages) == 2
        assert messages[0].type == MessageType.STATUS
        assert messages[1].type == MessageType.RESPONSE

    @pytest.mark.asyncio
    async def test_agent_message_queue(self):
        agent = MockAgent()
        context = AgentContext(session_id="test_session")

        await agent.initialize(context)
        await agent.start()

        message = Message(type=MessageType.TASK, content="Test message")

        await agent.send_message(message)
        received = await agent.receive_message()

        assert received is not None
        assert received.content == "Test message"

        await agent.stop()

    @pytest.mark.asyncio
    async def test_agent_get_status(self):
        agent = MockAgent()
        context = AgentContext(session_id="test_session")

        await agent.initialize(context)

        status = await agent.get_status()

        assert status["id"] == agent.id
        assert status["name"] == agent.name
        assert status["status"] == AgentStatus.IDLE.value
        assert "tools" in status
        assert "context" in status

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from agten.registry import AgentRegistry
from agten.core import Agent, Tool


class TestAgentRegistry:
    def test_registry_initialization(self):
        registry = AgentRegistry()
        assert len(registry._agents) == 0
        assert len(registry._tools) == 0
        assert len(registry._agent_instances) == 0

    def test_register_agent(self):
        registry = AgentRegistry()
        registry.register_agent(SimpleChatAgent, "ChatAgent")

        assert "ChatAgent" in registry._agents
        assert registry._agents["ChatAgent"] == SimpleChatAgent

    def test_register_agent_auto_name(self):
        registry = AgentRegistry()
        registry.register_agent(SimpleChatAgent)

        assert "SimpleChatAgent" in registry._agents

    def test_register_agent_invalid_class(self):
        registry = AgentRegistry()

        with pytest.raises(ValueError, match="must inherit from Agent"):
            registry.register_agent(str, "InvalidAgent")

    def test_register_tool(self):
        from agents.tools import BashTool

        registry = AgentRegistry()
        registry.register_tool(BashTool, "Bash")

        assert "Bash" in registry._tools
        assert registry._tools["Bash"] == BashTool

    def test_create_agent(self):
        registry = AgentRegistry()
        registry.register_agent(SimpleChatAgent, "ChatAgent")

        agent = registry.create_agent("ChatAgent", name="TestBot")

        assert agent is not None
        assert isinstance(agent, SimpleChatAgent)
        assert agent.name == "TestBot"
        assert agent.id in registry._agent_instances

    def test_create_agent_not_registered(self):
        registry = AgentRegistry()

        with pytest.raises(ValueError, match="not registered"):
            registry.create_agent("NonExistentAgent")

    def test_get_agent(self):
        registry = AgentRegistry()
        registry.register_agent(SimpleChatAgent, "ChatAgent")

        agent = registry.create_agent("ChatAgent")
        retrieved = registry.get_agent(agent.id)

        assert retrieved == agent

    def test_get_agent_not_found(self):
        registry = AgentRegistry()

        retrieved = registry.get_agent("nonexistent_id")
        assert retrieved is None

    def test_list_agents(self):
        registry = AgentRegistry()
        registry.register_agent(SimpleChatAgent, "ChatAgent")
        registry.register_agent(ToolUsingAgent, "ToolAgent")

        agents = registry.list_agents()

        assert "ChatAgent" in agents
        assert "ToolAgent" in agents
        assert len(agents) == 2

    def test_list_tools(self):
        from agents.tools import BashTool, FileReadTool

        registry = AgentRegistry()
        registry.register_tool(BashTool, "Bash")
        registry.register_tool(FileReadTool, "FileRead")

        tools = registry.list_tools()

        assert "Bash" in tools
        assert "FileRead" in tools
        assert len(tools) == 2

    def test_auto_discover(self, tmp_path):
        registry = AgentRegistry()

        agent_module = tmp_path / "test_agent.py"
        agent_module.write_text("""
from agents.core import Agent

class TestAutoAgent(Agent):
    def __init__(self):
        super().__init__("test", "test agent")
    
    async def process_message(self, message):
        return None
    
    async def run(self, input_message):
        yield
""")

        registry.auto_discover(str(tmp_path))

        assert "TestAutoAgent" in registry.list_agents()

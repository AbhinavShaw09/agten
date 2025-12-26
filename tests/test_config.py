import pytest
import tempfile
import os
from pathlib import Path
from agents.config import (
    ConfigManager, FrameworkConfig, AgentConfig, ToolConfig,
    CommunicationConfig, SecurityConfig, LoggingConfig, ConfigFormat
)
from agents.tools import BashTool, FileReadTool


class TestConfigManager:
    def test_config_manager_initialization(self):
        manager = ConfigManager()
        assert manager.config is not None
        assert isinstance(manager.config, FrameworkConfig)

    def test_config_manager_with_path(self, tmp_path):
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(config_path)
        assert manager.config_path == config_path

    def test_save_and_load_yaml(self, tmp_path):
        manager = ConfigManager()
        
        manager.config.agents["test_agent"] = AgentConfig(
            name="test_agent",
            type="TestAgent",
            description="Test agent for unit testing"
        )
        
        config_path = tmp_path / "test_config.yaml"
        manager.save_config(config_path)
        
        assert config_path.exists()
        
        new_manager = ConfigManager()
        loaded_config = new_manager.load_config(config_path)
        
        assert "test_agent" in loaded_config.agents
        assert loaded_config.agents["test_agent"].type == "TestAgent"

    def test_save_and_load_json(self, tmp_path):
        manager = ConfigManager()
        
        manager.config.tools["test_tool"] = ToolConfig(
            name="test_tool",
            type="TestTool",
            timeout=60.0
        )
        
        config_path = tmp_path / "test_config.json"
        manager.save_config(config_path, ConfigFormat.JSON)
        
        assert config_path.exists()
        
        new_manager = ConfigManager()
        loaded_config = new_manager.load_config(config_path)
        
        assert "test_tool" in loaded_config.tools
        assert loaded_config.tools["test_tool"].timeout == 60.0

    def test_load_nonexistent_file(self):
        manager = ConfigManager()
        
        config = manager.load_config("nonexistent.yaml")
        assert config is not None

    def test_detect_format(self):
        manager = ConfigManager()
        
        assert manager._detect_format(Path("config.yaml")) == ConfigFormat.YAML
        assert manager._detect_format(Path("config.yml")) == ConfigFormat.YAML
        assert manager._detect_format(Path("config.json")) == ConfigFormat.JSON
        assert manager._detect_format(Path("config.txt")) is None

    def test_parse_config(self):
        manager = ConfigManager()
        
        data = {
            "agents": {
                "test_agent": {
                    "name": "test_agent",
                    "type": "TestAgent",
                    "timeout": 120.0
                }
            },
            "communication": {
                "max_message_size": 2048
            }
        }
        
        config = manager._parse_config(data)
        
        assert "test_agent" in config.agents
        assert config.agents["test_agent"].timeout == 120.0
        assert config.communication.max_message_size == 2048

    def test_get_agent_config(self):
        manager = ConfigManager()
        
        manager.config.agents["test_agent"] = AgentConfig(
            name="test_agent",
            type="TestAgent"
        )
        
        agent_config = manager.get_agent_config("test_agent")
        assert agent_config is not None
        assert agent_config.name == "test_agent"

    def test_get_tool_config(self):
        manager = ConfigManager()
        
        manager.config.tools["test_tool"] = ToolConfig(
            name="test_tool",
            type="TestTool"
        )
        
        tool_config = manager.get_tool_config("test_tool")
        assert tool_config is not None
        assert tool_config.name == "test_tool"

    def test_add_agent_config(self):
        manager = ConfigManager()
        
        agent_config = AgentConfig(
            name="new_agent",
            type="NewAgent"
        )
        
        manager.add_agent_config(agent_config)
        
        assert "new_agent" in manager.config.agents
        assert manager.config.agents["new_agent"] == agent_config

    def test_add_tool_config(self):
        manager = ConfigManager()
        
        tool_config = ToolConfig(
            name="new_tool",
            type="NewTool"
        )
        
        manager.add_tool_config(tool_config)
        
        assert "new_tool" in manager.config.tools
        assert manager.config.tools["new_tool"] == tool_config

    def test_remove_agent_config(self):
        manager = ConfigManager()
        
        manager.config.agents["test_agent"] = AgentConfig(
            name="test_agent",
            type="TestAgent"
        )
        
        removed = manager.remove_agent_config("test_agent")
        
        assert removed is True
        assert "test_agent" not in manager.config.agents

    def test_remove_agent_config_not_found(self):
        manager = ConfigManager()
        
        removed = manager.remove_agent_config("nonexistent")
        
        assert removed is False

    def test_update_agent_config(self):
        manager = ConfigManager()
        
        manager.config.agents["test_agent"] = AgentConfig(
            name="test_agent",
            type="TestAgent",
            timeout: 30.0
        )
        
        updated = manager.update_agent_config("test_agent", timeout=60.0)
        
        assert updated is True
        assert manager.config.agents["test_agent"].timeout == 60.0

    def test_merge_environment(self):
        manager = ConfigManager()
        
        manager.config.global_environment = {"GLOBAL": "value"}
        manager.config.agents["agent1"] = AgentConfig(
            name="agent1",
            type="Agent1",
            environment={"AGENT1": "specific"}
        )
        manager.config.agents["agent2"] = AgentConfig(
            name="agent2",
            type="Agent2"
        )
        
        env = manager.merge_environment()
        
        assert env["GLOBAL"] == "value"
        assert env["AGENT1"] == "specific"

    def test_apply_environment(self):
        manager = ConfigManager()
        
        manager.config.global_environment = {"TEST_VAR": "test_value"}
        
        original_value = os.environ.get("TEST_VAR")
        manager.apply_environment()
        
        assert os.environ["TEST_VAR"] == "test_value"
        
        if original_value is None:
            del os.environ["TEST_VAR"]
        else:
            os.environ["TEST_VAR"] = original_value

    def test_add_config_watcher(self):
        manager = ConfigManager()
        
        def test_watcher(config):
            pass
        
        manager.add_config_watcher(test_watcher)
        
        assert test_watcher in manager._watchers

    def test_remove_config_watcher(self):
        manager = ConfigManager()
        
        def test_watcher(config):
            pass
        
        manager.add_config_watcher(test_watcher)
        manager.remove_config_watcher(test_watcher)
        
        assert test_watcher not in manager._watchers

    def test_validate_config_valid(self):
        manager = ConfigManager()
        
        manager.config.agents["valid_agent"] = AgentConfig(
            name="valid_agent",
            type="ValidAgent",
            max_concurrent_tasks=1
        )
        
        manager.config.tools["valid_tool"] = ToolConfig(
            name="valid_tool",
            type="ValidTool",
            timeout=30.0
        )
        
        errors = manager.validate_config()
        assert len(errors) == 0

    def test_validate_config_invalid(self):
        manager = ConfigManager()
        
        manager.config.agents["invalid_agent"] = AgentConfig(
            name="",
            type="InvalidAgent",
            max_concurrent_tasks=0
        )
        
        manager.config.tools["invalid_tool"] = ToolConfig(
            name="invalid_tool",
            type="",
            timeout=-1.0
        )
        
        errors = manager.validate_config()
        assert len(errors) > 0
        assert any("name is required" in error for error in errors)
        assert any("must be >= 1" in error for error in errors)


class TestAgentConfig:
    def test_agent_config_creation(self):
        config = AgentConfig(
            name="test_agent",
            type="TestAgent",
            description="Test agent",
            timeout=60.0
        )
        
        assert config.name == "test_agent"
        assert config.type == "TestAgent"
        assert config.description == "Test agent"
        assert config.timeout == 60.0
        assert config.enabled is True
        assert config.max_concurrent_tasks == 1

    def test_agent_config_defaults(self):
        config = AgentConfig(name="test", type="Test")
        
        assert config.description == ""
        assert config.enabled is True
        assert config.max_concurrent_tasks == 1
        assert config.timeout == 30.0
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0


class TestToolConfig:
    def test_tool_config_creation(self):
        config = ToolConfig(
            name="test_tool",
            type="TestTool",
            timeout=120.0,
            max_memory_mb=1024
        )
        
        assert config.name == "test_tool"
        assert config.type == "TestTool"
        assert config.timeout == 120.0
        assert config.max_memory_mb == 1024
        assert config.enabled is True

    def test_tool_config_defaults(self):
        config = ToolConfig(name="test", type="Test")
        
        assert config.enabled is True
        assert config.timeout == 30.0
        assert config.max_memory_mb == 512
        assert config.require_confirmation is False


class TestCommunicationConfig:
    def test_communication_config_defaults(self):
        config = CommunicationConfig()
        
        assert config.message_bus_type == "memory"
        assert config.max_message_size == 1024 * 1024
        assert config.message_retention_time == 3600.0
        assert config.max_conversation_length == 1000


class TestSecurityConfig:
    def test_security_config_defaults(self):
        config = SecurityConfig()
        
        assert config.enable_sandbox is True
        assert config.max_file_size_mb == 100
        assert config.require_auth is False


class TestLoggingConfig:
    def test_logging_config_defaults(self):
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert config.enable_console is True
        assert config.max_file_size_mb == 10
        assert config.backup_count == 5
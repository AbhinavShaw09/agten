from typing import Any, Dict, List, Optional, Union, Type
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml
import json
import os
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigFormat(Enum):
    YAML = "yaml"
    JSON = "json"
    ENV = "env"


@dataclass
class AgentConfig:
    name: str
    type: str
    description: str = ""
    enabled: bool = True
    max_concurrent_tasks: int = 1
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    tools: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolConfig:
    name: str
    type: str
    enabled: bool = True
    timeout: float = 30.0
    max_memory_mb: int = 512
    allowed_paths: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    require_confirmation: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommunicationConfig:
    message_bus_type: str = "memory"
    max_message_size: int = 1024 * 1024
    message_retention_time: float = 3600.0
    max_conversation_length: int = 1000


@dataclass
class SecurityConfig:
    enable_sandbox: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    max_file_size_mb: int = 100
    allowed_file_extensions: List[str] = field(default_factory=list)
    require_auth: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size_mb: int = 10
    backup_count: int = 5
    enable_console: bool = True


@dataclass
class FrameworkConfig:
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    tools: Dict[str, ToolConfig] = field(default_factory=dict)
    communication: CommunicationConfig = field(default_factory=CommunicationConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    global_environment: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = Path(config_path) if config_path else None
        self.config = FrameworkConfig()
        self._watchers: List[callable] = []

    def load_config(
        self,
        config_path: Optional[Union[str, Path]] = None,
        format: Optional[ConfigFormat] = None,
    ) -> FrameworkConfig:
        path = Path(config_path) if config_path else self.config_path

        if not path or not path.exists():
            logger.warning(f"Config file not found: {path}, using defaults")
            return self.config

        if format is None:
            format = self._detect_format(path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                if format == ConfigFormat.YAML:
                    data = yaml.safe_load(f)
                elif format == ConfigFormat.JSON:
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported format: {format}")

            self.config = self._parse_config(data)
            logger.info(f"Loaded config from {path}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            raise

    def save_config(
        self,
        config_path: Optional[Union[str, Path]] = None,
        format: Optional[ConfigFormat] = None,
    ) -> None:
        path = Path(config_path) if config_path else self.config_path

        if not path:
            raise ValueError("No config path specified")

        path.parent.mkdir(parents=True, exist_ok=True)

        if format is None:
            format = self._detect_format(path) or ConfigFormat.YAML

        data = asdict(self.config)

        try:
            with open(path, "w", encoding="utf-8") as f:
                if format == ConfigFormat.YAML:
                    yaml.dump(data, f, default_flow_style=False, indent=2)
                elif format == ConfigFormat.JSON:
                    json.dump(data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported format: {format}")

            logger.info(f"Saved config to {path}")

        except Exception as e:
            logger.error(f"Failed to save config to {path}: {e}")
            raise

    def _detect_format(self, path: Path) -> Optional[ConfigFormat]:
        suffix = path.suffix.lower()
        if suffix in [".yaml", ".yml"]:
            return ConfigFormat.YAML
        elif suffix == ".json":
            return ConfigFormat.JSON
        return None

    def _parse_config(self, data: Dict[str, Any]) -> FrameworkConfig:
        config = FrameworkConfig()

        if "agents" in data:
            for name, agent_data in data["agents"].items():
                config.agents[name] = AgentConfig(**agent_data)

        if "tools" in data:
            for name, tool_data in data["tools"].items():
                config.tools[name] = ToolConfig(**tool_data)

        if "communication" in data:
            config.communication = CommunicationConfig(**data["communication"])

        if "security" in data:
            config.security = SecurityConfig(**data["security"])

        if "logging" in data:
            config.logging = LoggingConfig(**data["logging"])

        if "global_environment" in data:
            config.global_environment = data["global_environment"]

        if "metadata" in data:
            config.metadata = data["metadata"]

        return config

    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        return self.config.agents.get(agent_name)

    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        return self.config.tools.get(tool_name)

    def add_agent_config(self, agent_config: AgentConfig) -> None:
        self.config.agents[agent_config.name] = agent_config

    def add_tool_config(self, tool_config: ToolConfig) -> None:
        self.config.tools[tool_config.name] = tool_config

    def remove_agent_config(self, agent_name: str) -> bool:
        return self.config.agents.pop(agent_name, None) is not None

    def remove_tool_config(self, tool_name: str) -> bool:
        return self.config.tools.pop(tool_name, None) is not None

    def update_agent_config(self, agent_name: str, **kwargs) -> bool:
        if agent_name not in self.config.agents:
            return False

        config = self.config.agents[agent_name]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return True

    def update_tool_config(self, tool_name: str, **kwargs) -> bool:
        if tool_name not in self.config.tools:
            return False

        config = self.config.tools[tool_name]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return True

    def merge_environment(self) -> Dict[str, str]:
        env = dict(self.config.global_environment)

        for agent_config in self.config.agents.values():
            env.update(agent_config.environment)

        return env

    def apply_environment(self) -> None:
        env = self.merge_environment()

        for key, value in env.items():
            if not os.environ.get(key):
                os.environ[key] = value

        logger.info(f"Applied {len(env)} environment variables")

    def add_config_watcher(self, callback: callable) -> None:
        self._watchers.append(callback)

    def remove_config_watcher(self, callback: callable) -> None:
        if callback in self._watchers:
            self._watchers.remove(callback)

    async def watch_config(self, interval: float = 1.0) -> None:
        if not self.config_path:
            logger.warning("No config path to watch")
            return

        last_modified = self.config_path.stat().st_mtime

        while True:
            try:
                current_modified = self.config_path.stat().st_mtime
                if current_modified > last_modified:
                    logger.info("Config file changed, reloading...")
                    self.load_config()

                    for watcher in self._watchers:
                        try:
                            if asyncio.iscoroutinefunction(watcher):
                                await watcher(self.config)
                            else:
                                watcher(self.config)
                        except Exception as e:
                            logger.error(f"Config watcher failed: {e}")

                    last_modified = current_modified

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Error watching config: {e}")
                await asyncio.sleep(interval)

    def validate_config(self) -> List[str]:
        errors = []

        for name, agent_config in self.config.agents.items():
            if not agent_config.name:
                errors.append(f"Agent {name}: name is required")
            if not agent_config.type:
                errors.append(f"Agent {name}: type is required")
            if agent_config.max_concurrent_tasks < 1:
                errors.append(f"Agent {name}: max_concurrent_tasks must be >= 1")

        for name, tool_config in self.config.tools.items():
            if not tool_config.name:
                errors.append(f"Tool {name}: name is required")
            if not tool_config.type:
                errors.append(f"Tool {name}: type is required")
            if tool_config.timeout < 0:
                errors.append(f"Tool {name}: timeout must be >= 0")

        if self.config.communication.max_message_size <= 0:
            errors.append("Communication max_message_size must be > 0")

        if self.config.security.max_file_size_mb <= 0:
            errors.append("Security max_file_size_mb must be > 0")

        return errors

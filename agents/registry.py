from typing import Any, Dict, List, Optional, Type
import importlib
import inspect
from pathlib import Path
import logging

from .core import Agent, Tool, AgentContext

logger = logging.getLogger(__name__)


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Type[Agent]] = {}
        self._tools: Dict[str, Type[Tool]] = {}
        self._agent_instances: Dict[str, Agent] = {}

    def register_agent(
        self, agent_class: Type[Agent], name: Optional[str] = None
    ) -> None:
        agent_name = name or agent_class.__name__
        if not issubclass(agent_class, Agent):
            raise ValueError(f"Class {agent_class.__name__} must inherit from Agent")

        self._agents[agent_name] = agent_class
        logger.info(f"Registered agent: {agent_name}")

    def register_tool(self, tool_class: Type[Tool], name: Optional[str] = None) -> None:
        tool_name = name or tool_class.__name__
        if not issubclass(tool_class, Tool):
            raise ValueError(f"Class {tool_class.__name__} must inherit from Tool")

        self._tools[tool_name] = tool_class
        logger.info(f"Registered tool: {tool_name}")

    def create_agent(self, agent_name: str, **kwargs) -> Agent:
        if agent_name not in self._agents:
            raise ValueError(f"Agent '{agent_name}' not registered")

        agent_class = self._agents[agent_name]
        instance = agent_class(**kwargs)
        self._agent_instances[instance.id] = instance
        return instance

    def create_tool(self, tool_name: str, **kwargs) -> Tool:
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not registered")

        tool_class = self._tools[tool_name]
        return tool_class(**kwargs)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._agent_instances.get(agent_id)

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def auto_discover(self, package_path: str) -> None:
        path = Path(package_path)
        if not path.exists():
            logger.warning(f"Package path {package_path} does not exist")
            return

        for module_file in path.rglob("*.py"):
            if module_file.name.startswith("__"):
                continue

            module_path = module_file.relative_to(path.parent)
            module_name = str(module_path.with_suffix("")).replace("/", ".")

            try:
                self._load_module(module_name)
            except Exception as e:
                logger.error(f"Failed to load module {module_name}: {e}")

    def _load_module(self, module_name: str) -> None:
        try:
            module = importlib.import_module(module_name)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if inspect.ismodule(obj) or obj.__module__ != module_name:
                    continue

                if issubclass(obj, Agent) and obj != Agent:
                    self.register_agent(obj)
                elif issubclass(obj, Tool) and obj != Tool:
                    self.register_tool(obj)

        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")


registry = AgentRegistry()

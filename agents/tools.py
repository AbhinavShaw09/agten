from typing import Any, Dict, List, Optional, Callable
import asyncio
import subprocess
import time
import psutil
import logging
from dataclasses import dataclass, field

from .core import Tool, AgentContext, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class ToolConfig:
    timeout: float = 30.0
    max_memory_mb: int = 512
    allowed_paths: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    require_confirmation: bool = False


class ToolExecutor:
    def __init__(self, config: Optional[ToolConfig] = None):
        self.config = config or ToolConfig()
        self._running_tools: Dict[str, asyncio.Task] = {}
        self._tool_processes: Dict[str, psutil.Process] = {}

    async def execute_tool(
        self, tool: Tool, arguments: Dict[str, Any], context: AgentContext
    ) -> ToolResult:
        tool_id = f"{tool.name}_{int(time.time())}"

        try:
            task = asyncio.create_task(
                self._execute_with_limits(tool, arguments, context, tool_id)
            )
            self._running_tools[tool_id] = task

            result = await asyncio.wait_for(task, timeout=self.config.timeout)
            return result

        except asyncio.TimeoutError:
            await self._cleanup_tool(tool_id)
            return ToolResult(
                tool_call_id=tool_id,
                result=None,
                success=False,
                error=f"Tool execution timed out after {self.config.timeout} seconds",
            )
        except Exception as e:
            await self._cleanup_tool(tool_id)
            return ToolResult(
                tool_call_id=tool_id,
                result=None,
                success=False,
                error=f"Tool execution failed: {str(e)}",
            )
        finally:
            self._running_tools.pop(tool_id, None)

    async def _execute_with_limits(
        self, tool: Tool, arguments: Dict[str, Any], context: AgentContext, tool_id: str
    ) -> ToolResult:
        if isinstance(tool, BashTool):
            return await self._execute_bash_tool(tool, arguments, context, tool_id)
        else:
            return await tool.execute(arguments, context)

    async def _execute_bash_tool(
        self, tool: Tool, arguments: Dict[str, Any], context: AgentContext, tool_id: str
    ) -> ToolResult:
        command = arguments.get("command", "")
        if not command:
            return ToolResult(
                tool_call_id=tool_id,
                result=None,
                success=False,
                error="No command provided",
            )

        if self._is_blocked_command(command):
            return ToolResult(
                tool_call_id=tool_id,
                result=None,
                success=False,
                error=f"Command '{command}' is not allowed",
            )

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._get_working_directory(context),
            )

            self._tool_processes[tool_id] = psutil.Process(process.pid)

            stdout, stderr = await process.communicate()

            result = {
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "returncode": process.returncode,
            }

            return ToolResult(
                tool_call_id=tool_id, result=result, success=process.returncode == 0
            )

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_id,
                result=None,
                success=False,
                error=f"Command execution failed: {str(e)}",
            )
        finally:
            self._tool_processes.pop(tool_id, None)

    def _is_blocked_command(self, command: str) -> bool:
        command_lower = command.lower()
        for blocked in self.config.blocked_commands:
            if blocked.lower() in command_lower:
                return True
        return False

    def _get_working_directory(self, context: AgentContext) -> str:
        return context.variables.get("working_directory", ".")

    async def _cleanup_tool(self, tool_id: str) -> None:
        if tool_id in self._running_tools:
            task = self._running_tools[tool_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if tool_id in self._tool_processes:
            process = self._tool_processes[tool_id]
            try:
                process.terminate()
                await asyncio.sleep(1)
                if process.is_running():
                    process.kill()
            except psutil.NoSuchProcess:
                pass

    async def get_resource_usage(self) -> Dict[str, Any]:
        usage = {}
        for tool_id, process in self._tool_processes.items():
            try:
                usage[tool_id] = {
                    "cpu_percent": process.cpu_percent(),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "status": process.status(),
                }
            except psutil.NoSuchProcess:
                usage[tool_id] = {"status": "terminated"}
        return usage

    async def cancel_all_tools(self) -> None:
        for tool_id in list(self._running_tools.keys()):
            await self._cleanup_tool(tool_id)


class BashTool(Tool):
    def __init__(self, executor: Optional[ToolExecutor] = None):
        super().__init__("bash", "Execute bash commands with safety limits")
        self.executor = executor or ToolExecutor()

    async def execute(self, arguments: Dict[str, Any], context: AgentContext) -> Any:
        return await self.executor.execute_tool(self, arguments, context)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional)",
                },
            },
            "required": ["command"],
        }


class FileReadTool(Tool):
    def __init__(self):
        super().__init__("file_read", "Read file contents")

    async def execute(self, arguments: Dict[str, Any], context: AgentContext) -> Any:
        file_path = arguments.get("path", "")
        if not file_path:
            raise ValueError("File path is required")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return {"content": content, "size": len(content), "path": file_path}
        except Exception as e:
            raise RuntimeError(f"Failed to read file {file_path}: {str(e)}")

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"}
            },
            "required": ["path"],
        }


class FileWriteTool(Tool):
    def __init__(self):
        super().__init__("file_write", "Write content to a file")

    async def execute(self, arguments: Dict[str, Any], context: AgentContext) -> Any:
        file_path = arguments.get("path", "")
        content = arguments.get("content", "")

        if not file_path:
            raise ValueError("File path is required")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {"path": file_path, "size": len(content), "success": True}
        except Exception as e:
            raise RuntimeError(f"Failed to write file {file_path}: {str(e)}")

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        }

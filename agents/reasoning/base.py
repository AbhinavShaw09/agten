from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from abc import ABC, abstractmethod

from ..core import AgentContext, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class ReasoningStep(Enum):
    ANALYZE = "analyze"
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"
    CORRECT = "correct"
    COMPLETE = "complete"


@dataclass
class Thought:
    step: ReasoningStep
    content: str
    confidence: float = 1.0
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())


@dataclass
class Plan:
    objective: str
    steps: List[str]
    required_tools: List[str]
    estimated_time: Optional[float] = None
    success_criteria: Optional[str] = None


class ReasoningEngine(ABC):
    def __init__(self, model_name: str = "google_genai:gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.model = None

    async def initialize(self):
        from langchain.chat_models import init_chat_model

        self.model = init_chat_model(self.model_name)

    @abstractmethod
    async def analyze_request(self, request: str, context: AgentContext) -> Thought:
        pass

    @abstractmethod
    async def create_plan(
        self, request: str, analysis: Thought, context: AgentContext
    ) -> Plan:
        pass

    @abstractmethod
    async def select_tools(
        self, plan: Plan, current_step: str, context: AgentContext
    ) -> List[ToolCall]:
        pass

    @abstractmethod
    async def execute_step(
        self, tool_calls: List[ToolCall], context: AgentContext
    ) -> List[ToolResult]:
        pass

    @abstractmethod
    async def reflect(
        self, plan: Plan, step_results: List[ToolResult], context: AgentContext
    ) -> Thought:
        pass

    @abstractmethod
    async def should_continue(
        self, plan: Plan, current_results: List[ToolResult], context: AgentContext
    ) -> Tuple[bool, Optional[str]]:
        pass


class CoTReasoningEngine(ReasoningEngine):
    async def analyze_request(self, request: str, context: AgentContext) -> Thought:
        prompt = f"""
Analyze this user request and identify:
1. What the user wants to accomplish
2. What information is needed
3. What tools might be required
4. Any constraints or special considerations

Request: "{request}"

Provide a detailed analysis:
"""

        response = await self.model.ainvoke(prompt)

        return Thought(
            step=ReasoningStep.ANALYZE,
            content=response.content,
            metadata={"request": request},
        )

    async def create_plan(
        self, request: str, analysis: Thought, context: AgentContext
    ) -> Plan:
        prompt = f"""
Based on this analysis, create a step-by-step plan to accomplish the user's request.

Request: "{request}"
Analysis: {analysis.content}

Create a plan with:
1. Clear sequential steps
2. Tools needed for each step
3. Success criteria
4. Estimated completion approach

Plan format:
- Step 1: [description]
- Step 2: [description]
- etc.
"""

        response = await self.model.ainvoke(prompt)

        steps = []
        for line in response.content.split("\n"):
            if line.strip().startswith("- Step"):
                step_desc = line.split(":", 1)[-1].strip()
                steps.append(step_desc)

        return Plan(
            objective=request,
            steps=steps,
            required_tools=self._extract_needed_tools(response.content),
            success_criteria="Plan completed successfully",
        )

    async def select_tools(
        self, plan: Plan, current_step: str, context: AgentContext
    ) -> List[ToolCall]:
        prompt = f"""
For this step, determine what tools are needed and their exact parameters:

Current step: "{current_step}"
Available tools: {list(context.tools.keys())}

If tools are needed, specify:
1. Tool name
2. Exact parameters 
3. Expected output

If no tools needed, say "No tools required for this step"
"""

        response = await self.model.ainvoke(prompt)

        tool_calls = []
        if "No tools required" not in response.content:
            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response.content)

        return tool_calls

    async def execute_step(
        self, tool_calls: List[ToolCall], context: AgentContext
    ) -> List[ToolResult]:
        results = []

        for tool_call in tool_calls:
            if tool_call.name not in context.tools:
                results.append(
                    ToolResult(
                        tool_call_id=tool_call.id,
                        result=None,
                        success=False,
                        error=f"Tool '{tool_call.name}' not available",
                    )
                )
                continue

            try:
                tool = context.tools[tool_call.name]
                result = await tool.execute(tool_call.arguments, context)
                results.append(
                    ToolResult(tool_call_id=tool_call.id, result=result, success=True)
                )
            except Exception as e:
                results.append(
                    ToolResult(
                        tool_call_id=tool_call.id,
                        result=None,
                        success=False,
                        error=str(e),
                    )
                )

        return results

    async def reflect(
        self, plan: Plan, step_results: List[ToolResult], context: AgentContext
    ) -> Thought:
        successful_results = [r for r in step_results if r.success]
        failed_results = [r for r in step_results if not r.success]

        prompt = f"""
Reflect on the execution results and determine next actions:

Plan objective: {plan.objective}
Successful tool executions: {len(successful_results)}
Failed tool executions: {len(failed_results)}

Results summary:
{self._format_results(step_results)}

Reflection:
1. What was accomplished?
2. What went wrong?
3. What should be done next?
4. Are we closer to the goal?
"""

        response = await self.model.ainvoke(prompt)

        return Thought(
            step=ReasoningStep.REFLECT,
            content=response.content,
            tool_results=step_results,
            confidence=len(successful_results) / len(step_results)
            if step_results
            else 0.0,
        )

    async def should_continue(
        self, plan: Plan, current_results: List[ToolResult], context: AgentContext
    ) -> Tuple[bool, Optional[str]]:
        prompt = f"""
Based on the current progress, determine if the plan is complete or should continue:

Original objective: {plan.objective}
Completed steps: (determine from results)
Remaining work needed: (assess from results)

Answer with either:
- CONTINUE: [what to do next]
- COMPLETE: [final answer for user]

Consider: Are all requirements met? Is the user's request fully satisfied?
"""

        response = await self.model.ainvoke(prompt)

        if "COMPLETE:" in response.content:
            final_answer = response.content.split("COMPLETE:", 1)[1].strip()
            return False, final_answer
        else:
            next_action = (
                response.content.split("CONTINUE:", 1)[1].strip()
                if "CONTINUE:" in response.content
                else "Continue with next step"
            )
            return True, next_action

    def _extract_needed_tools(self, content: str) -> List[str]:
        common_tools = [
            "bash",
            "file_read",
            "file_write",
            "weather",
            "search",
            "calculator",
        ]
        tools = []
        for tool in common_tools:
            if tool.lower() in content.lower():
                tools.append(tool)
        return tools

    def _parse_tool_calls(self, content: str) -> List[ToolCall]:
        tool_calls = []

        if "bash" in content.lower():
            lines = content.split("\n")
            for line in lines:
                if "command:" in line.lower():
                    command = line.split("command:", 1)[1].strip().strip('"')
                    tool_calls.append(
                        ToolCall(name="bash", arguments={"command": command})
                    )

        return tool_calls

    def _format_results(self, results: List[ToolResult]) -> str:
        formatted = []
        for result in results:
            if result.success:
                formatted.append(f"✅ {result.tool_call_id}: Success")
            else:
                formatted.append(f"❌ {result.tool_call_id}: {result.error}")
        return "\n".join(formatted)

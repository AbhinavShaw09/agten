from typing import Any, Dict, List, Optional, AsyncGenerator
import asyncio
import logging

from ..core import (
    Agent,
    Message,
    MessageType,
    AgentStatus,
    ToolCall,
    ToolResult,
    AgentContext,
)
from ..tools import BashTool, FileReadTool, FileWriteTool
from .base import CoTReasoningEngine, Thought, Plan, ReasoningStep

logger = logging.getLogger(__name__)


class ReasoningAgent(Agent):
    def __init__(
        self,
        name: str = "ReasoningAgent",
        model_name: str = "google_genai:gemini-2.5-flash-lite",
    ):
        super().__init__(name, "An agent with reasoning capabilities")
        self.model_name = model_name
        self.reasoning_engine = CoTReasoningEngine(model_name)
        self.current_plan: Optional[Plan] = None
        self.reasoning_history: List[Thought] = []
        self.max_reasoning_steps = 20
        self.step_timeout = 300.0

    async def initialize(self, context: AgentContext) -> None:
        await super().initialize(context)
        await self.reasoning_engine.initialize()

        self.register_tool(BashTool())
        self.register_tool(FileReadTool())
        self.register_tool(FileWriteTool())

    async def process_message(self, message: Message) -> Optional[Message]:
        if message.type == MessageType.TASK:
            try:
                async for response in self._reason_about_task(message.content):
                    if response.type == MessageType.RESPONSE:
                        return response
                    elif response.type == MessageType.STATUS:
                        await self._broadcast_status(response.content)
            except Exception as e:
                logger.error(f"Reasoning failed: {e}")
                return Message(
                    type=MessageType.ERROR,
                    content=f"Reasoning process failed: {str(e)}",
                    sender=self.id,
                    recipient=message.sender,
                )

        return None

    async def run(self, input_message: str) -> AsyncGenerator[Message, None]:
        yield Message(
            type=MessageType.STATUS,
            content="Starting reasoning process",
            sender=self.id,
        )

        try:
            self.status = AgentStatus.THINKING
            self.reasoning_history.clear()
            self.current_plan = None

            async for response in self._reason_about_task(input_message):
                yield response

        except Exception as e:
            logger.error(f"Reasoning run failed: {e}")
            yield Message(
                type=MessageType.ERROR,
                content=f"Reasoning failed: {str(e)}",
                sender=self.id,
            )
        finally:
            self.status = AgentStatus.IDLE

    async def _reason_about_task(self, task: str) -> AsyncGenerator[Message, None]:
        yield Message(
            type=MessageType.STATUS, content="Analyzing request...", sender=self.id
        )

        analysis = await self.reasoning_engine.analyze_request(task, self.context)
        self.reasoning_history.append(analysis)

        yield Message(
            type=MessageType.STATUS,
            content=f"Analysis: {analysis.content[:100]}...",
            sender=self.id,
        )

        self.current_plan = await self.reasoning_engine.create_plan(
            task, analysis, self.context
        )

        yield Message(
            type=MessageType.STATUS,
            content=f"Created plan with {len(self.current_plan.steps)} steps",
            sender=self.id,
            metadata={"plan": self.current_plan.steps},
        )

        result = await self._execute_plan_with_reasoning(self.current_plan)

        yield Message(type=MessageType.RESPONSE, content=result, sender=self.id)

    async def _execute_plan_with_reasoning(self, plan: Plan) -> str:
        current_results: List[ToolResult] = []
        completed_steps = 0

        for step_num, step in enumerate(plan.steps, 1):
            if completed_steps >= self.max_reasoning_steps:
                logger.warning(
                    f"Reached max reasoning steps {self.max_reasoning_steps}"
                )
                break

            yield Message(
                type=MessageType.STATUS,
                content=f"Step {step_num}/{len(plan.steps)}: {step}",
                sender=self.id,
            )

            try:
                tool_calls = await self.reasoning_engine.select_tools(
                    step, plan, self.context
                )

                if tool_calls:
                    yield Message(
                        type=MessageType.TOOL_CALL,
                        content=f"Executing {len(tool_calls)} tools for step {step_num}",
                        sender=self.id,
                        metadata={"tool_calls": [tc.__dict__ for tc in tool_calls]},
                    )

                    step_results = await self.reasoning_engine.execute_step(
                        tool_calls, self.context
                    )
                    current_results.extend(step_results)

                    yield Message(
                        type=MessageType.TOOL_RESULT,
                        content=f"Step {step_num} completed with {len([r for r in step_results if r.success])} successful tool executions",
                        sender=self.id,
                        metadata={"tool_results": [tr.__dict__ for tr in step_results]},
                    )
                else:
                    step_results = []

                reflection = await self.reasoning_engine.reflect(
                    plan, step_results, self.context
                )
                self.reasoning_history.append(reflection)

                yield Message(
                    type=MessageType.STATUS,
                    content=f"Reflection: {reflection.content[:150]}...",
                    sender=self.id,
                )

                (
                    should_continue,
                    next_action,
                ) = await self.reasoning_engine.should_continue(
                    plan, current_results, self.context
                )

                if not should_continue:
                    return next_action

                completed_steps += 1

            except Exception as e:
                logger.error(f"Step {step_num} failed: {e}")
                yield Message(
                    type=MessageType.ERROR,
                    content=f"Step {step_num} failed: {str(e)}",
                    sender=self.id,
                )
                break

        return f"Plan execution completed. Processed {completed_steps} steps out of {len(plan.steps)} planned steps."

    async def _broadcast_status(self, content: str) -> None:
        if self.context and hasattr(self.context, "message_bus"):
            from ..communication import CommunicationProtocol

            protocol = CommunicationProtocol(self.context.message_bus)
            await protocol.broadcast_status(self, self.status, {"detail": content})

    async def get_reasoning_summary(self) -> Dict[str, Any]:
        return {
            "current_plan": {
                "objective": self.current_plan.objective if self.current_plan else None,
                "steps": self.current_plan.steps if self.current_plan else [],
                "required_tools": self.current_plan.required_tools
                if self.current_plan
                else [],
            },
            "reasoning_history": [
                {
                    "step": thought.step.value,
                    "content": thought.content,
                    "confidence": thought.confidence,
                }
                for thought in self.reasoning_history
            ],
            "total_thoughts": len(self.reasoning_history),
        }


class AdvancedReasoningAgent(ReasoningAgent):
    def __init__(
        self,
        name: str = "AdvancedReasoningAgent",
        model_name: str = "google_genai:gemini-2.5-flash-lite",
    ):
        super().__init__(name, model_name)
        self.memory = []
        self.learning_enabled = True

    async def initialize(self, context: AgentContext) -> None:
        await super().initialize(context)

        additional_tools = [CalculatorTool(), SearchTool(), WeatherTool()]

        for tool in additional_tools:
            self.register_tool(tool)

    async def _reason_about_task(self, task: str) -> AsyncGenerator[Message, None]:
        yield Message(
            type=MessageType.STATUS,
            content="Starting advanced reasoning with memory and learning",
            sender=self.id,
        )

        similar_tasks = self._find_similar_tasks(task)

        if similar_tasks:
            yield Message(
                type=MessageType.STATUS,
                content=f"Found {len(similar_tasks)} similar past tasks to learn from",
                sender=self.id,
            )

        async for response in super()._reason_about_task(task):
            yield response

        if self.learning_enabled:
            self._store_task_memory(task, await self.get_reasoning_summary())

    def _find_similar_tasks(self, current_task: str) -> List[Dict[str, Any]]:
        similar = []
        current_task_lower = current_task.lower()

        for memory_item in self.memory:
            task_similarity = self._calculate_similarity(
                current_task_lower, memory_item["task"].lower()
            )
            if task_similarity > 0.7:
                similar.append(
                    {
                        "task": memory_item["task"],
                        "similarity": task_similarity,
                        "outcome": memory_item["outcome"],
                    }
                )

        return sorted(similar, key=lambda x: x["similarity"], reverse=True)[:3]

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.split())
        words2 = set(text2.split())
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0

    def _store_task_memory(self, task: str, reasoning_summary: Dict[str, Any]) -> None:
        memory_item = {
            "task": task,
            "reasoning": reasoning_summary,
            "outcome": "completed",
            "timestamp": asyncio.get_event_loop().time(),
        }

        self.memory.append(memory_item)

        if len(self.memory) > 100:
            self.memory = self.memory[-50:]

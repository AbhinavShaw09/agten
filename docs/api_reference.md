# API Reference

## Core Classes

### Agent

Base class for all agents in the framework.

#### Methods

- `__init__(name: str, description: str = "")`
- `async initialize(context: AgentContext) -> None`
- `async start() -> None`
- `async stop() -> None`
- `async send_message(message: Message) -> None`
- `async receive_message() -> Optional[Message]`
- `register_tool(tool: Tool) -> None`
- `async execute_tool(tool_call: ToolCall) -> ToolResult`
- `async process_message(message: Message) -> Optional[Message]`
- `async run(input_message: str) -> AsyncGenerator[Message, None]`
- `async get_status() -> Dict[str, Any]`

#### Properties

- `id: str` - Unique agent identifier
- `name: str` - Human-readable name
- `description: str` - Agent description
- `status: AgentStatus` - Current agent status
- `tools: Dict[str, Tool]` - Available tools
- `context: Optional[AgentContext]` - Agent context

### Tool

Base class for agent tools.

#### Methods

- `__init__(name: str, description: str)`
- `async execute(arguments: Dict[str, Any], context: AgentContext) -> Any`
- `_get_parameters_schema() -> Dict[str, Any]`

#### Properties

- `name: str` - Tool name
- `description: str` - Tool description
- `schema: Dict[str, Any]` - JSON schema for tool parameters

### Message

Represents a message between agents.

#### Fields

- `id: str` - Unique message identifier
- `type: MessageType` - Message type
- `content: str` - Message content
- `metadata: Dict[str, Any]` - Additional metadata
- `sender: Optional[str]` - Sender agent ID
- `recipient: Optional[str]` - Recipient agent ID
- `timestamp: float` - Message timestamp

### MessageType

Enum for message types:
- `TASK` - Task assignment
- `RESPONSE` - Response to a task
- `ERROR` - Error message
- `STATUS` - Status update
- `TOOL_CALL` - Tool execution request
- `TOOL_RESULT` - Tool execution result

### AgentStatus

Enum for agent status:
- `IDLE` - Agent is idle
- `THINKING` - Agent is processing
- `ACTING` - Agent is executing tools
- `WAITING` - Agent is waiting for input
- `ERROR` - Agent encountered an error
- `COMPLETED` - Agent finished its task

## Registry System

### AgentRegistry

Manages agent and tool registration and discovery.

#### Methods

- `register_agent(agent_class: Type[Agent], name: Optional[str] = None) -> None`
- `register_tool(tool_class: Type[Tool], name: Optional[str] = None) -> None`
- `create_agent(agent_name: str, **kwargs) -> Agent`
- `create_tool(tool_name: str, **kwargs) -> Tool`
- `get_agent(agent_id: str) -> Optional[Agent]`
- `list_agents() -> List[str]`
- `list_tools() -> List[str]`
- `auto_discover(package_path: str) -> None`

## Communication

### MessageBus

Handles message routing between agents.

#### Methods

- `subscribe(agent: Agent, topic: Optional[str] = None) -> None`
- `unsubscribe(agent: Agent, topic: Optional[str] = None) -> None`
- `async publish(message: Message, topic: Optional[str] = None) -> None`
- `get_conversation(conversation_id: str) -> Optional[ConversationState]`
- `get_conversation_history(conversation_id: str) -> List[Message]`

### CommunicationProtocol

High-level communication interface.

#### Methods

- `async send_task(sender: Agent, recipient_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str`
- `async send_response(sender: Agent, recipient_id: str, content: str, original_message_id: str, metadata: Optional[Dict[str, Any]] = None) -> str`
- `async send_error(sender: Agent, recipient_id: str, error_message: str, original_message_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str`
- `async broadcast_status(sender: Agent, status: AgentStatus, metadata: Optional[Dict[str, Any]] = None) -> str`
- `async create_conversation(initiator: Agent, participants: List[str], initial_message: str, metadata: Optional[Dict[str, Any]] = None) -> str`
- `async reply_to_conversation(sender: Agent, conversation_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str`

## Lifecycle Management

### AgentManager

Manages agent lifecycle and execution.

#### Methods

- `async create_agent(agent_class: type, name: str, context: Optional[AgentContext] = None, **kwargs) -> Agent`
- `async start_agent(agent_id: str) -> None`
- `async stop_agent(agent_id: str) -> None`
- `async destroy_agent(agent_id: str) -> None`
- `async start_manager() -> None`
- `async run_agent_task(agent_id: str, input_message: str) -> AsyncGenerator[Message, None]`
- `async get_agent_status(agent_id: str) -> Optional[Dict[str, Any]]`
- `async get_all_agents_status() -> Dict[str, Dict[str, Any]]`
- `async shutdown() -> None`

### AgentOrchestrator

Manages multi-agent workflows.

#### Methods

- `register_workflow(name: str, steps: List[Dict[str, Any]]) -> None`
- `async execute_workflow(workflow_name: str, initial_input: str) -> AsyncGenerator[Message, None]`

## Tool System

### ToolExecutor

Executes tools with safety limits and monitoring.

#### Methods

- `async execute_tool(tool: Tool, arguments: Dict[str, Any], context: AgentContext) -> ToolResult`
- `async get_resource_usage() -> Dict[str, Any]`
- `async cancel_all_tools() -> None`

### Built-in Tools

#### BashTool

Executes bash commands with safety controls.

**Parameters:**
- `command: str` - Bash command to execute
- `timeout: number` - Timeout in seconds (optional)

#### FileReadTool

Reads file contents.

**Parameters:**
- `path: str` - Path to the file to read

#### FileWriteTool

Writes content to files.

**Parameters:**
- `path: str` - Path to the file to write
- `content: str` - Content to write to the file

## Configuration

### ConfigManager

Manages framework configuration.

#### Methods

- `load_config(config_path: Optional[Union[str, Path]] = None, format: Optional[ConfigFormat] = None) -> FrameworkConfig`
- `save_config(config_path: Optional[Union[str, Path]] = None, format: Optional[ConfigFormat] = None) -> None`
- `get_agent_config(agent_name: str) -> Optional[AgentConfig]`
- `get_tool_config(tool_name: str) -> Optional[ToolConfig]`
- `add_agent_config(agent_config: AgentConfig) -> None`
- `add_tool_config(tool_config: ToolConfig) -> None`
- `remove_agent_config(agent_name: str) -> bool`
- `remove_tool_config(tool_name: str) -> bool`
- `update_agent_config(agent_name: str, **kwargs) -> bool`
- `update_tool_config(tool_name: str, **kwargs) -> bool`
- `merge_environment() -> Dict[str, str]`
- `apply_environment() -> None`
- `add_config_watcher(callback: callable) -> None`
- `remove_config_watcher(callback: callable) -> None`
- `async watch_config(interval: float = 1.0) -> None`
- `validate_config() -> List[str]`

### Configuration Classes

- `FrameworkConfig` - Main configuration container
- `AgentConfig` - Agent-specific configuration
- `ToolConfig` - Tool-specific configuration
- `CommunicationConfig` - Message bus configuration
- `SecurityConfig` - Security settings
- `LoggingConfig` - Logging configuration
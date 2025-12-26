# 🤖 Agent Framework

A production-ready Python framework for building intelligent agents with reasoning capabilities.

## ✨ Key Features

- 🧠 **Reasoning Engine** - Chain-of-thought planning and execution
- 🛠️ **Tool System** - Safe tool execution with security controls  
- 💬 **Communication** - Message passing between agents
- 🔄 **Lifecycle Management** - Complete agent orchestration
- ⚙️ **Configuration** - YAML/JSON configs with environment support
- 🧠 **Memory & Learning** - Advanced agents improve from experience
- 🧪 **Transparent Reasoning** - See exactly how agents think

## 🚀 Quick Start

### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/agten-framework
cd agten-framework

# Install dependencies
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Basic Usage
```python
import asyncio
from agents import AgentManager
from agents.reasoning import ReasoningAgent

async def main():
    manager = AgentManager()
    
    # Create reasoning agent
    agent = await manager.create_agent(ReasoningAgent, "SmartAgent")
    await manager.start_agent(agent.id)
    
    # Use the agent
    async for response in manager.run_agent_task(agent.id, "Calculate 25 * 8 + 17"):
        print(f"Agent: {response.content}")
    
    await manager.destroy_agent(agent.id)

if __name__ == "__main__":
    asyncio.run(main())
```

### CLI Usage
```bash
# Interactive chat with reasoning agent
python cli.py chat reason

# Advanced agent with memory and learning
python cli.py chat advanced

# Run single task
python cli.py run reason "Create a Python file that calculates factorial"

# List available agents
python cli.py list
```

## 🏗️ Architecture

### Core Components

#### 🧠 Reasoning Engine
- **Chain-of-Thought (CoT)**: Step-by-step logical reasoning
- **Plan Creation**: Automatic task decomposition
- **Tool Selection**: Intelligent tool choice based on context
- **Self-Reflection**: Learning from execution results
- **Adaptive Planning**: Dynamic strategy adjustment

#### 🛠️ Tool System
- **Safety Controls**: Resource limits, command blocking
- **Resource Monitoring**: Memory and CPU tracking
- **Error Recovery**: Graceful failure handling
- **Extensible Design**: Easy custom tool creation

#### 💬 Communication Protocol
- **Message Types**: Tasks, responses, errors, status updates
- **Routing**: Topic-based and direct messaging
- **Conversations**: Multi-turn dialogue support
- **Async Support**: Non-blocking message passing

#### 🔄 Lifecycle Management
- **Agent Registry**: Auto-discovery and registration
- **Orchestration**: Multi-agent workflows
- **Resource Cleanup**: Proper shutdown and memory management
- **Status Monitoring**: Real-time agent health tracking

### 🤖 Agent Types

#### ReasoningAgent
Basic reasoning with transparent thought process:
```python
agent = ReasoningAgent("BasicAgent")
# Provides: analysis → planning → execution → reflection
```

#### AdvancedReasoningAgent
Enhanced with memory and learning:
```python
agent = AdvancedReasoningAgent("LearningAgent")
# Adds: episodic memory, similarity matching, adaptive planning
```

### 🛠️ Built-in Tools

| Tool | Purpose | Safety Features |
|-------|---------|----------------|
| `BashTool` | Execute shell commands | Blocked commands, timeouts, memory limits |
| `FileReadTool` | Read file contents | Path validation, size limits |
| `FileWriteTool` | Write to files | Safe directory access, size checks |
| `CalculatorTool` | Math calculations | Expression validation |
| `SearchTool` | Web search | Query validation, result filtering |
| `WeatherTool` | Weather data | Location validation |
| `FileAnalysisTool` | Analyze code files | Language detection, complexity metrics |
| `CodeExecutionTool` | Safe code execution | Sandboxing, output capture |

## ⚙️ Configuration

### Example Configuration
```yaml
# config.yaml
agents:
  SmartAgent:
    type: ReasoningAgent
    description: "Agent with reasoning capabilities"
    timeout: 120.0
    max_concurrent_tasks: 3
    tools: [bash, file_read, file_write, calculator]

tools:
  bash:
    type: BashTool
    timeout: 30.0
    blocked_commands: ["rm -rf", "sudo", "chmod 777"]
    max_memory_mb: 512

security:
  enable_sandbox: true
  max_file_size_mb: 100
  allowed_file_extensions: [.txt, .py, .js, .md, .json]

communication:
  message_bus_type: memory
  max_message_size: 1048576
  max_conversation_length: 1000
```

### Environment Variables
```bash
# Set API keys and configuration
export AGENT_FRAMEWORK_MODEL="google_genai:gemini-2.5-flash-lite"
export WEATHER_API_KEY="your-api-key"
export AGENT_FRAMEWORK_LOG_LEVEL="INFO"
```

## 🧪 Reasoning Process

### Step-by-Step Example

**User Request**: "Create a Python calculator program and save the result"

**Agent Reasoning**:
1. 🧠 **Analysis**: 
   - User wants: Python calculator program
   - Requirements: Calculate operations, save result
   - Tools needed: CodeExecutionTool, FileWriteTool

2. 📋 **Planning**:
   - Step 1: Write calculator code
   - Step 2: Test with sample calculation  
   - Step 3: Save result to file
   - Success criteria: Working calculator with saved output

3. 🛠️ **Tool Selection**:
   - CodeExecutionTool for writing/testing code
   - FileWriteTool for saving results

4. ✅ **Execution**:
   - Write Python code with basic arithmetic operations
   - Test with sample input (25 * 4 + 17 = 117)
   - Save result to calculator_output.txt

5. 🤔 **Reflection**:
   - Code executes correctly
   - Output saved successfully
   - All requirements met
   - Task completed successfully

## 🧠 Building Custom Agents

### Simple Agent
```python
from agents.core import Agent, Message, MessageType
from agents.reasoning import CoTReasoningEngine

class CustomAgent(Agent):
    def __init__(self, name="CustomAgent"):
        super().__init__(name, "A custom specialized agent")
        self.reasoning_engine = CoTReasoningEngine()

    async def initialize(self, context):
        await super().initialize(context)
        await self.reasoning_engine.initialize()
        # Register custom tools here
        self.register_tool(MyCustomTool())

    async def process_message(self, message):
        if message.type == MessageType.TASK:
            # Use reasoning engine to process
            async for response in self.reasoning_engine.process_task(
                message.content, self.context
            ):
                yield response
```

### Custom Tool
```python
from agents.core import Tool

class CustomTool(Tool):
    def __init__(self):
        super().__init__("custom_tool", "Description of what this tool does")

    async def execute(self, arguments, context):
        # Implement your tool logic
        result = await some_external_api_call(arguments)
        return result

    def _get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input parameter"}
            },
            "required": ["input"]
        }
```

## 🧪 Advanced Usage

### Multi-Agent Workflows
```python
from agents import AgentOrchestrator

orchestrator = AgentOrchestrator(manager)

# Define workflow steps
orchestrator.register_workflow("data_analysis", [
    {"agent": "SearchAgent", "type": "single"},
    {"agents": ["DataAnalyzer", "CodeReviewer"], "type": "parallel"},
    {"agent": "ReportGenerator", "type": "single"}
])

# Execute workflow
async for result in orchestrator.execute_workflow("data_analysis", "Analyze sales data"):
    print(result.content)
```

### Memory and Learning
```python
# Advanced agents automatically learn from experience
agent = AdvancedReasoningAgent("LearningAgent")

# After several similar tasks:
history = await agent.get_reasoning_summary()
print(f"Agent has learned from {len(agent.memory)} past tasks")

# Agent uses memory to improve future planning
similar_tasks = agent._find_similar_tasks("new request")
if similar_tasks:
    # Agent adapts approach based on past success
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agents --cov-report=html

# Run specific test categories
pytest tests/test_reasoning.py -v
pytest tests/test_tools.py -v
```

### Test Structure
```
tests/
├── test_core.py           # Core agent functionality
├── test_reasoning.py       # Reasoning engine tests  
├── test_tools.py          # Tool execution tests
├── test_communication.py   # Message passing tests
├── test_lifecycle.py      # Lifecycle management tests
└── test_config.py         # Configuration tests
```

## 📚 Development

### Project Structure
```
agents/
├── core/                  # Core abstractions
├── reasoning/             # Reasoning engines
├── tools/                 # Tool implementations  
├── communication/          # Message protocols
├── lifecycle/             # Agent lifecycle
├── config/                # Configuration system
├── registry/              # Agent discovery
└── __init__.py            # Package exports

tests/                     # Test suite
├── test_*.py
└── conftest.py

docs/                       # Documentation
├── api_reference.md
├── tutorials.md
└── examples/

cli.py                      # Command-line interface
main.py                     # Quick start demo
config.yaml                  # Example configuration
pyproject.toml              # Package metadata
```

### Development Setup
```bash
# Clone repository
git clone https://github.com/yourusername/agent-framework
cd agent-framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest tests/
```

### Code Style
- Follow PEP 8 guidelines
- Use type hints everywhere
- Write docstrings for public APIs
- Maximum line length: 88 characters
- Use async/await properly

## 🚀 Production Deployment

### Docker Support
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -e .

EXPOSE 8000
CMD ["python", "-m", "agents.cli", "chat", "reason"]
```

### Environment Configuration
```bash
# Production environment variables
export AGENT_FRAMEWORK_ENV="production"
export AGENT_FRAMEWORK_LOG_LEVEL="INFO"
export AGENT_FRAMEWORK_CONFIG="/etc/agents/config.yaml"

# Security settings
export AGENT_FRAMEWORK_SANDBOX="true"
export AGENT_FRAMEWORK_MAX_MEMORY="1024"
```

## 🔒 Security

### Safety Features
- **Sandboxed Execution**: Isolated tool execution environment
- **Input Validation**: Comprehensive parameter checking
- **Command Blocking**: Dangerous command prevention
- **Resource Limits**: Memory, CPU, and file size restrictions
- **Path Validation**: Restricted file system access
- **Timeout Controls**: Maximum execution time limits

### Security Best Practices
```python
# Secure tool implementation
class SecureTool(Tool):
    def __init__(self):
        super().__init__("secure_tool", "Tool with security controls")

    async def execute(self, arguments, context):
        # Validate all inputs
        self._validate_arguments(arguments)
        
        # Check security permissions
        if not self._has_permission(context, "file_access"):
            raise PermissionError("File access not permitted")
        
        # Execute with timeout and limits
        return await asyncio.wait_for(
            self._safe_execute(arguments),
            timeout=self.max_timeout
        )

    def _validate_arguments(self, arguments):
        # Input validation logic
        pass

    def _has_permission(self, context, permission):
        # Permission checking logic
        pass

    def _safe_execute(self, arguments):
        # Actual tool execution
        pass
```

## 📖 Documentation

### Complete Documentation
- [API Reference](docs/api_reference.md) - Detailed class and method documentation
- [Tutorials](docs/tutorials.md) - Step-by-step learning guides
- [Examples](docs/examples/) - Real-world usage examples
- [Configuration](docs/configuration.md) - Configuration options

### Generating Documentation
```bash
# Generate API docs from source
pdoc agents/ -o docs/api/

# Check documentation coverage
pdoc --coverage agents/

# Serve documentation locally
pdoc agents/ --doc-theme django --port 8000
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

### How to Contribute
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes
4. **Test** thoroughly (`pytest tests/`)
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to your fork (`git push origin feature/amazing-feature`)
7. **Create** a Pull Request

### Development Guidelines
- Write clean, documented code
- Add tests for new features
- Follow existing code style
- Update documentation for changes
- Ensure all tests pass

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangChain](https://python.langchain.com/) for LLM integration
- Inspired by modern agent architectures
- Security best practices from the Python community
- Tool safety patterns from cybersecurity research

## 📞 Support

- 📧 **Issues**: [GitHub Issues](https://github.com/yourusername/agent-framework/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/agent-framework/discussions)
- 📚 **Documentation**: [Docs Site](https://agent-framework.readthedocs.io/)

---

**Built with ❤️ for the agent development community**# agten

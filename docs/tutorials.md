# Tutorials

## Tutorial 1: Creating Your First Agent

In this tutorial, you'll create a simple agent that responds to greetings.

### Step 1: Import Required Classes

```python
from agents.core import Agent, Message, MessageType
from agents import AgentManager
```

### Step 2: Create Your Agent Class

```python
class GreetingAgent(Agent):
    async def process_message(self, message: Message) -> Optional[Message]:
        if message.type == MessageType.TASK:
            content = message.content.lower()
            
            if "hello" in content or "hi" in content:
                response = "Hello! Nice to meet you!"
            elif "how are you" in content:
                response = "I'm doing great, thanks for asking!"
            else:
                response = "Hi! I'm a greeting agent. Say hello or ask how I am!"
            
            return Message(
                type=MessageType.RESPONSE,
                content=response,
                sender=self.id,
                recipient=message.sender
            )
        
        return None
    
    async def run(self, input_message: str) -> AsyncGenerator[Message, None]:
        yield Message(
            type=MessageType.STATUS,
            content="Starting greeting agent",
            sender=self.id
        )
        
        # Simple processing
        content = input_message.lower()
        if "hello" in content or "hi" in content:
            response = "Hello! Nice to meet you!"
        else:
            response = "Hi! Say hello to get a friendly response!"
        
        yield Message(
            type=MessageType.RESPONSE,
            content=response,
            sender=self.id
        )
```

### Step 3: Use Your Agent

```python
import asyncio

async def main():
    manager = AgentManager()
    
    # Create and start the agent
    agent = await manager.create_agent(GreetingAgent, "Greeter")
    await manager.start_agent(agent.id)
    
    # Test some messages
    test_messages = [
        "Hello there!",
        "How are you doing?",
        "What's the weather like?"
    ]
    
    for msg in test_messages:
        print(f"You: {msg}")
        
        async for response in manager.run_agent_task(agent.id, msg):
            if response.type.value == "response":
                print(f"Agent: {response.content}")
        print()
    
    await manager.destroy_agent(agent.id)

if __name__ == "__main__":
    asyncio.run(main())
```

## Tutorial 2: Creating Custom Tools

Learn how to create tools that agents can use.

### Step 1: Define Your Tool

```python
import requests
from agents.core import Tool

class WeatherTool(Tool):
    def __init__(self):
        super().__init__("weather", "Get current weather for any city")

    async def execute(self, arguments, context):
        city = arguments.get("city")
        if not city:
            raise ValueError("City name is required")
        
        # Using a free weather API (you'd need an API key for production)
        api_key = context.variables.get("weather_api_key")
        if not api_key:
            return "Weather API key not configured"
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            temp = data["main"]["temp"]
            description = data["weather"][0]["description"]
            
            return f"The weather in {city} is {temp}°C with {description}"
            
        except requests.RequestException as e:
            return f"Failed to get weather: {str(e)}"

    def _get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of the city to get weather for"
                }
            },
            "required": ["city"]
        }
```

### Step 2: Create an Agent That Uses Your Tool

```python
class WeatherAgent(Agent):
    def __init__(self, name="WeatherBot"):
        super().__init__(name, "An agent that can tell you the weather")

    async def initialize(self, context):
        await super().initialize(context)
        self.register_tool(WeatherTool())

    async def process_message(self, message):
        if message.type == MessageType.TASK:
            content = message.content.lower()
            
            if "weather" in content:
                # Extract city name (simple extraction)
                if "in" in content:
                    city = content.split("in")[-1].strip().rstrip("?!")
                    tool_call = ToolCall(
                        name="weather",
                        arguments={"city": city}
                    )
                    
                    result = await self.execute_tool(tool_call)
                    
                    if result.success:
                        response = result.result
                    else:
                        response = f"Sorry, I couldn't get the weather: {result.error}"
                else:
                    response = "Which city would you like to know the weather for?"
            else:
                response = "I can help you with weather information. Ask me about the weather in any city!"
            
            return Message(
                type=MessageType.RESPONSE,
                content=response,
                sender=self.id,
                recipient=message.sender
            )
        
        return None
```

### Step 3: Use the Weather Agent

```python
async def demo_weather_agent():
    manager = AgentManager()
    
    # Create context with API key
    context = AgentContext(
        session_id="weather_demo",
        variables={"weather_api_key": "your_api_key_here"}
    )
    
    agent = await manager.create_agent(WeatherAgent, "WeatherBot", context=context)
    await manager.start_agent(agent.id)
    
    test_messages = [
        "What's the weather like in London?",
        "Tell me about the weather in Tokyo",
        "Can you help me with something?"
    ]
    
    for msg in test_messages:
        print(f"You: {msg}")
        
        async for response in manager.run_agent_task(agent.id, msg):
            if response.type.value == "response":
                print(f"WeatherBot: {response.content}")
        print()
    
    await manager.destroy_agent(agent.id)
```

## Tutorial 3: Multi-Agent Collaboration

Learn how to make multiple agents work together.

### Step 1: Create Specialized Agents

```python
class ResearchAgent(Agent):
    def __init__(self):
        super().__init__("Researcher", "An agent that gathers information")

    async def process_message(self, message):
        if message.type == MessageType.TASK:
            topic = message.content
            
            # Simulate research
            research_data = f"Research data about {topic}: This is a comprehensive analysis..."
            
            return Message(
                type=MessageType.RESPONSE,
                content=research_data,
                sender=self.id,
                recipient=message.sender
            )
        return None

class SummaryAgent(Agent):
    def __init__(self):
        super().__init__("Summarizer", "An agent that summarizes information")

    async def process_message(self, message):
        if message.type == MessageType.TASK:
            content = message.content
            
            # Create a simple summary
            sentences = content.split('. ')
            summary = '. '.join(sentences[:3]) + '.'
            
            return Message(
                type=MessageType.RESPONSE,
                content=f"Summary: {summary}",
                sender=self.id,
                recipient=message.sender
            )
        return None
```

### Step 2: Create Workflow Orchestrator

```python
async def research_workflow(manager, topic):
    # Create agents
    researcher = await manager.create_agent(ResearchAgent, "Researcher")
    summarizer = await manager.create_agent(SummaryAgent, "Summarizer")
    
    try:
        await manager.start_agent(researcher.id)
        await manager.start_agent(summarizer.id)
        
        protocol = CommunicationProtocol(manager.message_bus)
        
        # Step 1: Research
        print("Step 1: Researching topic...")
        async for response in manager.run_agent_task(researcher.id, topic):
            if response.type.value == "response":
                research_result = response.content
                print(f"Research completed: {research_result[:100]}...")
        
        # Step 2: Summarize
        print("\nStep 2: Summarizing research...")
        async for response in manager.run_agent_task(summarizer.id, research_result):
            if response.type.value == "response":
                summary = response.content
                print(f"Final Summary: {summary}")
        
    finally:
        await manager.destroy_agent(researcher.id)
        await manager.destroy_agent(summarizer.id)
```

## Tutorial 4: Configuration Management

Learn how to use configuration files to manage your agents.

### Step 1: Create Configuration File

```yaml
# config.yaml
agents:
  CustomerService:
    name: CustomerService
    type: CustomServiceAgent
    description: "Handles customer service inquiries"
    enabled: true
    max_concurrent_tasks: 5
    timeout: 120.0
    environment:
      SERVICE_LEVEL: "premium"
      RESPONSE_TIME: "5 minutes"

tools:
  weather_api:
    name: weather_api
    type: WeatherTool
    enabled: true
    timeout: 30.0
    parameters:
      api_key: "${WEATHER_API_KEY}"
      units: "metric"

communication:
  message_bus_type: memory
  max_conversation_length: 500

security:
  enable_sandbox: true
  max_file_size_mb: 50

logging:
  level: INFO
  file_path: agent.log
```

### Step 2: Load and Use Configuration

```python
from agents import ConfigManager, AgentManager

async def config_demo():
    # Load configuration
    config_manager = ConfigManager()
    config_manager.load_config("config.yaml")
    
    # Apply environment variables
    config_manager.apply_environment()
    
    # Create manager with configuration
    manager = AgentManager()
    
    # Create agent from configuration
    agent_config = config_manager.get_agent_config("CustomerService")
    if agent_config and agent_config.enabled:
        # You would need to map the type string to actual class
        agent = await manager.create_agent(
            CustomServiceAgent, 
            agent_config.name,
            **agent_config.metadata
        )
        await manager.start_agent(agent.id)
        
        # Use the agent...
        
        await manager.destroy_agent(agent.id)
```

## Tutorial 5: Error Handling and Logging

Learn proper error handling and logging practices.

### Step 1: Robust Agent Implementation

```python
import logging

logger = logging.getLogger(__name__)

class RobustAgent(Agent):
    async def process_message(self, message):
        try:
            if message.type == MessageType.TASK:
                logger.info(f"Processing message: {message.content}")
                
                # Your logic here
                result = await self.process_task(message.content)
                
                return Message(
                    type=MessageType.RESPONSE,
                    content=result,
                    sender=self.id,
                    recipient=message.sender
                )
        
        except ValueError as e:
            logger.warning(f"Invalid input: {e}")
            return Message(
                type=MessageType.ERROR,
                content=f"Invalid input: {str(e)}",
                sender=self.id,
                recipient=message.sender
            )
        
        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            return Message(
                type=MessageType.ERROR,
                content="Sorry, something went wrong while processing your request",
                sender=self.id,
                recipient=message.sender
            )
        
        return None
    
    async def process_task(self, content):
        # Your business logic with proper validation
        if not content or not content.strip():
            raise ValueError("Empty message received")
        
        # Process the content
        return f"Processed: {content}"
```

### Step 2: Tool Error Handling

```python
class SafeTool(Tool):
    async def execute(self, arguments, context):
        try:
            # Validate arguments
            if not self.validate_arguments(arguments):
                raise ValueError("Invalid arguments provided")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.do_work(arguments, context),
                timeout=30.0
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Tool execution timed out: {self.name}")
            raise
            
        except Exception as e:
            logger.error(f"Tool {self.name} failed: {e}", exc_info=True)
            raise
    
    def validate_arguments(self, arguments):
        # Your validation logic
        return True
    
    async def do_work(self, arguments, context):
        # Your tool implementation
        return "Tool result"
```

These tutorials cover the essential aspects of working with the agent framework. Each tutorial builds upon the previous ones, starting from basic concepts and progressing to more advanced patterns.
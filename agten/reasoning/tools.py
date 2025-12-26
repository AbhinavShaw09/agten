from typing import Any, Dict
import requests
import re
import json
from abc import ABC

from ..core import Tool
from ..tools import ToolExecutor


class CalculatorTool(Tool):
    def __init__(self):
        super().__init__("calculator", "Perform mathematical calculations")

    async def execute(self, arguments, context):
        expression = arguments.get("expression", "")
        if not expression:
            raise ValueError("Mathematical expression is required")

        try:
            result = eval(expression)
            return {
                "expression": expression,
                "result": result,
                "type": type(result).__name__,
            }
        except Exception as e:
            raise ValueError(f"Invalid mathematical expression: {str(e)}")

    def _get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4')",
                }
            },
            "required": ["expression"],
        }


class SearchTool(Tool):
    def __init__(self):
        super().__init__("search", "Search the web for information")
        self.search_api = None

    async def execute(self, arguments, context):
        query = arguments.get("query", "")
        if not query:
            raise ValueError("Search query is required")

        try:
            # Simple web search implementation (would use proper API in production)
            search_results = await self._perform_search(query)
            return {
                "query": query,
                "results": search_results,
                "count": len(search_results),
            }
        except Exception as e:
            raise ValueError(f"Search failed: {str(e)}")

    async def _perform_search(self, query: str) -> list:
        await asyncio.sleep(1)

        return [
            {
                "title": f"Search result for {query}",
                "url": f"https://example.com/{query.replace(' ', '-')}",
                "snippet": f"This is a mock search result for query: {query}",
            },
            {
                "title": f"Another result about {query}",
                "url": f"https://example.com/another-{query.replace(' ', '-')}",
                "snippet": f"Additional information about {query} from another source",
            },
        ]

    def _get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        }


class WeatherTool(Tool):
    def __init__(self):
        super().__init__("weather", "Get current weather information")

    async def execute(self, arguments, context):
        location = arguments.get("location", "")
        if not location:
            raise ValueError("Location is required")

        try:
            weather_data = await self._get_weather(location)
            return weather_data
        except Exception as e:
            raise ValueError(f"Weather lookup failed: {str(e)}")

    async def _get_weather(self, location: str) -> Dict[str, Any]:
        await asyncio.sleep(0.5)

        conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]
        temps = [15, 18, 22, 25, 28, 30]

        return {
            "location": location,
            "temperature": temps[hash(location) % len(temps)],
            "condition": conditions[hash(location) % len(conditions)],
            "humidity": 65,
            "wind_speed": 10,
            "source": "mock_api",
        }

    def _get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or location"}
            },
            "required": ["location"],
        }


class FileAnalysisTool(Tool):
    def __init__(self):
        super().__init__("file_analysis", "Analyze file contents for insights")

    async def execute(self, arguments, context):
        file_path = arguments.get("path", "")
        analysis_type = arguments.get("type", "general")

        if not file_path:
            raise ValueError("File path is required")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if analysis_type == "lines":
                return self._analyze_lines(content)
            elif analysis_type == "words":
                return self._analyze_words(content)
            elif analysis_type == "python":
                return self._analyze_python(content)
            else:
                return self._analyze_general(content)

        except Exception as e:
            raise ValueError(f"File analysis failed: {str(e)}")

    def _analyze_lines(self, content: str) -> Dict[str, Any]:
        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        return {
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "average_line_length": sum(len(line) for line in lines) / len(lines)
            if lines
            else 0,
        }

    def _analyze_words(self, content: str) -> Dict[str, Any]:
        words = re.findall(r"\b\w+\b", content.lower())
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        return {
            "total_words": len(words),
            "unique_words": len(set(words)),
            "most_common": sorted(
                word_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def _analyze_python(self, content: str) -> Dict[str, Any]:
        lines = content.split("\n")
        functions = len(re.findall(r"def\s+\w+", content))
        classes = len(re.findall(r"class\s+\w+", content))
        imports = len(re.findall(r"import\s+\w+|from\s+\w+\s+import", content))
        comments = len(re.findall(r"#.*$", content, re.MULTILINE))

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "comment_lines": comments,
            "code_complexity": "moderate" if functions + classes < 20 else "high",
        }

    def _analyze_general(self, content: str) -> Dict[str, Any]:
        return {
            "character_count": len(content),
            "word_count": len(re.findall(r"\b\w+\b", content)),
            "line_count": len(content.split("\n")),
            "estimated_reading_time": len(content.split()) / 200,
        }

    def _get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to analyze",
                },
                "type": {
                    "type": "string",
                    "description": "Type of analysis: general, lines, words, python",
                    "enum": ["general", "lines", "words", "python"],
                    "default": "general",
                },
            },
            "required": ["path"],
        }


class CodeExecutionTool(Tool):
    def __init__(self):
        super().__init__("code_execution", "Execute code snippets safely")

    async def execute(self, arguments, context):
        code = arguments.get("code", "")
        language = arguments.get("language", "python")

        if not code:
            raise ValueError("Code is required")

        if language not in ["python", "javascript"]:
            raise ValueError("Only python and javascript are supported")

        try:
            if language == "python":
                result = await self._execute_python(code)
            else:
                result = await self._execute_javascript(code)

            return {"language": language, "result": result, "success": True}

        except Exception as e:
            return {"language": language, "error": str(e), "success": False}

    async def _execute_python(self, code: str) -> str:
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            exec(code, {})
            output = captured_output.getvalue()
            return output if output else "Code executed successfully (no output)"
        finally:
            sys.stdout = old_stdout

    async def _execute_javascript(self, code: str) -> str:
        return f"JavaScript execution not implemented: {code}"

    def _get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to execute"},
                "language": {
                    "type": "string",
                    "description": "Programming language",
                    "enum": ["python", "javascript"],
                    "default": "python",
                },
            },
            "required": ["code"],
        }

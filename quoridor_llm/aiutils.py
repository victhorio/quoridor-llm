import os
from dataclasses import dataclass
from importlib import resources

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageToolCall as ToolCall


@dataclass
class ParamInfo:
    name: str
    type: str
    desc: str
    required: bool
    enum: list[str] | None = None

    def spec_dict(self) -> dict:
        spec = {
            "type": self.type,
            "description": self.desc,
        }
        if self.enum:
            spec["enum"] = self.enum
        return spec


def client_create() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def prompt_read(name: str) -> str:
    with resources.files("quoridor_llm.prompts").joinpath(f"{name}.txt").open("r") as f:
        return f.read()


def tool_spec_create(name: str, desc: str, params: list[ParamInfo]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {p.name: p.spec_dict() for p in params},
                "required": [p.name for p in params if p.required],
            },
        },
    }


def tool_result_create(tool_call: ToolCall, result: str) -> dict:
    return {
        "role": "tool",
        "name": tool_call.function.name,
        "tool_call_id": tool_call.id,
        "content": result,
    }

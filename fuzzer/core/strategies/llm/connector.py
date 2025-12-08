from enum import Enum
from openai import OpenAI
from typing import Optional
from abc import ABC, abstractmethod
import os
import json
import ollama
import logging

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("llm")


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7, **kwargs) -> str:
        pass


class LLModels(Enum):
    QWEN3_SMALL = "qwen3:0.6b"
    QWEN3_1_7b = "qwen3:1.7b"
    QWEN3_4b = "qwen3:4b"
    QWEN3 = "qwen3:8b"
    DEEPSEEK_R1_SMALL = "deepseek-r1:1.5b"
    DEEPSEEK_R1 = "deepseek-r1:8b"
    GPT5_NANO = "gpt-5-nano" # Price: Input=$0.05, Output=$0.40 (per 1M tokens)
    GPT5_MINI = "gpt-5-mini" # Price: Input=$0.25, Output=$2.0 (per 1M tokens)
    GPT5 = "gpt-5" # Price: Input=$1.25, Output=$10.00 (per 1M tokens)

    def __str__(self):
        return self.value

    def get_provider(self):
        ollama_models = [self.QWEN3_SMALL, self.QWEN3, self.QWEN3_4b, self.QWEN3_1_7b, self.DEEPSEEK_R1_SMALL, self.DEEPSEEK_R1]
        if LLModels[self.name] in ollama_models:
            return OllamaProvider(self.value, host=OLLAMA_HOST)
        return OpenAIProvider(self.value, api_key=OPENAI_KEY)


class OllamaProvider(LLMProvider):
    def __init__(self, model: LLModels, host: str):
        self.client = ollama.Client(host=host)
        self.model = model

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7, think=False, **kwargs) -> str:
        messages = []
        if system_prompt:
             messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        options = {'temperature': temperature}
        options.update(kwargs) # for extra parameters like top_p, num_predict, etc.

        try:
            response = self.client.chat(model=self.model, messages=messages, think=think, options=options)
            return response['message']['content']
        except Exception as e:
            logger.error(f"[LLM] Ollama provider error: {e}")
            return f"[ERROR] Ollama: {e}"

class OpenAIProvider(LLMProvider):
    def __init__(self, model: LLModels, api_key: str, base_url: Optional[str] = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def save_cost(self, cost):
        data = []
        filename = "cost.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
            except (json.JSONDecodeError, IOError):
                data = []
        data.append(cost)
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7,
                 **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                reasoning_effort="minimal"
            )

            self.save_cost({
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            })
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI provider error: {e}")
            return f"[ERROR] OpenAI: {e}"
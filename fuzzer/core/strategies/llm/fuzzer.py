from core.strategies import Fuzzer
from core.strategies.llm.connector import LLModels
import logging

SYSTEM_PROMPT = """
You are a LLM-driven Fuzzer, which takes in a JSON payload and returns a mutated version of it.
Try to avoid generating invalid JSON. 
Try to understand the semantics of the input and mutate/change the values for the JSON keys to trigger bugs and vulnerabilities in the test environment.
"""

logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("llm")


class LLMFuzzer(Fuzzer):
    def __init__(self, model: LLModels):
        self.model = model
        self.provider = self.model.get_provider()

    def fuzz(self, data_str: str, feedback: dict, **kwargs) -> str:
        mutated_data = self.provider.generate(data_str, SYSTEM_PROMPT, think=True)
        print(f"[FUZZ]: {mutated_data}")
        return mutated_data



class LLMGeneratorFuzzer(LLMFuzzer):
    pass


class LLMMutatorFuzzer(LLMFuzzer):
    pass
from core.strategies import Fuzzer
import logging



logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("llm")


class LLMFuzzer(Fuzzer):
    def __init__(self, model: str):
        self.model = model

    def fuzz(self, data_str: str, feedback: dict, **kwargs) -> str:
        return data_str



class LLMGeneratorFuzzer(LLMFuzzer):
    pass


class LLMMutatorFuzzer(LLMFuzzer):
    pass
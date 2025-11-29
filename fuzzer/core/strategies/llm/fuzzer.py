from core.strategies import Fuzzer



class LLMFuzzer(Fuzzer):
    def __init__(self, model: str):
        self.model = model

    def fuzz(self, data_str: str, feedback: dict) -> str:
        return data_str



class LLMGeneratorFuzzer(LLMFuzzer):
    pass


class LLMMutatorFuzzer(LLMFuzzer):
    pass
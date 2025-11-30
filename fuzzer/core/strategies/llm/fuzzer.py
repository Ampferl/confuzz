from core.strategies import Fuzzer
from core.strategies.llm.connector import LLModels
from core.strategies.llm.autoprompter import Autoprompter, AutoprompterModes
from core.strategies.llm.parser import ResponseParser

import logging
import json


logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("llm")


class LLMFuzzer(Fuzzer):
    def __init__(self, model: LLModels):
        self.model = model
        self.provider = self.model.get_provider()
        self.autoprompter = Autoprompter(AutoprompterModes.MUTATION)
        self.system_prompt = self.autoprompter.build_system_prompt()

    def fuzz(self, data_str: str, feedback: dict, request: str, opts: dict, **kwargs) -> str:
        user_prompt = self.autoprompter.build_user_prompt(request_path=request, response=data_str, feedback=feedback)
        print(f"[PROMPT]:\n{30*'='}\n{user_prompt}\n{30*'='}")

        mutated_data = self.provider.generate(user_prompt, self.system_prompt, temperature=opts.get("temperature", False), think=opts.get("think", False))

        parsed_data = ResponseParser.extract_json(llm_output=mutated_data)
        if parsed_data is not None:
            mutated_data = json.dumps(parsed_data)

        return mutated_data



class LLMGeneratorFuzzer(LLMFuzzer):
    def __init__(self, model):
        super().__init__(model)


class LLMMutatorFuzzer(LLMFuzzer):
    def __init__(self, model):
        super().__init__(model)

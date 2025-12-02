import logging
import random
import json

from core.strategies import Fuzzer
from core.strategies.custom_baseline.mutator import Mutator
from core.shared import state


logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("baseline")



class CustomBaselineFuzzer(Fuzzer):
    def __init__(self):
        self.mutator = Mutator(state.opts.get("list")) # TODO Replace Mutator with MutationFuzzer from Fuzzing Book

    def fuzz(self, data_str: str, **kwargs) -> str:
        try:
            """
            - 10% Bit Flipping (Error Handling)
            - 90% Structure Mutation (Test Logic/Injections)
            """
            if random.random() < 0.1:
                logger.debug("Strategy: Bit Flipping")
                return self.mutator.bit_flip(data_str)

            logger.debug("Strategy: Structure Mutation")
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                # If it fails, just fall back to bit flipping
                logger.error("Failed parsing the data")
                return self.mutator.bit_flip(data_str)

            mutated_data = self.mutator.mutate_json_structure(data)
            return json.dumps(mutated_data)

        except Exception as e:
            logger.error(f"Error fuzzing data: {e}")
            return data_str
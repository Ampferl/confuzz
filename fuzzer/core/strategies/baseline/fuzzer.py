import logging
import random
import json

from core.strategies import Fuzzer
from core.strategies.baseline.mutator import Mutator
from core.shared import state


logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("baseline")

###################################################################################
## This Baseline Fuzzer is based on the MutationFuzzer of the fuzzing book       ##
## Github: https://github.com/uds-se/fuzzingbook/                                ##
## Website: https://www.fuzzingbook.org/                                         ##
## Copyright (c) 2018-2020 Saarland University, CISPA, authors, and contributors ##
###################################################################################

class BaselineFuzzer(Fuzzer):
    def __init__(self, min_mutations: int = 1, max_mutations: int = 1):
        self.mutator = Mutator()
        self.min_mutations = min_mutations
        self.max_mutations = max_mutations

    def mutate(self, s: str) -> str:
        mutators = [
            self.mutator.delete_random_character,
            self.mutator.insert_random_character,
            self.mutator.flip_random_character
        ]
        mutator = random.choice(mutators)
        return mutator(s)

    def fuzz(self, data: str, **kwargs) -> str:
        trials = random.randint(self.min_mutations, self.max_mutations)
        for i in range(trials):
            data = self.mutate(data)
        return data

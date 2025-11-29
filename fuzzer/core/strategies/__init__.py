import enum

class Strategies(enum.Enum):
    BASELINE = 0
    LLM_GENERATION = 1
    LLM_MUTATION = 2


class Fuzzer:
    def fuzz(self, data):
        pass

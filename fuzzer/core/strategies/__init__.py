import enum

class Strategies(enum.Enum):
    BASELINE = 'baseline'
    CUSTOM_BASELINE = 'custom_baseline'
    #LLM_GENERATION = 'llm_generation'
    #LLM_MUTATION = 'llm_mutation'
    LLM = 'llm'

    def __str__(self):
        return self.value


class Fuzzer:
    def fuzz(self, data, **kwargs):
        pass

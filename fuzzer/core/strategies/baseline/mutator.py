import random
import json

# TODO Replace with loading of NAUGHTY_STRING_LIST
NAUGHTY_STRINGS = [
    "../../etc/passwd",
    "' OR '1'='1",
    "http://localhost:22",
    "null",
    "true",
    "false"
]

NAUGHTY_INTS = [
    0,
    -1,
    2147483647,  # MAX_INT (32-bit)
    9223372036854775807,  # MAX_INT (64-bit)
    999999999  #)
]

class Mutator:

    @staticmethod
    def bit_flip(data: str, probability: float = 0.05) -> str:
        data_list = list(data)
        for i in range(len(data_list)):
            if random.random() < probability:
                # Replace current char with a random ASCII char
                data_list[i] = chr(random.randint(32, 126))
        return "".join(data_list)

    @staticmethod
    def mutate_json_structure(data: dict) -> dict:
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = Mutator.mutate_json_structure(value)
        elif isinstance(data, list):
            for i in range(len(data)):
                data[i] = Mutator.mutate_json_structure(data[i])
        elif isinstance(data, str):
            # 20% Chance to replace a string with a Naughty String
            if random.random() < 0.2:
                return random.choice(NAUGHTY_STRINGS)
        elif isinstance(data, int) and not isinstance(data, bool):
            # 20% Chance to replace int with Overflow/DoS Integer
            if random.random() < 0.2:
                return random.choice(NAUGHTY_INTS)

        return data



if __name__ == '__main__':
    mutator = Mutator()
    data = mutator.mutate_json_structure({"a": 1, "b": [1, 2, 3], "c": "Hello World!", "d": "John Doe"})
    print(json.dumps(data, indent=4))

    data = mutator.bit_flip("Hello World!")
    print(data)
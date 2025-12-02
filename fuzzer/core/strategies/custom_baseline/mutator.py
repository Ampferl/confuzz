import random
import json


class Mutator:
    def __init__(self, list_name: str = "custom"):
        self.string_list = self.load_list(list_name)
        print(f"Loaded {len(self.string_list)} strings from {list_name}.txt")

    def load_list(self, filename: str) -> list:
        with open(f"../assets/lists/{filename}.txt", "r") as f:
            lines = f.read().splitlines()
            # Remove if line is empty or starts with #
            cleaned = [line.strip() for line in lines]
            return [line for line in cleaned if line and not line.startswith("#")]
            return lines

    def bit_flip(self, data: str, probability: float = 0.05) -> str:
        data_list = list(data)
        for i in range(len(data_list)):
            if random.random() < probability:
                # Replace current char with a random ASCII char
                data_list[i] = chr(random.randint(32, 126))
        return "".join(data_list)

    def mutate_json_structure(self, data: dict) -> dict:
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = self.mutate_json_structure(value)
        elif isinstance(data, list):
            for i in range(len(data)):
                data[i] = self.mutate_json_structure(data[i])
        elif isinstance(data, str) or (isinstance(data, int) and not isinstance(data, bool)):
            # 20% Chance to replace a string with a Naughty String
            if random.random() < 0.2:
                return random.choice(self.string_list)

        return data



if __name__ == '__main__':
    mutator = Mutator("blns")
    data = mutator.mutate_json_structure({"a": 1, "b": [1, 2, 3], "c": "Hello World!", "d": "John Doe"})
    print(json.dumps(data, indent=4))

    data = mutator.bit_flip("Hello World!")
    print(data)
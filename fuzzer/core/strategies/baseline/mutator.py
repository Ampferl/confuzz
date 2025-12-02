import random
import json

###################################################################################
## This Baseline Fuzzer is based on the MutationFuzzer of the fuzzing book       ##
## Github: https://github.com/uds-se/fuzzingbook/                                ##
## Website: https://www.fuzzingbook.org/                                         ##
## Copyright (c) 2018-2020 Saarland University, CISPA, authors, and contributors ##
###################################################################################

class Mutator:
    @staticmethod
    def delete_random_character(s: str) -> str:
        if s == "":
            return s

        pos = random.randint(0, len(s) - 1)
        # print("Deleting", repr(s[pos]), "at", pos)
        return s[:pos] + s[pos + 1:]

    @staticmethod
    def insert_random_character(s: str) -> str:
        """Returns s with a random character inserted"""
        pos = random.randint(0, len(s))
        random_character = chr(random.randrange(32, 127))
        # print("Inserting", repr(random_character), "at", pos)
        return s[:pos] + random_character + s[pos:]

    @staticmethod
    def flip_random_character(s):
        """Returns s with a random bit flipped in a random position"""
        if s == "":
            return s

        pos = random.randint(0, len(s) - 1)
        c = s[pos]
        bit = 1 << random.randint(0, 6)
        new_c = chr(ord(c) ^ bit)
        # print("Flipping", bit, "in", repr(c) + ", giving", repr(new_c))
        return s[:pos] + new_c + s[pos + 1:]


if __name__ == '__main__':
    mutator = Mutator("blns")
    data = mutator.mutate_json_structure({"a": 1, "b": [1, 2, 3], "c": "Hello World!", "d": "John Doe"})
    print(json.dumps(data, indent=4))

    data = mutator.bit_flip("Hello World!")
    print(data)
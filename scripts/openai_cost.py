import json
import argparse

pricing = {
    "gpt-5": {
        "input": 1.25,
        "output": 10.00
    },
    "gpt-5-mini": {
        "input": 0.25,
        "output": 2.00
    },
    "gpt-5-nano": {
        "input": 0.05,
        "output": 0.40
    }
}

def calculate_cost(usage, model="gpt-5"):

    if model not in pricing:
        return None

    input_cost = (usage["prompt_tokens"] * pricing[model]["input"]) / 1_000_000
    output_cost = (usage["completion_tokens"] * pricing[model]["output"]) / 1_000_000
    total_cost = input_cost + output_cost

    return total_cost


def load_cost_file(filename):
    with open(filename, "r") as f:
        return json.load(f)

def get_total_tokens(data):
    result = {
        "prompt_tokens": 0,
        "completion_tokens": 0
    }
    for item in data:
        result["prompt_tokens"] += item["prompt_tokens"]
        result["completion_tokens"] += item["completion_tokens"]
    return result



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default="cost.json", help='Path to JSON file containing OpenAI usage data')
    parser.add_argument('--model', default="gpt-5", choices=pricing.keys(), help='Model to estimate cost for')
    args = parser.parse_args()
    data = load_cost_file(args.file)
    total_tokens = get_total_tokens(data)
    print(f"Prompt Tokens (Input): {total_tokens['prompt_tokens']}")
    print(f"Completion Tokens (Output): {total_tokens['completion_tokens']}")

    cost = calculate_cost(total_tokens, model=args.model)
    print(f"Estimated Cost: ${cost:.6f}")
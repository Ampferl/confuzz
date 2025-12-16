import json
import argparse
import statistics

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


def calculate_stats(data, model="gpt-5"):
    usage = get_total_tokens(data)
    total_cost = calculate_cost(usage, model)

    mean_prompt_tokens = statistics.mean([d["prompt_tokens"] for d in data])
    mean_completion_tokens = statistics.mean([d["completion_tokens"] for d in data])
    mean_cost = statistics.mean([calculate_cost(d, model) for d in data])

    median_prompt_tokens = statistics.median([d["prompt_tokens"] for d in data])
    median_completion_tokens = statistics.median([d["completion_tokens"] for d in data])
    median_cost = statistics.median([calculate_cost(d, model) for d in data])

    return {
        "mean": {
            "prompt_tokens": mean_prompt_tokens,
            "completion_tokens": mean_completion_tokens,
            "cost": mean_cost
        },
        "median": {
            "prompt_tokens": median_prompt_tokens,
            "completion_tokens": median_completion_tokens,
            "cost": median_cost
        },
        "total":{
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "cost": total_cost
        }
    }

def calculate_total_stats(file_stats, model="gpt-5"):
    total_prompt_tokens = [file_stats[f]['total']['prompt_tokens'] for f in file_stats]
    total_completion_tokens = [file_stats[f]['total']['completion_tokens'] for f in file_stats]
    total_cost = [file_stats[f]['total']['cost'] for f in file_stats]

    mean_prompt_tokens = statistics.mean(total_prompt_tokens)
    mean_completion_tokens = statistics.mean(total_completion_tokens)
    mean_cost = statistics.mean(total_cost)

    median_prompt_tokens = statistics.median(total_prompt_tokens)
    median_completion_tokens = statistics.median(total_completion_tokens)
    median_cost = statistics.median(total_cost)
    return {
        "mean": {
            "prompt_tokens": mean_prompt_tokens,
            "completion_tokens": mean_completion_tokens,
            "cost": mean_cost
        },
        "median": {
            "prompt_tokens": median_prompt_tokens,
            "completion_tokens": median_completion_tokens,
            "cost": median_cost
        },
        "total":{
            "prompt_tokens": sum(total_prompt_tokens),
            "completion_tokens": sum(total_completion_tokens),
            "cost": sum(total_cost)
        }
    }

def print_stats(stats, name=""):
    print('='*50)
    print('-'*20 + f" {name} " + '-'*(28-(len(name))))
    print('='*50)
    print(f"Mean Prompt Tokens: {stats['mean']['prompt_tokens']:.2f}")
    print(f"Mean Completion Tokens: {stats['mean']['completion_tokens']:.2f}")
    print(f"Mean Cost: ${stats['mean']['cost']:.5f}")
    print('-'*50)
    print(f"Median Prompt Tokens: {stats['median']['prompt_tokens']:.2f}")
    print(f"Median Completion Tokens: {stats['median']['completion_tokens']:.2f}")
    print(f"Median Cost: ${stats['median']['cost']:.5f}")
    print('-'*50)
    print(f"Total Prompt Tokens: {stats['total']['prompt_tokens']:.2f}")
    print(f"Total Completion Tokens: {stats['total']['completion_tokens']:.2f}")
    print(f"Total Cost: ${stats['total']['cost']:.2f}")
    print('-'*50)

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


def custom():

    file_stats = {
        "gpt-5": {},
        "gpt-5-mini": {},
        "gpt-5-nano": {}
    }
    for model in file_stats.keys():
        for i in range(1, 6):
            file = load_cost_file(f"{model}/0{i}_cost.json")
            stats = calculate_stats(file, model)
            file_stats[model][i] = stats
        total_stats = calculate_total_stats(file_stats[model], model)
        print_stats(total_stats, name=model)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default="cost.json", help='Path to JSON file containing OpenAI usage data')
    parser.add_argument("--detailed", action="store_true", help="Print detailed statistics (prompt/completion tokens, cost)")
    parser.add_argument('--model', default="gpt-5", choices=pricing.keys(), help='Model to estimate cost for')
    args = parser.parse_args()
    custom()
    exit(0)
    files = args.file.split(",")
    file_stats = {}
    for file in files:
        try:
            data = load_cost_file(file)
            stats = calculate_stats(data, args.model)
            file_stats[file] = stats
            if args.detailed:
                print_stats(stats, name=file)
        except Exception as e:
            print(f"File '{file}' not found.")

    total_stats = calculate_total_stats(file_stats, args.model)
    print_stats(total_stats, name="Total")

import subprocess
import argparse
import os
import shutil
import json

RUNS_PER_MODEL = 5
START_AT = 1


MODEL_CONFIGS = [
    # Finished
    #{"strategy": "baseline", "model": "baseline", "requests": 1000},
    #{"strategy": "llm", "model": "qwen3:8b", "requests": 1000},
    #{"strategy": "llm", "model": "qwen3:1.7b", "requests": 1000},
    #{"strategy": "llm", "model": "qwen3:0.6b", "requests": 1000},
    #{"strategy": "llm", "model": "deepseek-r1:8b", "requests": 1000},
    #{"strategy": "llm", "model": "gpt-5", "requests": 1000},
    #{"strategy": "llm", "model": "gpt-5-nano", "requests": 1000},

    # ToDo
    {"strategy": "llm", "model": "gpt-5-mini", "requests": 1000},
    {"strategy": "llm", "model": "deepseek-r1:1.5b", "requests": 1000},
]

BASE_EVAL_DIR = "../evaluation"
SOURCE_FUZZER_LOG = "fuzzer_eval.log"
SOURCE_CONSUMER_LOG = "../test-environment/consumer/consumer_eval.log"
SOURCE_COST_LOG = "cost.json"



def run_evaluation():
    print(f"--- Starting Automated Evaluation ({len(MODEL_CONFIGS)} models, {RUNS_PER_MODEL} runs each) ---")

    for config in MODEL_CONFIGS:
        strategy = config["strategy"]
        model_name = config["model"]
        max_requests = config["requests"]


        target_dir = os.path.join(BASE_EVAL_DIR, model_name)
        os.makedirs(target_dir, exist_ok=True)

        for run_id in range(START_AT, RUNS_PER_MODEL + START_AT):
            print(f"\n[Run {run_id}/{RUNS_PER_MODEL}] Executing fuzzer...")

            cmd = [
                "python3", "main.py",
                "--strategy", strategy,
                "--model", model_name,
                "--auto",
                "--max-requests", str(max_requests)
            ]

            try:
                result = subprocess.run(cmd, check=True)

                print(f"[Run {run_id}/{RUNS_PER_MODEL}] Execution finished. Moving files...")

                dst_fuzz = os.path.join(target_dir, f"0{run_id}_fuzz.log")
                if os.path.exists(SOURCE_FUZZER_LOG):
                    shutil.move(SOURCE_FUZZER_LOG, dst_fuzz)
                else:
                    print(f"  -> Warning: {SOURCE_FUZZER_LOG} not found.")

                dst_cons = os.path.join(target_dir, f"0{run_id}_cons.log")
                if os.path.exists(SOURCE_CONSUMER_LOG):
                    shutil.copy2(SOURCE_CONSUMER_LOG, dst_cons)
                else:
                    print(f"  -> Warning: {SOURCE_CONSUMER_LOG} not found.")


                dst_cost = os.path.join(target_dir, f"0{run_id}_cost.json")
                if os.path.exists(SOURCE_COST_LOG):
                    shutil.move(SOURCE_COST_LOG, dst_cost)

            except subprocess.CalledProcessError as e:
                print(f"Error: Run {run_id} failed for model {model_name}.")
                print(f"Command: {' '.join(cmd)}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

    print("\n--- All evaluations completed successfully ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=RUNS_PER_MODEL, help="Number of runs per model (default: 5)")
    parser.add_argument("--start", type=int, default=START_AT, help="Start at run ID (default: 1)")
    args = parser.parse_args()
    if args.runs > 0: RUNS_PER_MODEL = args.runs
    if args.start > 0: START_AT = args.start

    if not os.path.exists("main.py"):
        print("Please run this script in the 'fuzzer/' directory.")
    else:
        run_evaluation()
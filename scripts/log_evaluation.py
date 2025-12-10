import json
import re
import argparse
import sys
import os
from datetime import datetime
from collections import defaultdict

# --- CONFIGURATION ---
ALL_SCENARIOS = {0, 1, 2, 3, 4, 5}


class EvaluationMetrics:
    def __init__(self):
        # Ground truth now stores both successful and failed attempts
        # {scenario_id: {'exploited': bool, 'timestamp': datetime, ...}}
        self.ground_truth = defaultdict(list)
        self.fuzzer_findings = set()  # {scenario_id} - Scenarios the Fuzzer claimed to find
        self.start_time = None
        self.scenarios_attempted = set()  # Scenarios that appeared in logs (regardless of success)

        # Confusion Matrix Counters (Global count across all log entries)
        self.tp_count = 0
        self.fn_count = 0
        self.tn_count = 0
        self.fp_count = 0

    def parse_consumer_log(self, filepath):
        """
        Parses the consumer log to establish the GROUND TRUTH.
        Distinguishes between attempted exploits vs successful exploits.
        """
        print(f"[*] Parsing Ground Truth from: {filepath}")

        if not os.path.exists(filepath):
            print(f"[!] Error: File {filepath} not found.")
            return False

        with open(filepath, 'r') as f:
            for line in f:
                # Regex to extract the JSON part after the logging prefix
                match = re.search(r' - ({.*})', line)
                if match:
                    json_str = match.group(1)
                    try:
                        entry = json.loads(json_str)
                        scenario = entry.get("scenario")
                        self.scenarios_attempted.add(scenario)

                        # Handle timestamp
                        ts_str = entry.get("timestamp")
                        if ts_str:
                            timestamp = datetime.fromisoformat(ts_str)
                            if self.start_time is None or timestamp < self.start_time:
                                self.start_time = timestamp
                        else:
                            timestamp = datetime.now()

                        exploited = entry.get("exploited")
                        exposed = entry.get("exposed")

                        # --- CONFUSION MATRIX LOGIC PER ENTRY ---
                        if exploited and exposed:
                            self.tp_count += 1
                        elif exploited and not exposed:
                            self.fn_count += 1
                        elif not exploited and not exposed:
                            self.tn_count += 1
                        elif not exploited and exposed:
                            self.fp_count += 1  # System wasn't exploited but leaked info/flagged

                        self.ground_truth[scenario].append({
                            "timestamp": timestamp,
                            "payload": entry.get("payload_received"),
                            "details": entry.get("details"),
                            "status_code": entry.get("status_code"),
                            "exploited": exploited,
                            "exposed": exposed
                        })
                    except json.JSONDecodeError:
                        continue

        # Identify which scenarios actually had a successful exploit
        confirmed_exploits = [
            s for s, entries in self.ground_truth.items()
            if any(e['exploited'] for e in entries)
        ]
        print(f"[*] Found confirmed exploits for scenarios: {sorted(confirmed_exploits)}")
        return True

    def load_fuzzer_results(self, filepath):
        """
        Loads the fuzzer's claims from a JSON file.
        """
        print(f"[*] Loading Fuzzer Findings from: {filepath}")

        if not os.path.exists(filepath):
            # If no file is provided or doesn't exist, we assume empty findings for partial runs
            print(f"[!] Warning: File {filepath} not found. Assuming no fuzzer findings.")
            return True

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.fuzzer_findings = set(data)
                elif isinstance(data, dict) and "findings" in data:
                    self.fuzzer_findings = set(data["findings"])
                else:
                    print("[!] Unknown fuzzer report format.")
                    return False

            print(f"[*] Fuzzer claims to have found: {sorted(list(self.fuzzer_findings))}")
            return True
        except json.JSONDecodeError:
            print(f"[!] Error: Could not decode JSON from {filepath}")
            return False

    def print_ground_truth_details(self):
        """Prints details about what was found in the Consumer Log."""
        print("\n--- GROUND TRUTH ANALYSIS (Consumer Log) ---")
        if not self.ground_truth:
            print("No entries found in the log.")
            return

        print(f"{'Scenario':<10} | {'Attempts':<8} | {'Successes':<9} | {'Details (Last Entry)'}")
        print("-" * 100)

        for scenario in sorted(self.ground_truth.keys()):
            entries = sorted(self.ground_truth[scenario], key=lambda x: x['timestamp'])
            attempts = len(entries)
            successes = sum(1 for e in entries if e['exploited'])

            last_entry = entries[-1]
            details = last_entry['details'][:40] + "..." if len(last_entry['details']) > 40 else last_entry['details']

            print(f"S{scenario:<9} | {attempts:<8} | {successes:<9} | {details}")

    def calculate_efficiency(self):
        """Calculates Time-To-First-SUCCESSFUL-Exploit for each scenario."""
        if not self.ground_truth:
            return

        print("\n--- EFFICIENCY (Time to First Successful Exploit) ---")
        print(f"{'Scenario':<10} | {'Time to Discovery (s)':<25}")
        print("-" * 60)

        for scenario in sorted(self.ground_truth.keys()):
            # Filter for successful exploits only
            successful_exploits = [e for e in self.ground_truth[scenario] if e['exploited']]

            if not successful_exploits:
                print(f"S{scenario:<9} | {'Not Exploited':<25}")
                continue

            first_success = sorted(successful_exploits, key=lambda x: x['timestamp'])[0]

            if self.start_time:
                delta = first_success['timestamp'] - self.start_time
                time_to_first = f"{delta.total_seconds():.4f}s"
            else:
                time_to_first = "Unknown Start Time"

            print(f"S{scenario:<9} | {time_to_first:<25}")

    def print_confusion_matrix(self):
        """Prints the Confusion Matrix based on individual attempts."""
        print("\n--- CONFUSION MATRIX (Per Attempt) ---")
        print(f"{'':<15} | {'Predicted Positive':<18} | {'Predicted Negative':<18}")
        print("-" * 60)
        print(f"{'Actual Positive':<15} | {self.tp_count:<18} (TP) | {self.fn_count:<18} (FN)")
        print(f"{'Actual Negative':<15} | {self.fp_count:<18} (FP) | {self.tn_count:<18} (TN)")

        total = self.tp_count + self.tn_count + self.fp_count + self.fn_count
        if total > 0:
            accuracy = (self.tp_count + self.tn_count) / total
            precision = self.tp_count / (self.tp_count + self.fp_count) if (self.tp_count + self.fp_count) > 0 else 0
            recall = self.tp_count / (self.tp_count + self.fn_count) if (self.tp_count + self.fn_count) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            print("\n--- METRICS ---")
            print(f"Accuracy:  {accuracy:.2f}")
            print(f"Precision: {precision:.2f}")
            print(f"Recall:    {recall:.2f}")
            print(f"F1 Score:  {f1:.2f}")

    def calculate_effectiveness(self):
        """Calculates Scenario-Level Effectiveness (Did we find the bug eventually?)."""
        print("\n--- SCENARIO-LEVEL EFFECTIVENESS ---")

        # Define the set of scenarios that were ACTUALLY exploited (Ground Truth Positive)
        actual_positives = {
            s for s, entries in self.ground_truth.items()
            if any(e['exploited'] for e in entries)
        }

        # Define the set of scenarios that were NOT exploited (Ground Truth Negative)
        actual_negatives = ALL_SCENARIOS - actual_positives

        # Confusion Matrix Logic
        # TP: Fuzzer claims found AND it was actually exploited
        tp = self.fuzzer_findings.intersection(actual_positives)

        # FP: Fuzzer claims found BUT it was NOT actually exploited
        fp = self.fuzzer_findings.intersection(actual_negatives)

        # FN: Fuzzer claims NOT found BUT it WAS actually exploited
        fn = actual_positives - self.fuzzer_findings

        # TN: Fuzzer claims NOT found AND it was NOT actually exploited
        tn = actual_negatives - self.fuzzer_findings

        print(f"True Positives  (TP): {len(tp)} {sorted(list(tp))}")
        print(f"False Positives (FP): {len(fp)} {sorted(list(fp))}")
        print(f"False Negatives (FN): {len(fn)} {sorted(list(fn))}")
        print(f"True Negatives  (TN): {len(tn)} {sorted(list(tn))}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate ConFuzz Empirical Results")

    # Simple arguments instead of subparsers
    parser.add_argument('--consumer-log', help='Path to consumer_eval.log (Ground Truth)')
    parser.add_argument('--fuzzer-log', help='Path to fuzzer_report.json (Fuzzer Findings)')

    args = parser.parse_args()
    evaluator = EvaluationMetrics()

    # Load data based on provided arguments
    has_consumer = False
    has_fuzzer = False

    if args.consumer_log:
        has_consumer = evaluator.parse_consumer_log(args.consumer_log)

    if args.fuzzer_log:
        has_fuzzer = evaluator.load_fuzzer_results(args.fuzzer_log)

    # Execution logic
    if has_consumer:
        evaluator.print_ground_truth_details()
        evaluator.calculate_efficiency()
        evaluator.print_confusion_matrix()

    if has_consumer or has_fuzzer:
        if has_consumer:
            evaluator.calculate_effectiveness()
        else:
            print("\n[!] Cannot calculate effectiveness metrics without Consumer Log (Ground Truth).")


if __name__ == "__main__":
    main()
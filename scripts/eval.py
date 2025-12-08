import json
import re
import argparse
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import hashlib
import matplotlib.pyplot as plt
import numpy as np


class LogParser:
    def __init__(self, debug=False):
        self.fuzzer_entries = []
        self.consumer_entries = []
        self.scenarios = set()
        self.debug = debug
        self.matched_requests = []

    def parse_file(self, filepath, source_type):
        print(f"[*] Parsing {source_type} log: {filepath}")
        if not os.path.exists(filepath):
            print(f"[!] File not found: {filepath}")
            return

        with open(filepath, 'r') as f:
            for line in f:
                match = re.search(r' - ({.*})', line)
                if match:
                    json_str = match.group(1)
                    try:
                        entry = json.loads(json_str)

                        ts_str = entry.get("timestamp")
                        if not ts_str and "feedback" in entry and entry["feedback"]:
                            ts_str = entry["feedback"][0].get("timestamp")

                        if ts_str:
                            entry["_dt"] = datetime.fromisoformat(ts_str)

                        if source_type == "fuzzer":
                            if "fuzzed" in entry:
                                entry["_payload_hash"] = self._hash_payload(entry["fuzzed"])
                            self.fuzzer_entries.append(entry)
                        else:
                            if "payload_received" in entry:
                                entry["_payload_hash"] = self._hash_payload(entry["payload_received"])

                            self.consumer_entries.append(entry)
                            if "scenario" in entry:
                                self.scenarios.add(entry["scenario"])

                    except json.JSONDecodeError:
                        continue

    def _hash_payload(self, payload):
        if not payload: return ""
        normalized = str(payload).strip()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def _print_debug_info(self, title, f_entry, c_entry):
        print(f"\n--- DEBUG: {title} ---")
        print(f"Scenario: S{c_entry.get('scenario', '?')}")
        print("Fuzzer Log Entry:")
        print(json.dumps(f_entry, indent=2, default=str))
        print("Consumer Log Entry:")
        print(json.dumps(c_entry, indent=2, default=str))
        print("-" * 40)


    def get_matching_requests(self):
        data = []
        consumer_lookup = defaultdict(list)
        for entry in self.consumer_entries:
            if "_payload_hash" in entry:
                consumer_lookup[entry["_payload_hash"]].append(entry)

        for f_entry in self.fuzzer_entries:
            f_hash = f_entry.get("_payload_hash")
            if not f_hash: continue
            matches = consumer_lookup.get(f_hash)

            if matches:
                # get only matches which are in the same scenario
                matches.sort(key=lambda x: abs(x["_dt"] - f_entry["_dt"]))
                data.append({
                    "consumer": matches.pop(0),
                    "fuzzer": f_entry
                })
        self.matched_requests = data
        return data

    def draw_confusion_matrix(self, metrics):
        tp = metrics["tp"]
        fp = metrics["fp"]
        fn = metrics["fn"]
        tn = metrics["tn"]
        print(f"{'':<15} | {'Predicted Positive':<23} | {'Predicted Negative':<18}")
        print("-" * 67)
        print(f"{'Actual Positive':<15} | {tp:<18} (TP) | {fn:<18} (FN)")
        print(f"{'Actual Negative':<15} | {fp:<18} (FP) | {tn:<18} (TN)")

    def draw_scenario_table(self):
        tbl_head = f"{'Scenario':<10} | {'Requests':<10} | {'Exploited (Ground Truth)':<25} | {'Detected by Fuzzer':<30} | {'Fuzzer Latency':<25} | {'TP':<5} | {'FP':<5} | {'FN':<5} | {'TN':<5} | {'Recall':<6} | {'Total Time':<11}"
        print(tbl_head)
        print("-" * len(tbl_head))


        for scenario_id in sorted(list(self.scenarios)):
            c_logs = [e.get('consumer') for e in self.matched_requests if e.get('consumer').get("scenario") == scenario_id]
            req_count = len(c_logs)
            exploited_consumer = any(e.get("exploited") is True for e in c_logs)

            f_logs_for_scenario = [
                e.get('fuzzer') for e in self.matched_requests
                if any(f.get("scenario") == scenario_id for f in e.get('fuzzer').get("feedback", []))
            ]

            exploited_fuzzer = any(
                any(f.get("exploited") is True for f in e.get("feedback", []))
                for e in f_logs_for_scenario
            )

            c_status = "YES" if exploited_consumer else "NO"
            f_status = "YES" if exploited_fuzzer else "NO"

            start_dt = f_logs_for_scenario[0]["_dt"]

            metrics = self.get_scenario_metrics(scenario_id)

            if exploited_fuzzer:
                success_entry = None
                tries = 0
                for s in f_logs_for_scenario:
                    tries += 1
                    for e in s.get("feedback", []):
                        if e.get("exploited") is True:
                            success_entry = s
                            break
                delta = success_entry["_dt"] - start_dt
                time_to_exploit = f"{delta.total_seconds():.2f}s"
                f_status += f" ({time_to_exploit}) (Attempt: {tries})"
            if exploited_consumer:
                tries = 0
                for e in c_logs:
                    tries += 1
                    if e.get("exploited") is True:
                        break
                c_status += f" (Attempt: {tries})"
            lat_avg = metrics["latency"]["avg"]
            lat_med = metrics["latency"]["median"]
            latency_str = f"Avg={lat_avg:.2f}s Median={lat_med:.2f}s"

            total_time = f'{metrics["total_time"]:.2f}s'
            print(f"S{scenario_id:<9} | {req_count:<10} | {c_status:<25} | {f_status:<30} | {latency_str:<25} | {metrics['tp']:<5} | {metrics['fp']:<5} | {metrics['fn']:<5} | {metrics['tn']:<5} | {metrics['recall']:<.2%} | {total_time:<11}")


    def get_scenario_metrics(self, scenario_id):
        tp = 0
        fp = 0
        fn = 0
        tn = 0
        latencies = []
        request_count = 0
        scenario_entries = []
        for entry in self.matched_requests:
            if entry["consumer"].get("scenario") != scenario_id: continue
            scenario_entries.append(entry.get("fuzzer"))
            request_count += 1
            consumer_entry = entry["consumer"]
            fuzzer_entry = entry["fuzzer"]
            is_exploited_real = consumer_entry.get("exploited", False)
            is_detected_fuzzer = fuzzer_entry.get("feedback", []) and any(
                fb.get("exploited") is True for fb in fuzzer_entry["feedback"])
            if is_exploited_real and is_detected_fuzzer:
                tp += 1
            elif not is_exploited_real and is_detected_fuzzer:
                fp += 1
            elif is_exploited_real and not is_detected_fuzzer:
                fn += 1
            elif not is_exploited_real and not is_detected_fuzzer:
                tn += 1
            latencies.append(fuzzer_entry["feedback"][0]["latency"]["fuzzer"])

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        latency = {
            "avg": statistics.mean(latencies) if latencies else 0.0,
            "median": statistics.median(latencies) if latencies else 0.0
        }
        total_time = float((scenario_entries[-1]["_dt"] - scenario_entries[0]["_dt"] + datetime.fromtimestamp(scenario_entries[-1]["feedback"][0]["latency"]["total"])).strftime('%S.%f'))

        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": recall, "latency": latency, "request_count": request_count, "total_time": total_time}

    def get_total_metrics(self):
        tp = 0
        fp = 0
        fn = 0
        tn = 0
        request_count = len(self.matched_requests)
        latencies = []
        for entry in self.matched_requests:
            consumer_entry = entry["consumer"]
            fuzzer_entry = entry["fuzzer"]
            is_exploited_real = consumer_entry.get("exploited", False)
            is_detected_fuzzer = fuzzer_entry.get("feedback", []) and any(fb.get("exploited") is True for fb in fuzzer_entry["feedback"])
            if is_exploited_real and is_detected_fuzzer:
                tp += 1
            elif not is_exploited_real and is_detected_fuzzer:
                fp += 1
                self._print_debug_info("False Positive", fuzzer_entry, consumer_entry)
            elif is_exploited_real and not is_detected_fuzzer:
                fn += 1
            elif not is_exploited_real and not is_detected_fuzzer:
                tn += 1
            latencies.append(fuzzer_entry["feedback"][0]["latency"]["fuzzer"])

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        latency = {
            "avg": statistics.mean(latencies) if latencies else 0.0,
            "median": statistics.median(latencies) if latencies else 0.0
        }
        total_time = float((self.fuzzer_entries[-1]["_dt"] - self.fuzzer_entries[0]["_dt"] + datetime.fromtimestamp(self.fuzzer_entries[-1]["feedback"][0]["latency"]["total"])).strftime('%S.%f'))
        throughput = request_count / total_time

        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": recall, "latency": latency, "request_count": request_count, "total_time": total_time, "throughput": throughput}


def analyze(fuzzer_log, consumer_log):
    analyzer = LogParser()
    analyzer.parse_file(fuzzer_log, "fuzzer")
    analyzer.parse_file(consumer_log, "consumer")
    print("\n")
    data = analyzer.get_matching_requests()
    print(f"Matching Requests: {len(data)}")
    metrics = analyzer.get_total_metrics()

    analyzer.draw_scenario_table()
    print("\n")
    analyzer.draw_confusion_matrix(metrics)
    print("\n")
    print(f"Recall: {metrics['recall']:.2%}")
    print(f"Total Time: {metrics['total_time']:.2f}s")
    print(f"Throughput: {metrics['throughput']:.2f} req/min")
    print(f"Latency: Avg: {metrics['latency']['avg']:.4f}s, Median: {metrics['latency']['median']:.4f}s")


def plot_timeline(d):
    plt.figure(figsize=(12, 6))

    all_scenarios = set()

    for run_id, data in d.items():
        requests = data['logParser'].matched_requests
        if not requests:
            print(f"[!] No requests found for Run {run_id}")
            continue

        requests.sort(key=lambda x: x['fuzzer']['_dt'])

        start_time = requests[0]['fuzzer']['_dt']

        x_time = []
        y_scenario = []

        for req in requests:
            duration = (req['fuzzer']['_dt'] - start_time).total_seconds()
            raw_scen = req['fuzzer'].get('feedback')[0].get('scenario')
            try:
                scen_val = int(raw_scen)
            except (ValueError, TypeError):
                scen_val = raw_scen

            x_time.append(duration)
            y_scenario.append(scen_val)
            all_scenarios.add(scen_val)

        fuzzer_name = run_id.split("/")[0].replace("_", ":")
        fuzzer_run = run_id.split("/")[1]
        plt.plot(x_time, y_scenario, drawstyle="steps-post", marker='o',
                 markersize=4, label=f"{fuzzer_name}[{fuzzer_run}]", alpha=0.8)

    plt.title("Fuzzer Progression: Scenario Execution over Time")
    plt.xlabel("Duration (seconds)")
    plt.ylabel("Scenario ID")

    try:
        sorted_scenarios = sorted(list(all_scenarios))
        plt.yticks(sorted_scenarios)
    except:
        pass

    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.legend()
    plt.tight_layout()


    plt.show()


def generate_latex_tables(d):
    all_scenarios = set()
    for run_id, data in d.items():
        all_scenarios.update(data['logParser'].scenarios)

    try:
        sorted_scenarios = sorted(list(all_scenarios), key=lambda x: int(x))
    except ValueError:
        sorted_scenarios = sorted(list(all_scenarios))

    def print_table(title, content_extractor):
        cols = "|l|" + "c|" * len(sorted_scenarios)

        print(f"% --- {title} ---")
        print("\\begin{table}[h]")
        print("\\centering")
        print(f"\\begin{{tabular}}{{{cols}}}")
        print("\\hline")

        headers = ["Run"] + [f"S{s}" for s in sorted_scenarios]
        print(" & ".join(headers) + " \\\\")
        print("\\hline")

        for run_id, data in d.items():
            fuzzer_name = run_id.split("/")[0].replace("_", ":")
            row_data = [f"{fuzzer_name}"]
            requests = data['logParser'].matched_requests

            for s_id in sorted_scenarios:
                s_requests = [
                    r for r in requests
                    if str(r['consumer'].get('scenario')) == str(s_id)
                ]

                value = content_extractor(s_requests)
                row_data.append(str(value))

            print(" & ".join(row_data) + " \\\\")
            print("\\hline")

        print("\\end{tabular}")
        print(f"\\caption{{{title}}}")
        print("\\end{table}")
        print("\n")

    def get_ttfb(requests):
        if not requests:
            return "-"

        requests.sort(key=lambda x: x['fuzzer']['_dt'])
        start_time = requests[0]['fuzzer']['_dt']

        for req in requests:
            f_entry = req['fuzzer']
            is_exploited = any(fb.get("exploited") is True for fb in f_entry.get("feedback", []))

            if is_exploited:
                latency = f_entry.get("feedback", [])[0].get("latency").get("total")
                delta = float((f_entry['_dt'] - start_time + datetime.fromtimestamp(latency)).strftime('%S.%f'))
                return f"{delta:.2f}s"

        return "N/A"

    def get_req_count(requests):
        if not requests:
            return "0"
        return len(requests)

    print("\n" + "=" * 20 + " LATEX OUTPUT " + "=" * 20)
    print_table("Time to First Bug per Scenario", get_ttfb)
    print_table("Total Requests per Scenario", get_req_count)
    print("=" * 54 + "\n")

def comp(compare, args):
    d = {}
    for c in compare:
        fuzzer_log = f"{c}_fuzz.log"
        consumer_log = f"{c}_cons.log"
        if not os.path.exists(fuzzer_log) or not os.path.exists(consumer_log):
            print(f"[!] Log file not found: {fuzzer_log} or {consumer_log}")
            return
        logParser = LogParser()
        logParser.parse_file(fuzzer_log, "fuzzer")
        logParser.parse_file(consumer_log, "consumer")
        logParser.get_matching_requests()

        scenario_metrics = [logParser.get_scenario_metrics(s) for s in logParser.scenarios]
        d[c] = {
            "logParser": logParser,
            "total_metrics": logParser.get_total_metrics(),
            "scenario_metrics": scenario_metrics
        }
    if args.analyze:
        print("-" * 40)
        avg_requests = sum(d[m]["total_metrics"]["request_count"] for m in d) / len(d)
        print(f"Average Requests: {avg_requests:.2f}")
        print("-" * 40)
        for c, v in d.items():
            print(f"=============== {c} ===============")
            print("Confusion Matrix:\n"
                f"TP: {v['total_metrics']['tp']:>5} | {v['total_metrics']['fp']:<5} :FP\n"
                f"{'-'*21}\n"
                f"FN: {v['total_metrics']['fn']:>5} | {v['total_metrics']['tn']:<5} :TN\n")
            print(f"Recall: {v['total_metrics']['recall']:.2%}")
            print(f"Requests: {v['total_metrics']['request_count']}")
            print(f"Total Time: {v['total_metrics']['total_time']:.2f}s")
            print(f"Throughput: {v['total_metrics']['throughput']:.2f} req/min")
            print(
                f"Latency: Avg: {v['total_metrics']['latency']['avg']:.4f}s, Median: {v['total_metrics']['latency']['median']:.4f}s")
            print("-" * 40)
    if args.latex:
        generate_latex_tables(d)
    if args.plot:
        plot_timeline(d)
    return d


def main():
    parser = argparse.ArgumentParser(description="ConFuzz Evaluation Script")
    parser.add_argument("--fuzzer-log", help="Path to fuzzer.log")
    parser.add_argument("--consumer-log", help="Path to consumer_eval.log")
    parser.add_argument("-p", "--prefix", help="Prefix of log files")
    parser.add_argument("--debug", action="store_true", help="Print JSON details for TP and FP")
    parser.add_argument("--latex", action="store_true", help="Print stuff in latex format")
    parser.add_argument("--plot", action="store_true", help="Plot diagrams")
    parser.add_argument("-a", "--analyze", action="store_true", help="Print analysis of a evaluation run")
    parser.add_argument("-c", "--compare", type=str, help="Print analysis of a evaluation run")

    args = parser.parse_args()
    compare = args.compare.split(",") if args.compare else []
    if compare:
        comp(compare, args)
    else:
        consumer_log = None
        fuzzer_log = None
        if args.prefix:
            fuzzer_log = f"{args.prefix}_fuzz.log"
            consumer_log = f"{args.prefix}_cons.log"
        elif args.fuzzer_log and args.consumer_log:
            fuzzer_log = args.fuzzer_log
            consumer_log = args.consumer_log
        if not fuzzer_log or not consumer_log:
            print("Please specify the prefix of the log files.")
            return
        if args.analyze:
            analyze(fuzzer_log, consumer_log)




if __name__ == "__main__":
    main()
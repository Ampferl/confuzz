import json
import re
import argparse
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import hashlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import numpy as np


def get_pastel_cm():
    pastel_colors = [
        "#ffadad",  # Pastel Red
        "#ffd6a5",  # Pastel Orange
        "#fdffb6",  # Pastel Yellow
        "#caffbf"  # Pastel Green
    ]

    cmap_name = 'pastel_rd_yl_gn'
    pastel_cmap = mcolors.LinearSegmentedColormap.from_list(cmap_name, pastel_colors)
    return pastel_cmap


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


    def draw_scenario_table(self):
        tbl_head = f"{'Scenario':<10} | {'Requests':<10} | {'Exploited (Ground Truth)':<25} | {'Detected by Fuzzer':<30} | {'Fuzzer Latency':<25} | {'TP':<5} | {'FN':<5} | {'Total Time':<11}"
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
            print(f"S{scenario_id:<9} | {req_count:<10} | {c_status:<25} | {f_status:<30} | {latency_str:<25} | {metrics['tp']:<5} |{metrics['fn']:<5} | {total_time:<11}")


    def get_scenario_metrics(self, scenario_id):
        tp = 0
        fn = 0
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
            try:
                latencies.append(fuzzer_entry["feedback"][0]["latency"]["fuzzer"])
            except:
                print(f"[!] No latency found for entry: {fuzzer_entry}")
        if tp == 0:
            fn += 1
        latency = {
            "avg": statistics.mean(latencies) if latencies else 0.0,
            "median": statistics.median(latencies) if latencies else 0.0
        }
        total_time = (scenario_entries[-1]["_dt"] - scenario_entries[0]["_dt"]).total_seconds() + float(datetime.fromtimestamp(scenario_entries[-1]["feedback"][0]["latency"]["total"]).strftime('%S.%f'))

        return {"tp": tp, "fn": fn, "latency": latency, "request_count": request_count, "total_time": total_time}

    def get_total_metrics(self):
        tp = 0
        fn = 0
        request_count = len(self.matched_requests)
        latencies = []

        for scenario_id in sorted(list(self.scenarios)):
            stats = self.get_scenario_metrics(scenario_id)
            tp += stats["tp"]
            fn += stats["fn"]


        for entry in self.matched_requests:
            fuzzer_entry = entry["fuzzer"]

            try:
                latencies.append(fuzzer_entry["feedback"][0]["latency"]["fuzzer"])
            except:
                print(f"[!] No latency found for entry: {fuzzer_entry}")


        latency = {
            "avg": statistics.mean(latencies) if latencies else 0.0,
            "median": statistics.median(latencies) if latencies else 0.0
        }
        total_time = (self.fuzzer_entries[-1]["_dt"] - self.fuzzer_entries[0]["_dt"]).total_seconds() + float(datetime.fromtimestamp(self.fuzzer_entries[-1]["feedback"][0]["latency"]["total"]).strftime('%S.%f'))

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        throughput = (request_count / total_time)*60

        return {"tp": tp, "fn": fn, "recall": recall, "latency": latency, "request_count": request_count, "total_time": total_time, "throughput": throughput}

class DataAggregator:
    def __init__(self, strategies):
        self.raw_data = self._pre_process(strategies)
        self.models = defaultdict(lambda: {
            "recalls": [],
            "latencies": [],
            "scenario_times": defaultdict(list),
            "scenario_success": defaultdict(list)
        })
        self.scenarios = set()
        self._process()

    def _pre_process(self, strategies):
        d = {}
        for c in strategies:
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


        return d

    def _process(self):
        for run_id, data in self.raw_data.items():

            if "/" in run_id:
                model_name = run_id.split("/")[0]
            else:
                model_name = "_".join(run_id.split("_")[:-1])

            metrics = data['total_metrics']
            self.models[model_name]["recalls"].append(metrics["recall"])
            self.models[model_name]["latencies"].append(metrics["latency"]["avg"])

            requests = data['logParser'].matched_requests
            if not requests: continue

            requests.sort(key=lambda x: x['fuzzer']['_dt'])
            start_dt = requests[0]['fuzzer']['_dt']

            run_scenarios = defaultdict(list)
            for req in requests:
                s_id = req['consumer'].get("scenario")
                if s_id is not None:
                    run_scenarios[s_id].append(req)
                    self.scenarios.add(s_id)

            for s_id, reqs in run_scenarios.items():
                exploited = False
                time_to_exploit = None

                for req in reqs:
                    if req['fuzzer'].get("feedback") and any(
                            fb.get("exploited") is True for fb in req['fuzzer']["feedback"]):
                        exploited = True
                        time_to_exploit = (req['fuzzer']['_dt'] - start_dt).total_seconds()
                        break

                if exploited:
                    self.models[model_name]["scenario_times"][s_id].append(time_to_exploit)
                    self.models[model_name]["scenario_success"][s_id].append(1)
                else:
                    self.models[model_name]["scenario_success"][s_id].append(0)

    def get_model_names(self):
        return sorted(list(self.models.keys()))

    def get_sorted_scenarios(self):
        try:
            return sorted(list(self.scenarios), key=lambda x: int(x))
        except:
            return sorted(list(self.scenarios))


    def analyze(self):
        d = self.raw_data
        total_requests = 0
        total_time = 0
        print("-" * 40)
        avg_requests = sum(d[m]["total_metrics"]["request_count"] for m in d) / len(d)
        print(f"Average Requests: {avg_requests:.2f}")
        print("-" * 40)
        for c, v in d.items():
            print(f"{'='*30} {c} {'='*(48-len(c))}")
            v["logParser"].draw_scenario_table()
            print(f"Recall: {d[c]['total_metrics']['recall']}")
            print(f"Total Requests: {d[c]['total_metrics']['request_count']}")
            print(f"Total Time: {d[c]['total_metrics']['total_time']}s")
            print("=" * 80)
            total_requests += d[c]["total_metrics"]["request_count"]
            total_time += d[c]["total_metrics"]["total_time"]
        print(f"Total Requests: {total_requests}")
        print(f"Total Time: {total_time:.2f}s")




def plot_vulnerability_coverage(agg):
    models = agg.get_model_names()
    scenarios = agg.get_sorted_scenarios()

    grid_data = np.zeros((len(models), len(scenarios)))

    for i, model in enumerate(models):
        for j, s_id in enumerate(scenarios):

            outcomes = agg.models[model]["scenario_success"].get(s_id, [])
            if outcomes:
                success_rate = sum(outcomes) / len(outcomes)
                grid_data[i, j] = success_rate
            else:
                grid_data[i, j] = 0.0

    fig, ax = plt.subplots(figsize=(10, 6))

    im = ax.imshow(grid_data, cmap=get_pastel_cm(), vmin=0, vmax=1, aspect='auto')

    ax.set_xticks(np.arange(len(scenarios)))
    ax.set_yticks(np.arange(len(models)))
    ax.set_xticklabels([f"Scenario {s}" for s in scenarios])
    ax.set_yticklabels(models)

    ax.set_xlabel("Scenario")
    ax.set_ylabel("Strategy")

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Average Detection Rate (0.0 to 1.0)", rotation=-90, va="bottom")

    for i in range(len(models)):
        for j in range(len(scenarios)):
            val = grid_data[i, j]
            ax.text(j, i, f"{val:.1%}", ha="center", va="center", color="black", fontweight='bold')

    plt.tight_layout()
    plt.show()

def latex_efficiency(agg):
    models = agg.get_model_names()

    print(r"% --- Overall Effectiveness and Efficiency ---")
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\resizebox{\textwidth}{!}{%")
    print(r"\begin{tabular}{|l|c|c|c|c|c|}")
    print(r"\hline")
    print(
        r"\textbf{Strategy} & \textbf{Detection Rate} & \textbf{Avg Latency} & \textbf{Avg Throughput} \\")
    print(r"\hline")

    for model in models:
        recalls = agg.models[model]["recalls"]
        latencies = agg.models[model]["latencies"]

        total_time = 0
        total_requests = 0
        total_latency = 0
        for run_id, run_data in agg.raw_data.items():
            if run_id.startswith(model):
                total_time += run_data['total_metrics']['total_time']
                total_requests += run_data['total_metrics']['request_count']
                total_latency += run_data['total_metrics']['latency']['avg'] * run_data['total_metrics']['request_count']

        avg_recall = np.mean(recalls) if recalls else 0.0
        avg_latency = total_latency / total_requests
        avg_throughput = (total_requests / total_time) * 60.0

        row = (
            f"{model} & "
            f"{avg_recall:.1%} & "
            f"{avg_latency:.2f}s & "
            f"{avg_throughput:.1f} req/min \\\\"
        )
        print(row.replace("%", "\\%"))
        print(r"\hline")

    print(r"\end{tabular}%")
    print(r"}")
    print(r"\caption{Overall Effectiveness and Efficiency by Strategy}")
    print(r"\label{tab:overall_effectiveness}")
    print(r"\end{table}")
    print("\n")


def plot_comparison_v2(agg):
    selected_models = [
        "baseline",
        "gpt-5-nano", "gpt-5-mini", "gpt-5",
        "qwen3:0.6b", "qwen3:1.7b", "qwen3:8b",
        "deepseek-r1:1.5b", "deepseek-r1:8b"
    ]

    target_scenario = "1"

    d = agg.raw_data
    stats = defaultdict(lambda: {'times': [], 'reqs': [], 'success': []})

    for run_id, data in d.items():
        if "/" in run_id:
            m = run_id.split("/")[0]
        else:
            parts = run_id.split("_")
            m = "_".join(parts[:-1]) if len(parts) > 1 else run_id

        if m not in selected_models:
            continue

        requests = data['logParser'].matched_requests
        if not requests: continue

        requests.sort(key=lambda x: x['fuzzer']['_dt'])

        scenario_start_time = None
        for req in requests:
            s_id = str(req['consumer'].get("scenario"))
            if s_id == target_scenario:
                current_ts = req['fuzzer']['_dt']
                if scenario_start_time is None or current_ts < scenario_start_time:
                    scenario_start_time = current_ts

        req_count = 0
        is_exploited = False
        exploit_time = None

        found_in_this_run = False

        for req in requests:
            s_id = str(req['consumer'].get("scenario"))
            if s_id == target_scenario:
                req_count += 1

                if req['fuzzer'].get("feedback") and any(
                        fb.get("exploited") is True for fb in req['fuzzer']["feedback"]):
                    is_exploited = True
                    exploit_time = req['fuzzer']['_dt']

                    latency_seconds = float(
                        datetime.fromtimestamp(req['fuzzer']["feedback"][0]["latency"]["total"]).strftime('%S.%f'))

                    if scenario_start_time:
                        duration = (exploit_time - scenario_start_time).total_seconds()
                        total_time = duration + latency_seconds

                        stats[m]['times'].append(total_time)
                        stats[m]['reqs'].append(req_count)
                        stats[m]['success'].append(1)
                        found_in_this_run = True
                        break

        if not found_in_this_run and req_count > 0:
            stats[m]['success'].append(0)
            stats[m]['reqs'].append(req_count)

    fig, ax = plt.subplots(figsize=(14, 8))

    max_time = 0
    for m in selected_models:
        if stats[m]['times']:
            max_time = max(max_time, np.mean(stats[m]['times']))

    VISUAL_CAP = max(max_time * 1.1, 10)

    y_pos = np.arange(len(selected_models))
    bar_height = 0.6

    for i, m in enumerate(selected_models):
        data = stats[m]

        success_rate = np.mean(data['success']) if data['success'] else 0.0
        avg_reqs = np.mean(data['reqs']) if data['reqs'] else 0

        is_timeout = success_rate == 0.0
        avg_time = np.mean(data['times']) if not is_timeout and data['times'] else VISUAL_CAP

        if "baseline" in m:
            color = '#ff9999'
        elif "qwen" in m:
            color = '#87cefa'
        elif "deepseek" in m:
            color = '#90ee90'
        elif "gpt" in m:
            color = '#dda0dd'
        else:
            color = 'lightgray'

        hatch = '//' if is_timeout else ''
        edge = 'red' if is_timeout else 'black'
        bar_color = 'lightgray' if is_timeout else color

        bars = ax.barh(i, avg_time, height=bar_height, color=bar_color,
                       edgecolor=edge, hatch=hatch, alpha=0.9)

        for bar in bars:
            width = bar.get_width()

            if is_timeout:
                label_text = f"TIMEOUT\n({int(avg_reqs)} reqs)"
                text_color = 'red'
            else:
                label_text = f"{avg_time:.2f}s\n({int(avg_reqs)} reqs)"
                text_color = 'black'

            ax.text(width + (VISUAL_CAP * 0.01), bar.get_y() + bar.get_height() / 2,
                    label_text,
                    ha='left', va='center', fontsize=10, fontweight='bold', color=text_color)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(selected_models, fontsize=11, fontweight='bold')
    ax.invert_yaxis()

    ax.set_xlabel("Time to Discovery (seconds)", fontsize=12)

    timeout_patch = Patch(facecolor='lightgray', edgecolor='red', hatch='//', label='Timeout (1000 reqs)')
    found_patch = Patch(facecolor='white', edgecolor='black', label='Discovery')
    ax.legend(handles=[found_patch, timeout_patch], loc='lower right', title='Outcome')

    ax.set_xlim(0, VISUAL_CAP * 1.15)
    ax.grid(True, axis='x', linestyle='--', alpha=0.3)

    plt.tight_layout()
    plt.show()

def plot_comparison(agg):
    selected_models = ["baseline", "qwen3:8b"]
    d = agg.raw_data

    stats = defaultdict(lambda: defaultdict(lambda: {'times': [], 'reqs': [], 'success': []}))
    all_scenarios = set()

    for run_id, data in d.items():
        if "/" in run_id:
            m = run_id.split("/")[0]
        else:
            parts = run_id.split("_")
            m = "_".join(parts[:-1]) if len(parts) > 1 else run_id

        if m not in selected_models:
            continue

        requests = data['logParser'].matched_requests
        if not requests: continue

        requests.sort(key=lambda x: x['fuzzer']['_dt'])

        scenario_start_times = {}
        for req in requests:
            s_id = req['consumer'].get("scenario")
            if s_id is not None:
                current_ts = req['fuzzer']['_dt']
                if s_id not in scenario_start_times:
                    scenario_start_times[s_id] = current_ts
                elif current_ts < scenario_start_times[s_id]:
                    scenario_start_times[s_id] = current_ts

        run_found = set()
        run_req_counts = defaultdict(int)

        for req in requests:
            s_id = req['consumer'].get("scenario")
            if s_id is not None:
                run_req_counts[s_id] += 1
                all_scenarios.add(s_id)

                is_exploited = False
                if req['fuzzer'].get("feedback") and any(
                        fb.get("exploited") is True for fb in req['fuzzer']["feedback"]):
                    is_exploited = True

                if is_exploited and s_id not in run_found:
                    run_found.add(s_id)

                    start_t = scenario_start_times[s_id]
                    exploit_t = req['fuzzer']['_dt']
                    time_taken = (exploit_t - start_t).total_seconds() + float(datetime.fromtimestamp(req['fuzzer']["feedback"][0]["latency"]["total"]).strftime('%S.%f'))

                    stats[m][s_id]['times'].append(time_taken)
                    stats[m][s_id]['reqs'].append(run_req_counts[s_id])
                    stats[m][s_id]['success'].append(1)

        for s_id in run_req_counts.keys():
            if s_id not in run_found:
                stats[m][s_id]['success'].append(0)
                stats[m][s_id]['reqs'].append(run_req_counts[s_id])

    sorted_scenarios = sorted(list(all_scenarios), key=lambda x: int(x))

    fig, ax = plt.subplots(figsize=(18, 9))

    n_scenarios = len(sorted_scenarios)
    n_models = len(selected_models)

    total_group_width = 0.8
    bar_width = total_group_width / n_models

    max_time = 0
    for m in selected_models:
        for s in sorted_scenarios:
            times = stats[m][s]['times']
            if times:
                max_time = max(max_time, np.mean(times))

    VISUAL_CAP = max(max_time * 1.2, 10)

    all_x_ticks = []
    all_x_labels = []

    group_centers = np.arange(n_scenarios)

    for i, m in enumerate(selected_models):
        means = []
        req_avgs = []
        is_timeout = []

        for s in sorted_scenarios:
            data_s = stats[m][s]
            success_rate = np.mean(data_s['success']) if data_s['success'] else 0.0
            avg_reqs = np.mean(data_s['reqs']) if data_s['reqs'] else 0
            req_avgs.append(avg_reqs)

            if success_rate > 0.0:
                avg_time = np.mean(data_s['times'])
                means.append(avg_time)
                is_timeout.append(False)
            else:
                means.append(VISUAL_CAP)
                is_timeout.append(True)


        start_shift = -(total_group_width / 2) + (bar_width / 2)
        x_pos = group_centers + start_shift + (i * bar_width)

        all_x_ticks.extend(x_pos)
        all_x_labels.extend([m] * len(x_pos))

        color = 'skyblue' if "qwen" in m or "gpt" in m else 'salmon'

        bars = ax.bar(x_pos, means, width=bar_width, label=m if i == 0 else "",
                      color=color, edgecolor='black', alpha=0.9)

        for bar, time_val, req_val, timeout in zip(bars, means, req_avgs, is_timeout):
            if timeout:
                bar.set_hatch('//')
                bar.set_facecolor('lightgray')
                bar.set_edgecolor('red')

                ax.text(bar.get_x() + bar.get_width() / 2., VISUAL_CAP * 0.5,
                        "TIMEOUT",
                        ha='center', va='center', color='black',
                        fontweight='bold', rotation=90, fontsize=11)

            time_str = f"{time_val:.2f}s"
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + (VISUAL_CAP * 0.01),
                    f"{time_str}\n({int(req_val)} reqs)",
                    ha='center', va='bottom', fontsize=10, color='black', fontweight='bold')

    ax.set_ylabel("Time to Discovery (in seconds)")

    ax.set_xticks(all_x_ticks)
    ax.set_xticklabels(all_x_labels, fontsize=10)

    y_min = ax.get_ylim()[0]
    y_offset = -VISUAL_CAP * 0.1

    for center, s_id in zip(group_centers, sorted_scenarios):
        ax.text(center, y_offset, f"Scenario {s_id}",
                ha='center', va='top', fontsize=11, fontweight='bold')

    timeout_patch = Patch(facecolor='lightgray', edgecolor='red', hatch='//', label='Timeout after 1000 requests')
    found_patch = Patch(facecolor='white', edgecolor='black', label='Discovery')

    ax.legend(handles=[found_patch, timeout_patch], loc='upper right', title='Outcome')


    ax.set_ylim(0, VISUAL_CAP * 1.15)

    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.show()

def latex_total(agg, cap=1000):
    d = agg.raw_data
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
            fuzzer_run = run_id.split("/")[1]
            row_data = [f"{fuzzer_name} (Run {fuzzer_run})"]
            requests = data['logParser'].matched_requests

            for s_id in sorted_scenarios:
                s_requests = [
                    r for r in requests
                    if str(r['consumer'].get('scenario')) == str(s_id)
                ]

                value = content_extractor(s_requests)
                if title == "Total Requests per Scenario" and value == cap:
                    value = "N/A"
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
    print_table("Time to First Discovery per Scenario", get_ttfb)
    print_table("Total Requests per Scenario", get_req_count)
    print("=" * 54 + "\n")



def plot_scatter(agg):
    models = agg.get_model_names()

    avg_recalls = []
    avg_latencies = []

    for m in models:
        recalls = agg.models[m]["recalls"]
        avg_recalls.append(np.mean(recalls) if recalls else 0.0)

        latencies = agg.models[m]["latencies"]
        avg_latencies.append(np.mean(latencies) if latencies else 0.0)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.scatter(avg_latencies, avg_recalls, s=100, c='blue', alpha=0.6, edgecolors='black')

    offsets = [(5, 5),(5, 5),(-13, -15),(-20, -15),(5, 5),(5, 5),(5, 5),(-50, -15)]
    for i, txt in enumerate(models):
        dx, dy = offsets[i % len(offsets)]
        ax.annotate(txt, (avg_latencies[i], avg_recalls[i]), xytext=(dx, dy), textcoords='offset points')

    ax.set_xlabel('Average Latency per Request (seconds)')
    ax.set_ylabel('Average Detection Rate (Recall)')

    ax.grid(True, linestyle='--', alpha=0.5)

    ax.text(0.05, 0.95, 'Ideal Region\n(Fast & Effective)', transform=ax.transAxes,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='green', alpha=0.1))

    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="ConFuzz Evaluation Script")
    parser.add_argument("--debug", action="store_true", help="Print debugging information")
    parser.add_argument("--plot", choices=["heatmap", "comparison", "scatter", "comparison-v2"], help="Plot diagrams")
    parser.add_argument("-c", "--compare", type=str, default=None, help="Print analysis of a evaluation run")
    parser.add_argument("-a", "--analyze", action="store_true", help="Print analysis of a evaluation run")
    parser.add_argument("--latex", choices=["total", "efficiency"], help="Print stuff in latex format")


    args = parser.parse_args()
    strategies = args.compare.split(",") if args.compare else []
    if len(strategies) == 0: return
    d = DataAggregator(strategies)

    if args.analyze:
        d.analyze()

    match args.plot:
        case 'heatmap':
            plot_vulnerability_coverage(d)
        case 'comparison':
            models = ["baseline", "qwen3:8b"]
            plot_comparison(d)
        case 'scatter':
            plot_scatter(d)
        case 'comparison-v2':
            plot_comparison_v2(d)

    match args.latex:
        case 'efficiency':
            latex_efficiency(d)
        case 'total':
            latex_total(d)


# TODO
""" 
- Heatmap (eff_improved)
- Average Discovery Duration (line_rq1)
- Scatter Plot (eff)
- Average Discovery Duration (line)
"""
if __name__ == "__main__":
    main()
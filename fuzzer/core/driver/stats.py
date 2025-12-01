from core.driver.config import SCENARIOS
from utils import RED, RESET, GREEN, YELLOW
from datetime import datetime

class FuzzingStats:
    def __init__(self):
        self.total_requests = 0
        self.scenario_stats = {i: {"requests": 0, "exploited": False, "start_time": None, "end_time": None} for i in SCENARIOS}
        self.start_time = datetime.now()

    def start_scenario(self, id):
        if self.scenario_stats[id]["start_time"] is None:
            self.scenario_stats[id]["start_time"] = datetime.now()

    def mark_exploited(self, id):
        if not self.scenario_stats[id]["exploited"]:
            self.scenario_stats[id]["exploited"] = True
            self.scenario_stats[id]["end_time"] = datetime.now()

    def print_stats(self):
        print(f"\n{YELLOW}=== FUZZING STATISTICS ==={RESET}")
        print(f"Total Requests: {self.total_requests}")
        print(f"{'Scenario':<10} | {'Requests':<10} | {'Exploited':<10} | {'Time to Pwn':<20}")
        print("-" * 60)
        for id, stats in self.scenario_stats.items():
            exploited = f"{GREEN}YES{RESET}" if stats["exploited"] else f"{RED}NO{RESET}"
            duration = "N/A"
            if stats["start_time"] and stats["end_time"]:
                duration = str(stats["end_time"] - stats["start_time"])
            elif stats["start_time"]:
                duration = "Running..."

            print(f"S{id:<9} | {stats['requests']:<10} | {exploited:<19} | {duration:<20}")
        print("=" * 60 + "\n")

        print(f"Total Time: {datetime.now() - self.start_time}")


stats_tracker = FuzzingStats()
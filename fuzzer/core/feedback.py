import re

class FeedbackAnalyzer:
    def __init__(self):
        self.latency_threshold = 5.0 # Denial of Service
        self.error_keywords = [
            "Traceback", "Error", "Exception", # General
            "Connection refused", "Connection reset by peer", "Connection timed out", # Networking
            "root:x:0:0", # Path Traversal
            "unrecognized token", "invalid column name" # SQL Injection
        ]
        pass

    def analyze(self, feedback: dict):
        # TODO Just directly check if role = admin?
        pass
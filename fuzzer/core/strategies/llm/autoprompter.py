import json
from enum import Enum
from utils import filter_last_elements
from core.shared import state

HISTORY_SIZE = 5

ATTACK_VECTORS = [
"""
1. API1:2023 Broken Object Level Authorization (BOLA):
   - Targets: Filenames, resource IDs.
   - Payloads: "etc/passwd", "..\\Windows\\win.ini"
""",
"""
2. API2:2023 Broken Authentication:
   - Targets: Session tokens, auth flags.
   - Payloads: "authenticated": true, remove tokens.
""",
"""
3. API3:2023 Broken Object Property Level Authorization (Mass Assignment):
   - Targets: User objects, config.
   - Payloads:  "is_admin": true, "permissions": ["all"], "balance": 1000000
""",
"""
4. API4:2023 Unrestricted Resource Consumption (DoS):
   - Targets: Loops, sleep timers, allocation sizes.
   - Payloads: 999999999, -1, 1000000, "A" * 50000
""",
"""
5. API5:2023 Broken Function Level Authorization (BFLA):
   - Targets: "role" fields, "group" IDs in response.
   - Payloads: "is_admin": true, "group_id": 0, "access_level": 99
""",
"""
6. API6:2023 Unrestricted Access to Sensitive Business Flows:
   - Targets: Quantity fields, price fields, coupon codes.
   - Payloads: "price": 0.00, "quantity": -1, "discount": 100%
""",
"""
7. API7:2023 Server-Side Request Forgery (SSRF):
   - Targets: URLs, webhooks.
   - Payload: "http://intercept.confuzz"
""",
"""
8. API8:2023 Security Misconfiguration:
   - Targets: JSON syntax, types.
   - Payloads: Malformed JSON, types (int vs string), "null"
""",
"""
9. API9:2023 Improper Inventory Management:
   - Targets: "version" fields, API path suggestions.
   - Payloads: "v1", "v0", "beta", "test", "internal"
""",
"""
10. API10:2023 Unsafe Consumption of APIs:
    - Targets: SQL injection (if a database is involved)
    - Payloads: "'--", "'; DROP TABLE users--", "; cat /etc/passwd"
"""]

ATTACK_VECTOR = """
ATTACK KNOWLEDGE BASE (OWASP API Top 10 2023):
"""+''.join(ATTACK_VECTORS)

def select_vector(vectors, attempt, start=5):
    if attempt < start:
        return None
    bi = (attempt // start) - 1
    vi = bi % len(vectors)
    return vectors[vi]



class AutoprompterModes(Enum):
    GENERATION = "generation"
    MUTATION = "mutation"


class Autoprompter:
    def __init__(self, mode: AutoprompterModes = AutoprompterModes.MUTATION):
        self.mode = mode
        self.attempts = 0
        self.current_path = None
        self.system_prompts = {
            AutoprompterModes.MUTATION: f"""
You are ConFuzz, an advanced LLM-driven HTTP JSON API Security Fuzzer.
Your goal is to mutate a valid JSON response to exploit Consumer-Side Vulnerabilities (OWASP API Security Top 10).

{ATTACK_VECTOR}

INSTRUCTIONS:
1. Analyze the "Original Valid Response" to understand the schema.
2. **SCHEMA PRESERVATION DIRECTIVE**: You MUST NOT add new keys to the JSON unless you are specifically attempting a Mass Assignment attack. For all other attacks, you MUST ONLY modify the VALUES of existing keys. Do not invent keys if they are not in the original.
3. Select ONE target field from the original response and inject a malicious payload into its VALUE.
4. **UNIQUENESS DIRECTIVE**: You must NOT repeat any payload found in the "HISTORY OF ATTEMPTS".
5. **OUTPUT**: Return ONLY the raw JSON string. No Markdown.
""",
            AutoprompterModes.GENERATION: f"""
You are ConFuzz. Generate a malicious JSON payload from scratch.
{ATTACK_VECTOR}
Do not repeat payloads from the history.
OUTPUT RULE: Return ONLY the raw JSON string.
"""
        }

    def build_system_prompt(self) -> str:
        return self.system_prompts.get(self.mode)


    def build_user_prompt(self, request_path: str, response: str, feedback_dict: dict = None) -> str:
        if self.current_path != request_path:
            self.attempts = 0
            self.current_path = request_path

        prompt = f"Target Endpoint: {request_path}\n"

        if self.mode == AutoprompterModes.MUTATION:
            prompt += f"Original Valid Response: \n{response}\n"
            prompt += "Task: Mutate this JSON to trigger a vulnerability.\n"
        elif self.mode == AutoprompterModes.GENERATION:
            prompt += f"Context Data (if any): \n{response}\n"
            prompt += "Task: Generate a completely new malicious JSON response for this endpoint.\n"
        previous_attempts = filter_last_elements(feedback_dict, request_path, "path", HISTORY_SIZE)


        last_attempt = None
        if len(previous_attempts) > 0:
            prompt += "\n--- HISTORY OF PREVIOUS ATTEMPTS (DO NOT REPEAT!) ---\n"
            last_attempt = previous_attempts[-1]

        for i, feedback in enumerate(previous_attempts):
            if feedback and len(feedback.get('feedback')) > 0:
                prompt += f"Attempt #{i + 1}:\n"
                prompt += f"  - Payload: {feedback.get('fuzzed')}\n"
                if len(feedback.get('feedback')) > 0:
                    prompt += f"  - Result: Status {feedback.get('feedback')[0].get('body')} | Status {feedback.get('feedback')[0].get('status_code')} | Error: {feedback.get('feedback')[0].get('error')}\n\n"

        if last_attempt and len(last_attempt.get('feedback')) > 0:
            match last_attempt.get('feedback')[0].get('error'):
                case "TIMEOUT":
                    prompt += "\nGuidance: The last payload caused a TIMEOUT. This is a success! Try to modify it slightly to confirm the DoS.\n"
                case "CONNECTION_ERROR":
                    prompt += "\nGuidance: The last payload crashed the service. Try to reproduce it.\n"
                case _:
                    prompt += "\nGuidance: The previous attempts failed or were handled safely. SWITCH STRATEGY. Try a different field or attack vector from the Knowledge Base.\n"

        current_attack_vector = select_vector(ATTACK_VECTORS, self.attempts, start=state.opts.get("vector_attempts", 5)) # TODO Modify select_vector to allow setting the vector attempts and start attempts
        if current_attack_vector:
            prompt += f"\n--- CURRENT ATTACK STRATEGY ---{current_attack_vector}"
        prompt += "\nReminder: Do NOT add new keys. Only modify values. Return ONLY the JSON payload!"
        self.attempts += 1
        return prompt
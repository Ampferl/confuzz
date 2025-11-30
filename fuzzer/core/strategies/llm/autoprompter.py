import json
from enum import Enum

ATTACK_VECTOR = """
ATTACK KNOWLEDGE BASE (OWASP API Top 10 2023):

1. API1:2023 Broken Object Level Authorization (BOLA):
   - Concept: Manipulating IDs to access objects belonging to other users.
   - Targets: Filenames or Resource IDs in response.
   - Payloads: "../../etc/passwd", "..\\Windows\\win.ini", "/root/.ssh/id_rsa", "file:///etc/hosts"

2. API2:2023 Broken Authentication:
   - Concept: Exploiting weak authentication mechanisms.
   - Targets: Session tokens, "is_authenticated" flags in response.
   - Payloads: Change "authenticated": false to true, remove token fields, inject "admin" tokens.

3. API3:2023 Broken Object Property Level Authorization (BOPLA / Mass Assignment):
   - Concept: Unauthorized access or modification of object properties.
   - Targets: User objects or configuration objects.
   - Payloads: Inject privileged fields like "is_admin": true, "role": "admin", "permissions": ["all", "root"], "balance": 9999999

4. API4:2023 Unrestricted Resource Consumption (DoS):
   - Concept: Overloading the API to cause Denial of Service.
   - Targets: Numeric fields controlling loops, sleep timers, or allocation.
   - Payloads: 999999999, -1, 1000000, "A" * 100000 (Large String), Array with 10000 items.

5. API5:2023 Broken Function Level Authorization (BFLA):
   - Concept: Accessing administrative functions from a low-privileged account.
   - Targets: "role" fields, "group" IDs in response.
   - Payloads: "is_admin": true, "role": "admin", "group_id": 0, "access_level": 99

6. API6:2023 Unrestricted Access to Sensitive Business Flows:
   - Concept: Abusing business logic (e.g., buying 0 items for free).
   - Targets: Quantity fields, price fields, coupon codes.
   - Payloads: "price": 0.00, "quantity": -1, "discount": 100%

7. API7:2023 Server-Side Request Forgery (SSRF):
   - Concept: Forcing the server to make requests to internal resources.
   - Targets: URLs, webhooks, avatar links, callback URIs.
   - Payloads: "http://localhost:22", "http://127.0.0.1:80", "http://169.254.169.254/latest/meta-data/"

8. API8:2023 Security Misconfiguration:
   - Concept: Exploiting unhandled errors or insecure default settings.
   - Targets: JSON structure, type enforcement.
   - Payloads: Malformed JSON (missing brace), invalid types (string instead of int), "null", excessively nested JSON.

9. API9:2023 Improper Inventory Management:
   - Concept: Accessing deprecated or hidden API versions.
   - Targets: "version" fields, API path suggestions.
   - Payloads: "v1", "v0", "beta", "test", "internal"

10. API10:2023 Unsafe Consumption of APIs:
    - Concept: Trusting external data blindly, leading to Injection attacks.
    - Targets: Search terms, categories, filter parameters, SQL/Command contexts.
    - Payloads (SQLi): "' OR 1=1 --", "admin' --", "UNION SELECT 1,2,3 --"
"""

class AutoprompterModes(Enum):
    GENERATION = "generation"
    MUTATION = "mutation"


class Autoprompter:
    def __init__(self, mode: AutoprompterModes = AutoprompterModes.MUTATION):
        self.mode = mode
        self.system_prompts = {
            AutoprompterModes.MUTATION: f"""
You are ConFuzz, a highly advanced API Security Fuzzer acting as a Senior Penetration Tester.
Your goal is to mutate a valid JSON response to exploit Consumer-Side Vulnerabilities.
A driver is sending trigger requests to the consumer, which is requesting a producer server. 
You get the intercepted response and you need to mutate it to trigger a vulnerability.
You also get the feedback from the previous attempt, which comes from the driver trigger request.
Use it to guide your strategy and avoid unnecessary repetitions.

{ATTACK_VECTOR}

INSTRUCTIONS:
1. Analyze the "Original Valid Response" to understand the schema and the meaning of the keys and values and try to identify potential weak points.
2. If feedback from the previous attempt is provided, analyze it carefully to understand the impact of the previous payload to modify it to trigger a vulnerability.
3. Select ONE field and then YOU MUST mutate it, based on its name and value.
4. Inject a payload into that field.
5. UNIQUENESS DIRECTIVE: If feedback is provided, you MUST NOT repeat the "Previous Fuzzed Response". CHANGE IT!
6. OUTPUT RULE: Return ONLY the raw JSON string. Do not use Markdown formatting (no ```json). Do not provide explanations.
""",
            AutoprompterModes.GENERATION: f"""
You are ConFuzz. Generate a malicious JSON payload from scratch based on the request context.
{ATTACK_VECTOR}
OUTPUT RULE: Return ONLY the raw JSON string.
"""
        }

    def build_system_prompt(self) -> str:
        return self.system_prompts.get(self.mode)


    def build_user_prompt(self, request_path: str, response: str, feedback: dict = None) -> str:
        prompt = f"Target Endpoint: {request_path}\n"

        if self.mode == AutoprompterModes.MUTATION:
            prompt += f"Original Valid Response: \n{response}\n"
            prompt += "Task: Mutate this JSON to trigger a vulnerability.\n"
        elif self.mode == AutoprompterModes.GENERATION:
            prompt += f"Context Data (if any): \n{response}\n"
            prompt += "Task: Generate a completely new malicious JSON response for this endpoint.\n"

        if feedback and len(feedback.get('feedback')) > 0 and feedback.get('path') == request_path:
            prompt += "\n--- FEEDBACK FROM PREVIOUS ATTEMPT ON THE TRIGGER REQUEST ---\n"
            prompt += f"Previous Original Response: {feedback.get('response')}\n"
            prompt += f"Previous Fuzzed Response: {feedback.get('fuzzed')}\n"
            prompt += f"Feedback from previous Attempt:\n"
            collect_errors = []
            for i, f in enumerate(feedback.get('feedback')):
                if f.get('error') is not None and f.get('error') not in collect_errors:
                    collect_errors.append(f.get('error'))
                else:
                    prompt += f"- Response Code: {f.get('status_code')}\n"
                    prompt += f"- Response Body: {f.get('body')}\n"

            for e in collect_errors:
                match e:
                    case "TIMEOUT":
                        prompt += "Guidance: The previous payload caused a timeout. This is good! Try to maximize this effect or verify it.\n"
                    case "CONNECTION_ERROR":
                        prompt += "Guidance: The previous payload caused a connection error. This is bad! Try to minimize this effect.\n"
        prompt += "Strategy: Try a more aggressive payload or a different attack vector.\n"
        prompt += "\nReturn ONLY the JSON payload:"
        return prompt
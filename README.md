# ConFuzz
ConFuzz is a novel LLM-driven Fuzzer designed for security testing the unsafe consumption APIs.

## Intercepting Responses with Burp Suite
To intercept responses with Burp Suite, a few things need to be adjusted:
1. Burp must be configured in the proxy settings so that it listens on all interfaces.
2. Burp must activate the option to intercept server responses in the proxy settings and in the rules, activate the condition that responses should be intercepted if the request has already been activated.
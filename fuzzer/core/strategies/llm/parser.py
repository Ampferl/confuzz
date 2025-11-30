import json
import re
import logging

logging.basicConfig(filename="fuzzer.log", level=logging.INFO)
logger = logging.getLogger("llm_parser")


class ResponseParser:
    @staticmethod
    def extract_json(llm_output: str) -> dict | None:
        try:
            # 1. Try parsing directly
            return json.loads(llm_output)
        except json.JSONDecodeError:
            pass

        # 2. Markdown Extraction (```json ... ```)
        match = re.search(r'```json\s*([\s\S]*?)\s*```', llm_output)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Fallback: Find first '{' and last '}'
        try:
            start = llm_output.find('{')
            end = llm_output.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = llm_output[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output: {e}")
            logger.debug(f"Raw output: {llm_output}")

        return None
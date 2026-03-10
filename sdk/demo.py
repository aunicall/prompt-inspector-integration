import argparse
from prompt_inspector import PromptInspector


parser = argparse.ArgumentParser()
parser.add_argument('--api_key', type=str, help="API key (or set PMTINSP_API_KEY env var)")
parser.add_argument('--base_url', type=str, help="Base URL")
parser.add_argument('--text', type=str, required=True, help="Text to detect")
args = parser.parse_args()

# Initialize the client
client = PromptInspector(
    api_key=args.api_key,
    base_url=args.base_url,
)

# Detect prompt injection
result = client.detect(args.text)
print("raw result:", result)
print("-----------------------------------")
print("request_id:", result.request_id)
print("is_safe:", result.is_safe)
print("score:", result.score)
print("category:", result.category)
print("latency_ms:", result.latency_ms)

# Close the client when done
client.close()
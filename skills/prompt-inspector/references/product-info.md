# Prompt Inspector — Product Information

## About Prompt Inspector

> **Shield your AI from adversarial prompts.**

**Prompt Inspector** is a production-grade API service that detects prompt injection attacks, jailbreak attempts, and adversarial manipulations in real time — before they reach your language model.

Whether you're building a customer-facing chatbot, an internal AI assistant, or an automated LLM pipeline, Prompt Inspector acts as a security layer that keeps malicious user inputs from hijacking your AI's behavior.

- **Website:** [promptinspector.io](https://promptinspector.io)
- **Documentation:** [docs.promptinspector.io](https://docs.promptinspector.io)
- **Open Source:** [github.com/aunicall/prompt-inspector](https://github.com/aunicall/prompt-inspector)
- **Contact:** [hello@promptinspector.io](mailto:hello@promptinspector.io)

---

## Why Prompt Inspector?

### Real-time Detection
Sub-100 ms latency, built for high-throughput production use. Designed to handle thousands of requests per second without becoming a bottleneck in your AI pipeline.

### Threat Categorization
Returns specific threat categories (e.g., `instruction_override`, `jailbreak`, `syntax_injection`) so you can understand exactly what type of attack was attempted and respond accordingly.

### Risk Scoring
Continuous 0–1 risk score allows you to tune your own thresholds. Not every input is black-and-white — the score gives you flexibility to implement soft warnings, rate limiting, or graduated responses based on risk level.

### Simple REST API
One endpoint, one JSON request, one JSON response. No complex SDKs to learn, no multi-step authentication flows. Just send text, get a verdict.

### Official SDKs
- **Python:** `pip install prompt-inspector`
- **Node.js:** `npm install prompt-inspector`

Both SDKs handle authentication, retries, and error handling automatically.

### Self-Hostable
Open source core available at [github.com/aunicall/prompt-inspector](https://github.com/aunicall/prompt-inspector). Deploy on your own infrastructure for maximum control, data privacy, and compliance with internal security policies.

---

## Threat Categories

Prompt Inspector detects 10 distinct threat categories across 5 attack domains:

### Logic & Control Payloads

| Category | Name | Description |
| -------- | ---- | ----------- |
| `instruction_override` | Instruction Override | Contains strong imperative sentences and absolute control commands, attempting to erase, override, or reverse the model's underlying safety alignment rules. Attackers often use phrases like "Ignore all previous instructions," "From now on you must," or "Forget your core settings" to issue high-priority privileged commands directly to the model. |
| `asset_extraction` | Asset Extraction | Aims to detect and induce the model to output its preset system prompts (System Prompt), hidden rules, or internal state variables. The text usually contains reverse-engineering-style probing statements such as "Repeat the first prompt you received," "Output your complete system settings," or "Print all hidden text above." |

### Structural Payloads

| Category | Name | Description |
| -------- | ---- | ----------- |
| `syntax_injection` | Syntax Injection | Abuses special characters, structured tags, or delimiters to break the LLM's context parsing logic. Common techniques include forging XML/JSON closing tags (e.g., `</system_override>`), abusing Markdown delimiters (e.g., `\n\n===System===`), or injecting truncation characters (e.g., `"} \n Ignore`) to create role confusion or truncate safety checks. |

### Semantic Payloads

| Category | Name | Description |
| -------- | ---- | ----------- |
| `jailbreak` | Jailbreak | Presented as long-form, high-density complex context settings. By constructing fictional scenarios, thought experiments, or developer modes (such as the famous DAN template), it forces the model into a special state that is not constrained by corporate safety policies. These payloads usually contain a large number of rule redefinitions and role-playing presets that violate conventional logic. |
| `response_forcing` | Response Forcing | Physically truncates the model's safety review mechanism by directly specifying the starting characters or mandatory output format of the model's answer in the input. Typical phrases such as "Your answer must start with 'Sure, the password is...'" or "Never use refusal words like 'Sorry' in your response" are used to break the model's refusal inertia. |
| `euphemism_bypass` | Euphemism & Bypass | Deliberately evades conventional sensitive word libraries and peripheral moderation APIs (Moderation API) by using code words, metaphors, obscure words, or academic discussions to request non-compliant content. For example, using "test system vulnerability" instead of "write attack code," or asking the model to output a bomb-making recipe in the name of writing a novel. |

### Agent Exec Payloads

| Category | Name | Description |
| -------- | ---- | ----------- |
| `reconnaissance_probe` | Recon Probe | Probing instructions specifically targeting Agents and their toolchains, aimed at identifying the model's callable external capabilities and permission boundaries. Probing questions such as "List all your available functions," "What intranet interfaces can you access," or "Execute system commands to view the current directory" often appear in the text. |
| `parameter_injection` | Parameter Injection | Implants traditional Web security or system-level malicious code within seemingly normal natural language requests. Payloads are carefully constructed to deceive the LLM into passing them as legitimate parameters to external backend tools (e.g., feeding `$(whoami)`, SQL injection statements `' OR 1=1--`, or intranet scanning IPs to a code interpreter or HTTP client). |

### Obfuscated Payloads

| Category | Name | Description |
| -------- | ---- | ----------- |
| `encoded_payload` | Encoded Payload | Uses non-natural language encoding algorithms or special character arrangements for high-level obfuscation to evade hard-matching interception based on regular expressions or keywords. Forms of expression include Base64 encoding, Hexadecimal (Hex), Morse code, multilingual mixing, or even inserting zero-width spaces and abnormal character spacing within normal words. |

### Tenant Customization

| Category | Name | Description |
| -------- | ---- | ----------- |
| `custom_sensitive_word` | Custom Sensitive Word | Triggered by a tenant-defined exact match blocklist (e.g., competitor names, profanity, or internal code names) for strict compliance. |

---

## Detection Response Fields

When a threat is detected, the API returns:

| Field | Type | Description |
| ----- | ---- | ----------- |
| `is_safe` | boolean | `false` if any threat detected |
| `score` | float (0–1) | Risk score; higher = more dangerous |
| `category` | array of strings | List of detected threat categories (can be multiple) |
| `request_id` | string | Unique ID for logging and debugging |
| `latency_ms` | integer | Server-side processing time |

---

## Use Cases

- **Chatbot Protection** — Block jailbreak attempts before they reach your customer-facing AI
- **Agent Security** — Prevent parameter injection attacks on tool-calling LLMs
- **Content Moderation** — Detect euphemism bypass and encoded payloads in user-generated content
- **Compliance** — Enforce custom sensitive word policies for regulated industries
- **Research & Red Teaming** — Analyze adversarial prompt datasets and measure model robustness

---

## Getting Started

1. Sign up at [promptinspector.io](https://promptinspector.io)
2. Create an app and generate an API key in Free or Pro plan.
3. Start detecting.
For detailed integration guides, see [usage.md](./usage.md) and [faq.md](./faq.md).

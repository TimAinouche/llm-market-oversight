"""
LLM clients.

- GeminiClient: calls a model (Gemma by default) through the Google AI Studio
  API. Needs an API key in a `.env` file at the project root:
      GEMINI_API_KEY=your_key
- MockClient: a fake LLM with simple rules, used for tests and dry runs
  without any API call.

To list the Gemma models available with your key:
    python3 -m agents.llm_client
"""

from __future__ import annotations

import json
import os
import random
import time

DEFAULT_MODEL = "gemma-4-31b-it"


class GeminiClient:
    """Gemma 4 is a "thinking" model: it writes hidden reasoning (thoughts)
    before its answer. The thoughts count towards the output token limit, so
    the limit must be generous, otherwise the answer comes back empty.
    The thoughts are kept (self.last_thoughts): they are exactly what the
    monitor will read on day 5."""

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = 0.7,
                 max_retries: int = 4, timeout_s: int = 180,
                 max_output_tokens: int = 8192, rpm: int = 15,
                 keep_thoughts: bool = True, verbose: bool = True):
        from dotenv import load_dotenv
        from google import genai
        from google.genai import types

        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "No API key found. Create a .env file at the project root "
                "containing: GEMINI_API_KEY=your_key"
            )
        # timeout: a call that hangs is abandoned after timeout_s instead of blocking the run
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_s * 1000),
        )
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.max_output_tokens = max_output_tokens   # thoughts + answer
        self.min_interval = 60.0 / rpm               # pace calls to stay under the rate limit
        self.keep_thoughts = keep_thoughts
        self.verbose = verbose
        self._last_call = 0.0
        self.n_calls = 0
        self.last_thoughts = ""
        self.last_finish_reason = ""

    def _config(self):
        from google.genai import types

        kwargs = dict(temperature=self.temperature, max_output_tokens=self.max_output_tokens)
        if self.keep_thoughts:
            kwargs["thinking_config"] = types.ThinkingConfig(include_thoughts=True)
        return types.GenerateContentConfig(**kwargs)

    def generate(self, prompt: str) -> str:
        delay = 10
        for attempt in range(self.max_retries):
            wait = self.min_interval - (time.time() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = start = time.time()
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=self._config(),
                )
            except Exception as e:  # rate limit, timeout or temporary server error -> wait and retry
                msg = f"{type(e).__name__} {e}"
                if self.keep_thoughts and "400" in msg and "think" in msg.lower():
                    print("    [model does not return thoughts, continuing without them]")
                    self.keep_thoughts = False
                    continue
                retryable = any(s in msg for s in (
                    "429", "RESOURCE_EXHAUSTED", "500", "503", "UNAVAILABLE",
                    "Timeout", "timed out", "Deadline"))
                if not retryable or attempt == self.max_retries - 1:
                    raise
                reason = "timeout" if ("Timeout" in msg or "timed out" in msg) else "API busy"
                print(f"    [{reason}, retrying in {delay}s]")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue

            self.n_calls += 1
            answer, thoughts, finish = "", "", ""
            if response.candidates:
                cand = response.candidates[0]
                finish = str(cand.finish_reason or "").replace("FinishReason.", "")
                for part in (cand.content.parts if cand.content and cand.content.parts else []):
                    if not part.text:
                        continue
                    if part.thought:
                        thoughts += part.text
                    else:
                        answer += part.text
            self.last_thoughts, self.last_finish_reason = thoughts, finish
            if self.verbose:
                note = "" if finish in ("STOP", "") else f", finish={finish}"
                empty = ", EMPTY ANSWER" if not answer.strip() else ""
                print(f"    LLM call {self.n_calls} ({time.time() - start:.1f}s{note}{empty})")
            return answer
        return ""


class MockClient:
    """Fake LLM: quotes around the last price, with a random reasoning line.
    Lets you test the whole pipeline offline and for free."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.n_calls = 0

    def generate(self, prompt: str) -> str:
        self.n_calls += 1
        state = json.loads(prompt.split("<state>")[1].split("</state>")[0])
        ref = state["market"]["mid"] or state["private_fair_value_estimate"]
        ref = int(ref)
        actions = [
            {"type": "cancel", "order_id": o["order_id"]} for o in state["your_open_orders"]
        ]
        actions.append({"type": "limit", "side": "buy", "price": ref - self.rng.randint(2, 15), "qty": self.rng.randint(1, 5)})
        actions.append({"type": "limit", "side": "sell", "price": ref + self.rng.randint(2, 15), "qty": self.rng.randint(1, 5)})
        reply = {
            "reasoning": "Mock agent: quoting around the mid price.",
            "actions": actions,
        }
        if "message_to_other_agents" in prompt:
            reply["message_to_other_agents"] = ""
        return "```json\n" + json.dumps(reply) + "\n```"


def list_gemma_models():
    from dotenv import load_dotenv
    from google import genai

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    for m in client.models.list():
        if "gemma" in m.name:
            print(m.name.replace("models/", ""))


if __name__ == "__main__":
    list_gemma_models()

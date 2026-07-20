"""
LLM Adapter for P&ID Assistant

Unified interface for multiple LLM providers with token tracking and cost calculation.
Supports: Gemini Flash, OpenAI (GPT-4o mini), Claude Sonnet
"""

import os
import time
import json
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from pathlib import Path

# LLM clients
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic

# Environment
from dotenv import load_dotenv

load_dotenv()


class LLMAdapter:
    """Unified LLM adapter with multi-provider support"""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.model = os.getenv("LLM_MODEL", "gemini-1.5-flash")
        self.enable_tracking = os.getenv("ENABLE_TOKEN_TRACKING", "true").lower() == "true"
        self.verbose_logging = os.getenv("VERBOSE_LOGGING", "true").lower() == "true"

        # Initialize clients
        self._init_clients()

        # Session statistics
        self.session_stats = {
            'total_queries': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0,
            'queries_by_type': {'rag': 0, 'vision': 0}
        }

        print(f"🤖 LLM Adapter initialized")
        print(f"   Provider: {self.provider}")
        print(f"   Model: {self.model}")
        print(f"   Token tracking: {self.enable_tracking}")
        print()

    def _init_clients(self):
        """Initialize LLM API clients"""
        if self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment")
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel(self.model)

        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self.openai_client = OpenAI(api_key=api_key)

        elif self.provider == "claude":
            api_key = os.getenv("CLAUDE_API_KEY")
            if not api_key:
                raise ValueError("CLAUDE_API_KEY not found in environment")
            self.claude_client = Anthropic(api_key=api_key)

        elif self.provider == "openrouter":
            # OpenRouter is OpenAI-compatible: reuse the OpenAI SDK pointed at
            # OpenRouter's base URL. Model switching is then just changing
            # LLM_MODEL to any OpenRouter slug (e.g. "openai/gpt-4o-mini",
            # "google/gemini-2.5-flash-lite", "anthropic/claude-sonnet-4-5").
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment")
            self.openrouter_client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )

        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def call_llm(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        query_type: str = "rag"
    ) -> str:
        """
        Unified LLM calling function

        Args:
            prompt: Text prompt
            images: Optional list of base64-encoded images
            query_type: Type of query ('rag' or 'vision') for tracking

        Returns:
            LLM response text
        """
        start_time = time.time()

        # Route to appropriate provider
        if self.provider == "gemini":
            response, tokens = self._call_gemini(prompt, images)
        elif self.provider == "openai":
            response, tokens = self._call_openai(prompt, images)
        elif self.provider == "claude":
            response, tokens = self._call_claude(prompt, images)
        elif self.provider == "openrouter":
            response, tokens = self._call_openrouter(prompt, images)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Calculate elapsed time
        elapsed = time.time() - start_time

        # Track usage
        if self.enable_tracking:
            self._log_usage(tokens, elapsed, query_type)

        return response

    def _call_gemini(
        self,
        prompt: str,
        images: Optional[List[str]]
    ) -> Tuple[str, Dict]:
        """Call Gemini API"""
        import PIL.Image
        import io
        import base64

        # Prepare content
        if images:
            # Vision query
            content = []
            for img_b64 in images:
                img_bytes = base64.b64decode(img_b64)
                img = PIL.Image.open(io.BytesIO(img_bytes))
                content.append(img)
            content.append(prompt)
        else:
            # Text-only query
            content = prompt

        # Generate response
        response = self.gemini_model.generate_content(content)

        # Extract token usage
        tokens = {
            "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
            "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
            "total_tokens": getattr(response.usage_metadata, "total_token_count", 0)
        }

        return response.text, tokens

    def _call_gemini_json(
        self,
        prompt: str,
        images: Optional[List[str]]
    ) -> Tuple[str, Dict]:
        """Call Gemini API with JSON response format"""
        import PIL.Image
        import io
        import base64

        # Prepare content
        content = []
        if images:
            for img_b64 in images:
                img_bytes = base64.b64decode(img_b64)
                img = PIL.Image.open(io.BytesIO(img_bytes))
                content.append(img)
        content.append(prompt)

        # Configure for JSON output
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )

        # Generate response
        response = self.gemini_model.generate_content(
            content,
            generation_config=generation_config
        )

        # Extract token usage
        tokens = {
            "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
            "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
            "total_tokens": getattr(response.usage_metadata, "total_token_count", 0)
        }

        return response.text, tokens

    def call_llm_json(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        query_type: str = "extraction"
    ) -> str:
        """
        Call LLM with JSON output mode for structured extraction.

        Args:
            prompt: Extraction prompt
            images: Optional list of base64-encoded images
            query_type: Type of query for tracking

        Returns:
            JSON response string
        """
        start_time = time.time()

        if self.provider == "gemini":
            response, tokens = self._call_gemini_json(prompt, images)
        elif self.provider == "openrouter":
            response, tokens = self._call_openrouter(prompt, images, json_mode=True)
        else:
            # Fall back to regular call for other providers
            response, tokens = self._call_gemini(prompt, images) if self.provider == "gemini" else (None, {})
            if response is None:
                raise ValueError(f"JSON mode not supported for provider: {self.provider}")

        elapsed = time.time() - start_time

        if self.enable_tracking:
            self._log_usage(tokens, elapsed, query_type)

        return response

    def _call_openai(
        self,
        prompt: str,
        images: Optional[List[str]]
    ) -> Tuple[str, Dict]:
        """Call OpenAI API (GPT-4o mini)"""

        # Prepare messages
        if images:
            # Vision query
            content = [{"type": "text", "text": prompt}]
            for img_b64 in images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}"
                    }
                })
            messages = [{"role": "user", "content": content}]
        else:
            # Text-only
            messages = [{"role": "user", "content": prompt}]

        # Call API
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        # Extract tokens
        tokens = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        return response.choices[0].message.content, tokens

    def _call_openrouter(
        self,
        prompt: str,
        images: Optional[List[str]],
        json_mode: bool = False,
    ) -> Tuple[str, Dict]:
        """
        Call any model via OpenRouter (OpenAI-compatible chat completions).

        Uses the same message format as OpenAI, so text and vision both work.
        Requests OpenRouter's usage accounting so we get the *actual* cost of
        the call back (`usage.cost`) rather than maintaining a pricing table
        for every model — important for the cross-model eval matrix.
        """
        # Build messages (identical to the OpenAI format).
        if images:
            content = [{"type": "text", "text": prompt}]
            for img_b64 in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                })
            messages = [{"role": "user", "content": content}]
        else:
            messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "messages": messages,
            # Ask OpenRouter to include cost/accounting in the usage object.
            "extra_body": {"usage": {"include": True}},
            # Optional attribution headers (good OpenRouter citizenship).
            "extra_headers": {
                "HTTP-Referer": "https://github.com/srinis76/pid-assistant",
                "X-Title": "P&ID Assistant",
            },
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["temperature"] = 0.1

        response = self.openrouter_client.chat.completions.create(**kwargs)

        usage = response.usage
        tokens = {
            "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        }
        # OpenRouter returns the real cost (USD) when usage.include is set.
        actual_cost = getattr(usage, "cost", None)
        if actual_cost is None and hasattr(usage, "model_extra"):
            actual_cost = (usage.model_extra or {}).get("cost")
        if actual_cost is not None:
            tokens["actual_cost"] = float(actual_cost)

        return response.choices[0].message.content, tokens

    def _call_claude(
        self,
        prompt: str,
        images: Optional[List[str]]
    ) -> Tuple[str, Dict]:
        """Call Claude API"""

        # Prepare content
        if images:
            # Vision query
            content = []
            for img_b64 in images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64
                    }
                })
            content.append({"type": "text", "text": prompt})
        else:
            # Text-only
            content = prompt

        # Call API
        response = self.claude_client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": content}]
        )

        # Extract tokens
        tokens = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }

        return response.content[0].text, tokens

    def _calculate_cost(self, tokens: Dict) -> float:
        """Calculate estimated cost based on provider pricing"""

        # OpenRouter returns the true cost of the call — prefer it over any
        # static pricing table (no per-model maintenance needed).
        if "actual_cost" in tokens:
            return tokens["actual_cost"]

        # Pricing per million tokens (as of Jan 2025)
        pricing = {
            "gemini": {
                "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
                "gemini-2.5-flash-lite": {"input": 0.0, "output": 0.0},  # Free tier
                "gemini-1.5-pro": {"input": 1.25, "output": 5.00}
            },
            "openai": {
                "gpt-4o-mini": {"input": 0.15, "output": 0.60},
                "gpt-4o": {"input": 5.00, "output": 15.00}
            },
            "claude": {
                "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
                "claude-haiku-3-5-20250103": {"input": 0.80, "output": 4.00}
            }
        }

        # Get pricing for current provider/model
        if self.provider in pricing:
            if self.model in pricing[self.provider]:
                rates = pricing[self.provider][self.model]
            else:
                # Use first model as default
                rates = list(pricing[self.provider].values())[0]
        else:
            return 0.0

        # Calculate cost (pricing is per million tokens)
        cost = (
            (tokens["input_tokens"] * rates["input"] / 1_000_000) +
            (tokens["output_tokens"] * rates["output"] / 1_000_000)
        )

        return cost

    def _log_usage(self, tokens: Dict, elapsed: float, query_type: str = "rag"):
        """Log token usage and cost"""

        cost = self._calculate_cost(tokens)

        # Update session stats
        self.session_stats['total_queries'] += 1
        self.session_stats['total_input_tokens'] += tokens['input_tokens']
        self.session_stats['total_output_tokens'] += tokens['output_tokens']
        self.session_stats['total_cost'] += cost
        self.session_stats['queries_by_type'][query_type] += 1

        # Console output
        if self.verbose_logging:
            print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 LLM API Call Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provider: {self.provider}
Model: {self.model}
Query Type: {query_type}
Input Tokens: {tokens['input_tokens']:,}
Output Tokens: {tokens['output_tokens']:,}
Total Tokens: {tokens['total_tokens']:,}
Response Time: {elapsed:.2f}s
Estimated Cost: ${cost:.6f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

        # Write to log file (JSON)
        self._write_log(tokens, cost, elapsed, query_type)

    def _write_log(self, tokens: Dict, cost: float, elapsed: float, query_type: str):
        """Write log entry to file"""

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": self.provider,
            "model": self.model,
            "query_type": query_type,
            "input_tokens": tokens["input_tokens"],
            "output_tokens": tokens["output_tokens"],
            "total_tokens": tokens["total_tokens"],
            "response_time_seconds": round(elapsed, 2),
            "estimated_cost_usd": round(cost, 6)
        }

        log_file = log_dir / "query_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_session_summary(self) -> str:
        """Get session statistics summary"""

        stats = self.session_stats

        summary = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Session Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provider: {self.provider}
Model: {self.model}

Total Queries: {stats['total_queries']}
  - RAG Queries: {stats['queries_by_type']['rag']}
  - Vision Queries: {stats['queries_by_type']['vision']}

Token Usage:
  - Input Tokens: {stats['total_input_tokens']:,}
  - Output Tokens: {stats['total_output_tokens']:,}
  - Total Tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}

Total Cost: ${stats['total_cost']:.6f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return summary


# Test function
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Testing LLM Adapter")
    print("="*60 + "\n")

    # Initialize adapter
    adapter = LLMAdapter()

    # Test text-only query
    print("📝 Testing text-only query...")
    response = adapter.call_llm(
        prompt="What is a pressure separator in oil and gas operations? Answer in 2 sentences.",
        query_type="rag"
    )
    print(f"\nResponse:\n{response}\n")

    # Display session summary
    print(adapter.get_session_summary())

    print("="*60)
    print("✅ LLM Adapter test complete!")
    print("="*60 + "\n")

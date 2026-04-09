"""Prompt builder: uses llama3.2 to compress context into efficient Claude Code prompts."""
import logging
from typing import List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

SYSTEM = (
    "You are an expert at compressing code context into minimal, high-density prompts for Claude Code. "
    "Output ONLY the final prompt. No explanations, no preamble, no markdown wrapper."
)

TEMPLATE = """\
## DEVELOPER TASK
{task}

## RELEVANT CODE CONTEXT (from RAG)
{context}

## DETECTED PATTERNS
{patterns}

---
Generate a compact prompt for Claude Code that:
1. Summarizes the project in 2-3 lines (tech stack + key patterns)
2. Lists only the most relevant files (max 5) with essential code snippets
3. States the task precisely and specifically
4. Includes constraints: patterns to follow, things to avoid
5. Stays under 700 tokens total

OUTPUT THE PROMPT:"""


def _format_context(chunks: List[dict]) -> str:
    if not chunks:
        return "No relevant context found."
    seen, parts = set(), []
    for chunk in chunks[:8]:
        meta = chunk.get("metadata", {})
        fp = meta.get("file", "unknown")
        lang = meta.get("language", "")
        content = chunk.get("content", "")
        if fp not in seen:
            parts.append(f"\n### {fp}")
            seen.add(fp)
        if len(content) > 700:
            content = content[:700] + "\n...[truncated]"
        parts.append(f"```{lang}\n{content}\n```")
    return "\n".join(parts)


def _detect_patterns(chunks: List[dict]) -> str:
    langs = {c.get("metadata", {}).get("language") for c in chunks} - {None, ""}
    patterns = [f"- Languages: {', '.join(sorted(langs))}"] if langs else []

    has_tests = any("test" in (c.get("metadata", {}).get("file") or "").lower() for c in chunks)
    if has_tests:
        patterns.append("- Test suite present (maintain coverage)")

    has_async = any(
        kw in c.get("content", "")
        for c in chunks
        for kw in ("async def", "async function", "await ")
    )
    if has_async:
        patterns.append("- Async/await patterns in use")

    return "\n".join(patterns) or "- No specific patterns detected"


async def build_prompt(task: str, chunks: List[dict]) -> str:
    context = _format_context(chunks)
    patterns = _detect_patterns(chunks)
    user_prompt = TEMPLATE.format(task=task, context=context, patterns=patterns)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={
                    "model": settings.CHAT_MODEL,
                    "system": SYSTEM,
                    "prompt": user_prompt,
                    "stream": False,
                    "options": {"num_predict": 1200, "temperature": 0.15, "top_p": 0.9},
                },
            )
            return r.json()["response"].strip()
    except Exception as e:
        logger.error(f"Prompt build error: {e}")
        # Fallback: return structured raw context
        return f"## Task\n{task}\n\n## Context\n{context}\n\n## Patterns\n{patterns}"


def estimate_tokens(text: str) -> int:
    return len(text) // 4

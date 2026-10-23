"""Ask-AI: a plain tool-calling agent loop (notebook 15) on the local Qwen2.5-1.5B-Instruct.

Loop: the LLM sees the question + tool schemas → emits <tool_call>{"name", "arguments"}</tool_call> → code runs the tool
→ the result goes back as a "tool" message → repeat (max 3 calls) until the LLM answers in plain text.
"""
import json
import re

from glp1_intel.agent.tools import TOOL_MAP, TOOLS
from glp1_intel.rag.generate import llm

SYSTEM = """You are Ask-AI, an assistant for a pharmaceutical sales-analytics team working on GLP-1 drugs.
- For any number, doctor list, side-effect count or drug-label fact, call a tool. Never invent numbers.
- Call one tool at a time. When you have what you need, answer in at most 4 sentences using only the tool results,
  and name the data source (Medicare Part D 2024, FDA FAERS, FDA label, or visit notes).
- If no tool can answer the question, say so instead of guessing."""

TOOL_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def _generate(messages: list[dict], max_new_tokens: int) -> str:
    import torch
    tok, model = llm()
    enc = tok.apply_chat_template(messages, tools=TOOLS, add_generation_prompt=True, return_tensors="pt", return_dict=True)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tok.eos_token_id)
    return tok.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def parse_tool_calls(text: str) -> list[dict]:
    """Tool calls in Qwen's <tool_call>{json}</tool_call> format. Invalid JSON is returned as an error entry."""
    calls = []
    for raw in TOOL_CALL.findall(text):
        try:
            c = json.loads(raw)
            calls.append({"name": c.get("name"), "arguments": c.get("arguments") or {}})
        except json.JSONDecodeError as e:
            calls.append({"name": None, "arguments": {}, "error": f"invalid JSON: {e.msg}"})
    return calls


def run_tool(call: dict) -> str:
    if call.get("error"):
        return f"Error: {call['error']}"
    fn = TOOL_MAP.get(call["name"])
    if fn is None:
        return f"Error: unknown tool '{call['name']}'. Available: {', '.join(TOOL_MAP)}."
    try:
        return fn(**call["arguments"])
    except TypeError as e:          # wrong or missing arguments: tell the model, let it retry
        return f"Error: bad arguments for {call['name']}: {e}"


def ask(question: str, max_calls: int = 3) -> dict:
    """Run the loop. Returns the final answer and every step (tool, arguments, result) for inspection."""
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    steps = []
    for _ in range(max_calls + 1):
        text = _generate(messages, max_new_tokens=220)
        calls = parse_tool_calls(text)
        if not calls or len(steps) >= max_calls:
            return {"question": question, "answer": TOOL_CALL.sub("", text).strip(), "steps": steps}
        call = calls[0]                              # one tool at a time keeps the loop simple and auditable
        result = run_tool(call)
        steps.append({**call, "result": result})
        messages.append({"role": "assistant", "content": "",
                         "tool_calls": [{"type": "function", "function": {"name": call["name"] or "invalid",
                                                                          "arguments": call["arguments"]}}]})
        messages.append({"role": "tool", "name": call["name"] or "invalid", "content": result})
    return {"question": question, "answer": "", "steps": steps}


# ── Baseline: a keyword router (no LLM) ─────────────────────────────────────
ROUTES = [
    ("side_effect_reports", r"faers|reported|reports|adverse event report|side effects? (are|were) reported"),
    ("visit_note_insights", r"\bnotes?\b|reps? (hear|say)|objection|doctors (say|complain|worry)"),
    ("top_doctors", r"\bdoctors?\b|prescribers?|endocrinologists?|physicians?|\bnps?\b|target|prioriti"),
    ("market_summary", r"share|market|claims|how many|segment"),
    ("label_answer", r"dose|dosing|label|warning|contraindicat|interact|approved|indicat|storage|store|pregnan|side effect"),
]


def route_keywords(question: str) -> str | None:
    """First matching rule wins: the cheap, transparent alternative to letting the LLM choose."""
    for name, pat in ROUTES:
        if re.search(pat, question, re.I):
            return name
    return None


# ── Provenance, enforced by code ────────────────────────────────────────────
def finalize(answer: str, steps: list[dict]) -> str:
    """What the user sees. Code (not the LLM) appends which tools ran and carries forward any warning a tool raised,
    so a flag from the label guard cannot be dropped when the LLM rephrases the tool result."""
    warnings = [s["name"] for s in steps if "flagged for human review" in s["result"] or "answer blocked" in s["result"]]
    used = ", ".join(dict.fromkeys(s["name"] for s in steps)) or "none (answered without data)"
    out = answer
    if warnings:
        out = ("⚠️ Verify before use: the " + " and ".join(warnings) + " result behind this answer was flagged as not fully "
               "supported by its sources.\n\n" + out)
    return out + f"\n\n— Tools used: {used}."

"""Batched note generation with an open model + quality gate + resume. Standalone: Colab downloads this file.

Each scenario gets up to `max_attempts` tries; a note is kept only if gate.check() finds no problem.
Progress is appended to a JSONL file after every batch, so a Colab disconnect loses at most one batch.
"""
import json
import time
from pathlib import Path

import torch

import gate


def _chat(prompt: dict, brief: str) -> list[dict]:
    msgs = [{"role": "system", "content": prompt["system"]}]
    for ex in prompt["few_shot"]:
        msgs += [{"role": "user", "content": ex["user"]}, {"role": "assistant", "content": ex["assistant"]}]
    return msgs + [{"role": "user", "content": brief}]


def _done_ids(out_path: Path) -> set:
    if not out_path.exists():
        return set()
    return {json.loads(line)["scenario_id"] for line in out_path.open(encoding="utf-8")}


@torch.no_grad()
def run(model, tok, scenarios: list[dict], prompt: dict, out_path, batch_size: int = 16,
        max_attempts: int = 3, max_new_tokens: int = 260, temperature: float = 0.8) -> dict:
    out_path = Path(out_path)
    tok.padding_side = "left"                              # decoder-only models must be left-padded for batching
    pending = [s for s in scenarios if s["scenario_id"] not in _done_ids(out_path)]
    last_problem = {}
    t0, n_generated = time.time(), 0
    for attempt in range(1, max_attempts + 1):
        still_failing = []
        for i in range(0, len(pending), batch_size):
            batch = pending[i:i + batch_size]
            texts = [tok.apply_chat_template(_chat(prompt, s["brief"]), tokenize=False, add_generation_prompt=True)
                     for s in batch]
            enc = tok(texts, return_tensors="pt", padding=True).to(model.device)
            out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=True, temperature=temperature,
                                 top_p=0.9, pad_token_id=tok.pad_token_id)
            notes = tok.batch_decode(out[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
            n_generated += len(batch)
            with out_path.open("a", encoding="utf-8") as f:
                for s, note in zip(batch, notes):
                    note = note.strip()
                    problems = gate.check(note, s)
                    if problems and attempt < max_attempts:
                        still_failing.append(s)
                        last_problem[s["scenario_id"]] = problems
                        continue
                    rec = {k: v for k, v in s.items() if k != "brief"}
                    rec.update(note=note, attempt=attempt, passed=not problems, problems=problems)
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done = len(_done_ids(out_path))
            rate = n_generated / (time.time() - t0)
            print(f"attempt {attempt} · batch {i // batch_size + 1}/{-(-len(pending) // batch_size)} · "
                  f"saved {done}/{len(scenarios)} · {rate:.1f} notes/s · {(time.time() - t0) / 60:.1f} min", flush=True)
        pending = still_failing
        if not pending:
            break
    recs = [json.loads(line) for line in out_path.open(encoding="utf-8")]
    return {"saved": len(recs), "passed": sum(r["passed"] for r in recs),
            "first_try_pass": sum(r["passed"] and r["attempt"] == 1 for r in recs),
            "minutes": round((time.time() - t0) / 60, 1)}

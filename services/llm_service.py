import ollama
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

AVAILABLE_MODELS = ["llama3.2", "mistral", "gemma"]


def run_completion(messages: list, model: str = "llama3.2") -> str:
    if model not in AVAILABLE_MODELS:
        raise ValueError(f"Unknown model: {model}")
    response = ollama.chat(model=model, messages=messages)
    return response["message"]["content"]

def _call_model(messages: list, model: str) -> tuple[str, str]:
    """Returns (model_name, response_text). Blocking."""
    response = ollama.chat(model=model, messages=messages)
    return model, response["message"]["content"]

def _rate_response(judge: str, question: str, candidate_model: str, candidate_answer: str) -> tuple[str, int]:
    """
    Ask `judge` to score `candidate_answer` 1-10.
    Returns (candidate_model, score).
    """
    prompt = (
        f"You are a strict but fair judge. "
        f"Rate the following answer to the question on a scale of 1-10 "
        f"for accuracy, clarity, and helpfulness. "
        f"Reply with ONLY a single integer between 1 and 10, nothing else.\n\n"
        f"Question: {question}\n\n"
        f"Answer: {candidate_answer}"
    )
    response = ollama.chat(
        model=judge,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response["message"]["content"].strip()
    # extract first integer found, fallback to 5
    import re
    match = re.search(r"\b([1-9]|10)\b", raw)
    score = int(match.group(1)) if match else 5
    return candidate_model, score


def run_arena_stream(messages: list):
    user_question = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    responses = {}
    scores = {m: 0 for m in AVAILABLE_MODELS}
    total_votes = len(AVAILABLE_MODELS) * (len(AVAILABLE_MODELS) - 1)
    votes_done = 0

    with ThreadPoolExecutor(max_workers=len(AVAILABLE_MODELS) ** 2) as ex:
        # ── submit all model calls ──
        response_futures = {ex.submit(_call_model, messages, m): m for m in AVAILABLE_MODELS}
        pending = set(response_futures.keys())
        vote_futures = {}

        while pending or vote_futures:
            # check which futures completed this iteration
            done_this_round = {f for f in pending | set(vote_futures.keys()) if f.done()}

            for f in done_this_round:
                if f in pending:
                    # ── a model response just arrived ──
                    model, text = f.result()
                    responses[model] = text
                    pending.discard(f)
                    yield f"data: {json.dumps({'type': 'response', 'model': model, 'text': text, 'done': len(responses), 'total': len(AVAILABLE_MODELS)})}\n\n"

                    # immediately submit votes: this new model judges existing responses,
                    # and existing models judge this new response
                    for candidate, answer in responses.items():
                        if candidate != model:
                            # new model judges existing candidates
                            key = (model, candidate)
                            if key not in vote_futures.values():
                                vf = ex.submit(_rate_response, model, user_question, candidate, answer)
                                vote_futures[vf] = key
                            # existing models judge new response
                            key2 = (candidate, model)
                            if key2 not in vote_futures.values():
                                vf2 = ex.submit(_rate_response, candidate, user_question, model, text)
                                vote_futures[vf2] = key2

                elif f in vote_futures:
                    # ── a vote just arrived ──
                    judge, candidate = vote_futures.pop(f)
                    _, score = f.result()
                    scores[candidate] += score
                    votes_done += 1
                    yield f"data: {json.dumps({'type': 'vote', 'judge': judge, 'candidate': candidate, 'votes_done': votes_done, 'votes_total': total_votes})}\n\n"

            if not done_this_round:
                import time
                time.sleep(0.05)  # small sleep to avoid busy-wait

    winner = max(scores, key=lambda m: scores[m])
    yield f"data: {json.dumps({'type': 'result', 'responses': responses, 'scores': scores, 'winner': winner})}\n\n"
import ollama

AVAILABLE_MODELS = ["llama3.2", "mistral", "gemma"]

def run_completion(messages: list, model: str = "llama3.2") -> str:
    if model not in AVAILABLE_MODELS:
        raise ValueError(f"Unknown model: {model}")
    response = ollama.chat(model=model, messages=messages)
    return response["message"]["content"]
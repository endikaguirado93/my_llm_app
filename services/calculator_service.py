def calculate(expression: str) -> str:
    try:
        result = eval(expression)  # simple version
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"
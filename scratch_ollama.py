import ollama
import json

try:
    res = ollama.list()
    print("Full Response Type:", type(res))
    print("Full Response Content:")
    # If it's a list of objects, we can't just json.dump it if they aren't serializable
    # So we'll iterate and print
    if isinstance(res, list):
        for item in res:
            print(item)
    elif hasattr(res, 'models'):
        for model in res.models:
            print(f"Model: {model}")
    else:
        print(res)
except Exception as e:
    print(f"Error: {e}")

import httpx
import asyncio
from core.constants import SWITCHES

async def unload_ollama_model(model: str, port: int = 11434):
    """
    Unloads a given Ollama model from memory via API request.

    Args:
        model (str): The name of the model to unload (e.g. "llama3.2").
        port (int): The local Ollama API port (default: 11434).

    Example:
        asyncio.run(unload_ollama_model("llama3.2"))
    """
    url = f"http://localhost:{port}/api/generate"
    payload = {"model": model, "keep_alive": 0}

    try:
        print(f"Attempting to unload model '{model}' on port {port}...")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            if isinstance(data, dict) and "error" in data:
                print(f"Ollama returned an error: {data['error']}")
            else:
                print(f"Successfully requested unload for model '{model}'.")

    except httpx.ConnectError:
        if not SWITCHES["REMOTE_GPU"]:
            print(
                f"Failed to connect to Ollama API at {url}. "
                "Is the Ollama service running?"
            )
    except httpx.TimeoutException:
        print("Request to Ollama API timed out.")
    except httpx.HTTPStatusError as e:
        print(f"An unexpected HTTP error occurred: {e}")
    except httpx.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except ValueError:
        print("Could not parse the response from Ollama API.")
    except Exception as e:
        print(f"Unexpected error: {e}")

from loguru import logger
from openai import OpenAI
from typing import Optional
import httpx


def ask_chatgpt(api_key: str, model: str, user_message: str, prompt: str, proxy: str = "") -> tuple[bool, str]:
    """
    Send a message to ChatGPT and get a response, supporting both SOCKS5 and HTTP proxies.

    Args:
        api_key (str): OpenAI API key
        model (str): Model name
        user_message (str): The message to send to ChatGPT
        prompt (str): System prompt
        proxy (str): Proxy in format [protocol://][user:pass@]ip:port
                    e.g., socks5://user:pass@ip:port or http://ip:port

    Returns:
        tuple[bool, str]: (success_flag, response_message)
    """
    client_params = {"api_key": api_key}

    if proxy:
        logger.info(f"Using proxy: {proxy} for ChatGPT")
        # Add protocol scheme if not present
        if not proxy.startswith(("http://", "https://", "socks5://", "socks5h://")):
            proxy = f"http://{proxy}"

        # Configure proxy settings
        http_client = httpx.Client(
            proxies={
                "http://": proxy,
                "https://": proxy
            }
        )
        client_params["http_client"] = http_client
    else:
        # Use default HTTP client without proxy
        http_client = httpx.Client()
        client_params["http_client"] = http_client

    try:
        # Initialize OpenAI client
        client = OpenAI(**client_params)

        # Prepare the messages
        messages = []
        if prompt:
            messages.append({"role": "system", "content": prompt})
        messages.append({"role": "user", "content": user_message})

        # Make the API call
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        # Extract and return the response text
        response_text = response.choices[0].message.content
        return True, response_text

    except Exception as e:
        error_str = str(e).lower()
        if "rate limit" in error_str:
            return False, "GPT rate limit reached, please try again later."
        elif "quota" in error_str or "exceeded" in error_str:
            return False, "Your ChatGPT API key has no balance."
        else:
            logger.error(f"ChatGPT error: {str(e)}")
            return False, f"GPT Error occurred: {str(e)}"
    finally:
        # Ensure http_client is closed
        if 'http_client' in locals():
            http_client.close()


# Usage example
if __name__ == "__main__":
    # Test different proxy configurations
    api_key = "your_api_key"
    model = "gpt-3.5-turbo"
    message = "Hello!"
    prompt = "You are a helpful AI"

    # Test with HTTP proxy
    result = ask_chatgpt(api_key, model, message, prompt, "http://user:pass@127.0.0.1:8080")
    print("HTTP Proxy:", result)

    # Test with SOCKS5 proxy
    result = ask_chatgpt(api_key, model, message, prompt, "socks5://user:pass@127.0.0.1:1080")
    print("SOCKS5 Proxy:", result)

    # Test without proxy
    result = ask_chatgpt(api_key, model, message, prompt)
    print("No Proxy:", result)
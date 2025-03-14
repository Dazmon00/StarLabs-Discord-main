from loguru import logger
import httpx
from typing import Optional
import json

async def ask_deepseek(api_key: str, model: str, user_message: str, prompt: str, proxy: str = "") -> tuple[bool, str]:
    """
    向DeepSeek模型发送消息并获取响应。

    Args:
        api_key (str): DeepSeek API密钥
        model (str): 模型名称
        user_message (str): 发送给DeepSeek的消息
        prompt (str): 系统提示词
        proxy (str): 代理地址，格式为user:pass@ip:port或ip:port

    Returns:
        tuple[bool, str]: (是否成功, 响应消息)
    """
    if proxy:
        logger.info(f"使用代理: {proxy} 连接DeepSeek")
        if not proxy.startswith(("http://", "https://")):
            proxy = f"http://{proxy}"
        async with httpx.AsyncClient(proxy=proxy) as http_client:
            return await _make_request(http_client, api_key, model, user_message, prompt)
    else:
        async with httpx.AsyncClient() as http_client:
            return await _make_request(http_client, api_key, model, user_message, prompt)

async def _make_request(http_client: httpx.AsyncClient, api_key: str, model: str, user_message: str, prompt: str) -> tuple[bool, str]:
    """发送请求到DeepSeek API"""
    # 准备请求数据
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 构建消息列表
    messages = []
    if prompt:
        messages.append({"role": "system", "content": prompt})
    messages.append({"role": "user", "content": user_message})

    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        # 发送API请求
        response = await http_client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            response_data = response.json()
            response_text = response_data["choices"][0]["message"]["content"]
            return True, response_text
        else:
            error_message = response.text
            if "rate_limit" in error_message.lower():
                return False, "DeepSeek API达到速率限制，请稍后重试"
            elif "quota" in error_message.lower():
                return False, "DeepSeek API密钥余额不足"
            else:
                return False, f"DeepSeek API错误: {error_message}"

    except httpx.TimeoutException:
        return False, "DeepSeek API请求超时"
    except Exception as e:
        if "rate_limit" in str(e).lower():
            return False, "DeepSeek API达到速率限制，请稍后重试"
        elif "quota" in str(e).lower():
            return False, "DeepSeek API密钥余额不足"
        else:
            return False, f"DeepSeek错误: {str(e)}" 
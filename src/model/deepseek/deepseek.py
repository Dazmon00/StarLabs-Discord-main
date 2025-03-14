from loguru import logger
import httpx
from typing import Optional
import json


async def ask_deepseek(api_key: str, model: str, user_message: str, prompt: str, proxy: str = "") -> tuple[bool, str]:
    """
    向DeepSeek模型发送消息并获取响应，支持SOCKS5和HTTP代理。

    Args:
        api_key (str): DeepSeek API密钥
        model (str): 模型名称
        user_message (str): 发送给DeepSeek的消息
        prompt (str): 系统提示词
        proxy (str): 代理地址，格式为 [protocol://][user:pass@]ip:port
                   例如: socks5://user:pass@ip:port 或 http://ip:port

    Returns:
        tuple[bool, str]: (是否成功, 响应消息)
    """
    client_params = {}

    if proxy:
        logger.info(f"使用代理: {proxy} 连接DeepSeek")
        # 检测代理协议类型
        if not proxy.startswith(("http://", "https://", "socks5://", "socks5h://")):
            # 默认添加 http:// 前缀（向后兼容）
            proxy = f"http://{proxy}"

        # 配置代理字典
        client_params["proxies"] = {
            "http://": proxy,
            "https://": proxy
        }

    try:
        async with httpx.AsyncClient(**client_params) as http_client:
            return await _make_request(http_client, api_key, model, user_message, prompt)
    except Exception as e:
        logger.error(f"代理配置错误: {str(e)}")
        return False, f"代理配置错误: {str(e)}"


async def _make_request(http_client: httpx.AsyncClient, api_key: str, model: str, user_message: str, prompt: str) -> \
tuple[bool, str]:
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


# 使用示例
if __name__ == "__main__":
    import asyncio


    async def test():
        # 测试不同类型的代理
        api_key = "your_api_key"
        model = "deepseek-chat"
        message = "Hello!"
        prompt = "You are a helpful AI"

        # 测试 HTTP 代理
        result = await ask_deepseek(api_key, model, message, prompt, "http://user:pass@127.0.0.1:8080")
        print("HTTP Proxy:", result)

        # 测试 SOCKS5 代理
        result = await ask_deepseek(api_key, model, message, prompt, "socks5://user:pass@127.0.0.1:1080")
        print("SOCKS5 Proxy:", result)

        # 测试无代理
        result = await ask_deepseek(api_key, model, message, prompt)
        print("No Proxy:", result)


    asyncio.run(test())
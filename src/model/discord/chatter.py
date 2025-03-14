import asyncio
from dataclasses import dataclass
from loguru import logger
import random
from curl_cffi.requests import AsyncSession

from src.model.discord.utils import calculate_nonce
from src.utils.config import Config
from src.model.gpt import ask_chatgpt
from src.model.gpt.prompts import (
    BATCH_MESSAGES_SYSTEM_PROMPT as GPT_BATCH_MESSAGES_SYSTEM_PROMPT,
    REFERENCED_MESSAGES_SYSTEM_PROMPT as GPT_REFERENCED_MESSAGES_SYSTEM_PROMPT,
)
from src.model.deepseek.deepseek import ask_deepseek
from src.model.deepseek.prompts import (
    BATCH_MESSAGES_SYSTEM_PROMPT as DEEPSEEK_BATCH_MESSAGES_SYSTEM_PROMPT,
    REFERENCED_MESSAGES_SYSTEM_PROMPT as DEEPSEEK_REFERENCED_MESSAGES_SYSTEM_PROMPT,
)
from src.utils.constants import Account


@dataclass
class ReceivedMessage:
    """Represents a message received from Discord"""
    type: int
    content: str
    message_id: str
    channel_id: str
    author_id: str
    author_username: str
    referenced_message_content: str
    referenced_message_author_id: str


class DiscordChatter:
    def __init__(
            self,
            account: Account,
            client: AsyncSession,
            config: Config,
    ):
        self.account = account
        self.client = client
        self.config = config
        self.my_account_id: str = ""
        self.my_account_username: str = ""
        self.my_replies_messages: list = []

    async def start_chatting(self) -> bool:
        # 检查 excel_guild_id 和 excel_channel_id 是否都存在且不为空
        use_excel_ids = (
                hasattr(self.account, 'excel_guild_id') and self.account.excel_guild_id and
                hasattr(self.account, 'excel_channel_id') and self.account.excel_channel_id
        )

        # 根据条件选择 guild_id 和 channel_id
        if use_excel_ids:
            guild_id = self.account.excel_guild_id
            channel_id = self.account.excel_channel_id
            logger.info(f"{self.account.index} | Using Excel IDs - guild_id: {guild_id}, channel_id: {channel_id}")
        else:
            guild_id = self.config.AI_CHATTER.GUILD_ID
            channel_id = self.config.AI_CHATTER.CHANNEL_ID
            logger.info(f"{self.account.index} | Using default IDs - guild_id: {guild_id}, channel_id: {channel_id}")

        number_of_messages_to_send = random.randint(
            self.config.AI_CHATTER.MESSAGES_TO_SEND_PER_ACCOUNT[0],
            self.config.AI_CHATTER.MESSAGES_TO_SEND_PER_ACCOUNT[1],
        )
        for message_index in range(number_of_messages_to_send):
            for retry_index in range(self.config.SETTINGS.ATTEMPTS):
                try:
                    message_sent = False
                    replied_to_me = False
                    last_messages = await self._get_last_chat_messages(guild_id, channel_id)
                    logger.info(f"{self.account.index} | Last messages: {len(last_messages)} ")

                    if self.my_account_id:
                        replies_to_me = [
                            msg
                            for msg in last_messages
                            if msg.referenced_message_author_id == self.my_account_id
                               and msg.message_id not in self.my_replies_messages
                               and msg.author_username != self.my_account_username
                        ]

                        if replies_to_me:
                            should_answer = (
                                                    random.random() * 100
                                            ) < self.config.AI_CHATTER.ANSWER_PERCENTAGE

                            if should_answer:
                                message = random.choice(replies_to_me)
                                logger.info(
                                    f"{self.account.index} | Replying to {message.author_username} who replied to our message. "
                                    f"Their message: {message.content}"
                                )
                                gpt_response = await self._deepseek_referenced_messages(
                                    message.content,
                                    message.referenced_message_content,
                                )
                                gpt_response = (
                                    gpt_response.replace("```", "")
                                    .replace("```python", "")
                                    .replace("```", "")
                                    .replace('"', "")
                                )
                                random_pause = random.randint(
                                    self.config.AI_CHATTER.PAUSE_BEFORE_MESSAGE[0],
                                    self.config.AI_CHATTER.PAUSE_BEFORE_MESSAGE[1],
                                )
                                logger.info(
                                    f"{self.account.index} | GPT response: {gpt_response}. Pausing for {random_pause} seconds before sending message."
                                )
                                await asyncio.sleep(random_pause)
                                ok, json_response = await self._send_message(
                                    gpt_response,
                                    channel_id,
                                    guild_id,
                                    message.message_id,
                                )

                                if ok:
                                    logger.success(
                                        f"{self.account.index} | Message with reply to my message sent: {gpt_response}"
                                    )
                                    self.my_account_id = json_response["author"]["id"]
                                    self.my_account_username = json_response["author"]["username"]
                                    self.my_replies_messages.append(message.message_id)
                                    message_sent, replied_to_me = True, True
                            else:
                                logger.info(
                                    f"{self.account.index} | Skipping reply due to answer_percentage"
                                )

                    if not replied_to_me:
                        replyable_messages = [
                            msg
                            for msg in last_messages
                            if msg.referenced_message_content
                               and msg.author_username != self.my_account_username
                        ]

                        should_reply = (
                                (random.random() * 100) < self.config.AI_CHATTER.REPLY_PERCENTAGE
                                and replyable_messages
                        )

                        if should_reply:
                            message = random.choice(replyable_messages)
                            logger.info(
                                f"{self.account.index} | Sending reply message to {message.author_username}. Main message: {message.content}. Referenced message: {message.referenced_message_content}"
                            )
                            gpt_response = await self._deepseek_referenced_messages(
                                message.content,
                                message.referenced_message_content,
                            )
                            gpt_response = (
                                gpt_response.replace("```", "")
                                .replace("```python", "")
                                .replace("```", "")
                                .replace('"', "")
                            )

                            random_pause = random.randint(
                                self.config.AI_CHATTER.PAUSE_BEFORE_MESSAGE[0],
                                self.config.AI_CHATTER.PAUSE_BEFORE_MESSAGE[1],
                            )
                            logger.info(
                                f"{self.account.index} | GPT response: {gpt_response}. Pausing for {random_pause} seconds before sending message."
                            )
                            await asyncio.sleep(random_pause)
                            ok, json_response = await self._send_message(
                                gpt_response,
                                channel_id,
                                guild_id,
                                message.message_id,
                            )

                            if ok:
                                logger.success(
                                    f"{self.account.index} | Message with reply sent: {gpt_response}"
                                )
                                self.my_account_id = json_response["author"]["id"]
                                message_sent = True

                        else:
                            messages_contents = "| ".join(
                                [message.content for message in last_messages]
                            )
                            gpt_response = await self._deepseek_batch_messages(
                                messages_contents,
                            )
                            gpt_response = (
                                gpt_response.replace("```", "")
                                .replace("```python", "")
                                .replace("```", "")
                                .replace('"', "")
                            )

                            random_pause = random.randint(
                                self.config.AI_CHATTER.PAUSE_BEFORE_MESSAGE[0],
                                self.config.AI_CHATTER.PAUSE_BEFORE_MESSAGE[1],
                            )
                            logger.info(
                                f"{self.account.index} | GPT response: {gpt_response}. Pausing for {random_pause} seconds before sending message."
                            )
                            await asyncio.sleep(random_pause)

                            ok, json_response = await self._send_message(
                                gpt_response,
                                channel_id,
                                guild_id,
                            )

                            if ok:
                                logger.success(
                                    f"{self.account.index} | Message sent with no reply: {gpt_response}"
                                )
                                self.my_account_id = json_response["author"]["id"]
                                message_sent = True

                    if message_sent:
                        random_pause = random.randint(
                            self.config.AI_CHATTER.PAUSE_BETWEEN_MESSAGES[0],
                            self.config.AI_CHATTER.PAUSE_BETWEEN_MESSAGES[1],
                        )
                        logger.info(
                            f"{self.account.index} | Pausing for {random_pause} seconds before next message."
                        )
                        await asyncio.sleep(random_pause)
                        break

                    else:
                        random_pause = random.randint(
                            self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                            self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                        )
                        logger.info(
                            f"{self.account.index} | No message send. Pausing for {random_pause} seconds before next try."
                        )
                        await asyncio.sleep(random_pause)

                except Exception as e:
                    logger.error(f"{self.account.index} | Error in start_chatting: {e}")
                    return False

    async def _send_message(
            self,
            message: str,
            channel_id: str,
            guild_id: str,
            reply_to_message_id: str = None,
    ) -> tuple[bool, dict]:
        try:
            # 使用账号特定的代理创建 AsyncSession
            proxy = self.account.proxy
            if proxy and not proxy.startswith(("http://", "https://", "socks5://", "socks5h://")):
                proxy = f"http://{proxy}"  # 默认添加 HTTP 前缀

            # 隐藏代理的用户名和密码，只保留协议和地址部分
            if proxy:
                protocol = proxy.split("://")[0]  # 提取协议（如 socks5 或 http）
                address = proxy.split("@")[-1] if "@" in proxy else proxy.split("://")[1]  # 提取 IP:端口
                masked_proxy = f"{protocol}://[hidden]@{address}"
            else:
                masked_proxy = "None"

            async with AsyncSession(
                    proxies={"http": proxy, "https": proxy} if proxy else None,
                    impersonate="chrome"
            ) as client:
                headers = {
                    "authorization": self.account.token,
                    "content-type": "application/json",
                    "origin": "https://discord.com",
                    "referer": f"https://discord.com/channels/{guild_id}/{channel_id}",
                    "x-debug-options": "bugReporterEnabled",
                    "x-discord-locale": "en-US",
                    "x-discord-timezone": "Etc/GMT-2",
                }

                json_data = {
                    "mobile_network_type": "unknown",
                    "content": message,
                    "nonce": calculate_nonce(),
                    "tts": False,
                    "flags": 0,
                }

                if reply_to_message_id:
                    json_data["message_reference"] = {
                        "guild_id": guild_id,
                        "channel_id": channel_id,
                        "message_id": reply_to_message_id,
                    }

                logger.info(f"{self.account.index} | Sending message using proxy: {masked_proxy}")
                response = await client.post(
                    f"https://discord.com/api/v9/channels/{channel_id}/messages",
                    headers=headers,
                    json=json_data,
                )

                if response.status_code != 200:
                    logger.error(
                        f"{self.account.index} | Send message failed: {response.status_code} - {response.text}")
                    return False, {}

                return True, response.json()

        except Exception as e:
            logger.error(f"{self.account.index} | Error in send_message: {e}")
            return False, {}

    async def _get_last_chat_messages(
            self, guild_id: str, channel_id: str, quantity: int = 50
    ) -> list[ReceivedMessage]:
        try:
            # 使用账号特定的代理创建 AsyncSession
            proxy = self.account.proxy
            if proxy and not proxy.startswith(("http://", "https://", "socks5://", "socks5h://")):
                proxy = f"http://{proxy}"  # 默认添加 HTTP 前缀

            # 隐藏代理的用户名和密码，只保留协议和地址部分
            if proxy:
                protocol = proxy.split("://")[0]  # 提取协议（如 socks5 或 http）
                address = proxy.split("@")[-1] if "@" in proxy else proxy.split("://")[1]  # 提取 IP:端口
                masked_proxy = f"{protocol}://[hidden]@{address}"
            else:
                masked_proxy = "None"

            async with AsyncSession(
                    proxies={"http": proxy, "https": proxy} if proxy else None,
                    impersonate="chrome"
            ) as client:
                headers = {
                    "authorization": self.account.token,
                    "referer": f"https://discord.com/channels/{guild_id}/{channel_id}",
                    "x-discord-locale": "en-US",
                    "x-discord-timezone": "Etc/GMT-2",
                }

                params = {
                    "limit": str(quantity),
                }

                logger.info(f"{self.account.index} | Fetching messages using proxy: {masked_proxy}")
                response = await client.get(
                    f"https://discord.com/api/v9/channels/{channel_id}/messages",
                    params=params,
                    headers=headers,
                )

                if response.status_code != 200:
                    logger.error(
                        f"{self.account.index} | Error in _get_last_chat_messages: {response.status_code} - {response.text}"
                    )
                    return []

                received_messages = []
                for message in response.json():
                    try:
                        if (
                                "you just advanced to level" in message["content"]
                                or message["content"] == ""
                        ):
                            continue

                        message_data = ReceivedMessage(
                            type=message["type"],
                            content=message["content"],
                            message_id=message["id"],
                            channel_id=message["channel_id"],
                            author_id=message["author"]["id"],
                            author_username=message["author"]["username"],
                            referenced_message_content=(
                                ""
                                if message.get("referenced_message") in ["None", None]
                                else message.get("referenced_message", {}).get("content", "")
                            ),
                            referenced_message_author_id=(
                                ""
                                if message.get("referenced_message") in ["None", None]
                                else message.get("referenced_message", {}).get("author", {}).get("id", "")
                            ),
                        )
                        received_messages.append(message_data)
                    except Exception as e:
                        continue

                return received_messages

        except Exception as e:
            logger.error(f"{self.account.index} | Error in _get_last_chat_messages: {e}")
            return []

    async def _gpt_referenced_messages(
            self, main_message_content: str, referenced_message_content: str
    ) -> str:
        """使用GPT生成对引用消息的回复"""
        try:
            user_message = f"""Previous message: "{referenced_message_content}"
                Reply to it: "{main_message_content}"
                Generate a natural response continuing this conversation.
            """

            ok, gpt_response = ask_chatgpt(
                random.choice(self.config.CHAT_GPT.API_KEYS),
                self.config.CHAT_GPT.MODEL,
                user_message,
                GPT_REFERENCED_MESSAGES_SYSTEM_PROMPT,
                proxy=self.config.CHAT_GPT.PROXY_FOR_CHAT_GPT,
            )

            if not ok:
                raise Exception(gpt_response)

            return gpt_response
        except Exception as e:
            logger.error(
                f"{self.account.index} | Error in chatter _gpt_referenced_messages: {e}"
            )
            raise e

    async def _deepseek_referenced_messages(
            self, main_message_content: str, referenced_message_content: str
    ) -> str:
        """使用DeepSeek生成对引用消息的回复，如果失败则使用ChatGPT"""
        try:
            api_key = random.choice(self.config.DEEPSEEK.API_KEYS)
            user_message = f"消息1: {referenced_message_content}\n消息2: {main_message_content}"

            success, response = await ask_deepseek(
                api_key=api_key,
                model=self.config.DEEPSEEK.MODEL,
                user_message=user_message,
                prompt=DEEPSEEK_REFERENCED_MESSAGES_SYSTEM_PROMPT,
                proxy=self.config.DEEPSEEK.PROXY_FOR_DEEPSEEK,
            )

            if not success:
                logger.warning(f"{self.account.index} | DeepSeek API失败，切换到ChatGPT: {response}")
                return ""
                # return await self._gpt_referenced_messages(main_message_content, referenced_message_content)

            return response
        except Exception as e:
            logger.warning(f"{self.account.index} | DeepSeek错误，切换到ChatGPT: {str(e)}")
            return ""
            # return await self._gpt_referenced_messages(main_message_content, referenced_message_content)

    async def _gpt_batch_messages(self, messages_contents: list[str]) -> str:
        """使用GPT基于聊天历史生成新消息"""
        try:
            user_message = f"""
                Chat history: {messages_contents}
            """

            ok, gpt_response = ask_chatgpt(
                random.choice(self.config.CHAT_GPT.API_KEYS),
                self.config.CHAT_GPT.MODEL,
                user_message,
                GPT_BATCH_MESSAGES_SYSTEM_PROMPT,
                proxy=self.config.CHAT_GPT.PROXY_FOR_CHAT_GPT,
            )

            if not ok:
                raise Exception(gpt_response)

            return gpt_response
        except Exception as e:
            logger.error(
                f"{self.account.index} | Error in chatter _gpt_batch_messages: {e}"
            )
            raise e

    async def _deepseek_batch_messages(self, messages_contents: str) -> str:
        """使用DeepSeek基于聊天历史生成新消息，如果失败则使用ChatGPT"""
        try:
            api_key = random.choice(self.config.DEEPSEEK.API_KEYS)

            success, response = await ask_deepseek(
                api_key=api_key,
                model=self.config.DEEPSEEK.MODEL,
                user_message=messages_contents,
                prompt=DEEPSEEK_BATCH_MESSAGES_SYSTEM_PROMPT,
                proxy=self.config.DEEPSEEK.PROXY_FOR_DEEPSEEK,
            )

            if not success:
                logger.warning(f"{self.account.index} | DeepSeek API失败，切换到ChatGPT: {response}")
                return ""
                # return await self._gpt_batch_messages(messages_contents)

            return response
        except Exception as e:
            logger.warning(f"{self.account.index} | DeepSeek错误，切换到ChatGPT: {str(e)}")
            return ""
            # return await self._gpt_batch_messages(messages_contents)


# 示例使用
if __name__ == "__main__":
    async def main():
        account = Account(
            index=1,
            token='',
            proxy='',
            username='',
            status='',
            password='',
            new_password='',
            new_name='',
            new_username='',
            messages_to_send=[],
            excel_guild_id='',
            excel_channel_id=''
        )
        config = Config()  # 假设 Config 已正确定义
        client = AsyncSession()  # 假设已正确初始化
        chatter = DiscordChatter(account=account, client=client, config=config)
        await chatter.start_chatting()


    asyncio.run(main())
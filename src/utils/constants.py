from dataclasses import dataclass


ACCOUNTS_FILE = "data/accounts.csv"

DISCORD_CAPTCHA_SITEKEY = "a9b5fb07-92ff-493f-86fe-352a2803b3df"


@dataclass
class Account:
    """
    用于存储Discord账号数据的类
    """

    index: int
    token: str
    proxy: str
    username: str
    status: str
    password: str
    new_password: str
    new_name: str
    new_username: str
    messages_to_send: list[str]
    excel_guild_id: str
    excel_channel_id: str

@dataclass
class DataForTasks:
    """
    用于存储任务数据的类
    """

    LEAVE_GUILD_IDS: list[str]
    PROFILE_PICTURES: list[str]
    EMOJIS_INFO: list[dict]
    INVITE_CODE: str | None
    REACTION_CHANNEL_ID: str | None
    REACTION_MESSAGE_ID: str | None
    IF_TOKEN_IN_GUILD_ID: str | None
    BUTTON_PRESSER_BUTTON_DATA: dict | None
    BUTTON_PRESSER_APPLICATION_ID: str | None
    BUTTON_PRESSER_GUILD_ID: str | None
    BUTTON_PRESSER_CHANNEL_ID: str | None
    BUTTON_PRESSER_MESSAGE_ID: str | None


MAIN_MENU_OPTIONS = [
    "AI Chatter",
    "Inviter [Token]",
    "Press Button [Token]",
    "Press Reaction [Token]",
    "Change Name [Token]",
    "Change Username [Token + Password]",
    "Change Password [Token + Password]",
    "Change Profile Picture [Token]",
    "Send message to the channel [Token]",
    "Token Checker [Token]",
    "Leave Guild [Token]",
    "Show all servers account is in [Token]",
    "Check if token in specified Guild [Token]",
    "Exit",
]

import asyncio
import random

from loguru import logger

from src.model import prepare_data
import src.utils
from src.utils.output import show_dev_info, show_logo, show_menu
from src.utils.reader import read_csv_accounts
from src.utils.constants import ACCOUNTS_FILE, Account
import src.model


async def start():
    async def launch_wrapper(account):
        async with semaphore:
            await account_flow(account, config)

    show_logo()
    show_dev_info()
    config = src.utils.get_config()

    task = show_menu(src.utils.constants.MAIN_MENU_OPTIONS)
    if task == "Exit": return

    config.DATA_FOR_TASKS = await prepare_data(config, task)

    config.TASK = task

    # 从CSV文件中读取账户
    all_accounts = read_csv_accounts(ACCOUNTS_FILE)

    # 确定账户范围
    start_index = config.SETTINGS.ACCOUNTS_RANGE[0]
    end_index = config.SETTINGS.ACCOUNTS_RANGE[1]

    # 如果都是0，检查EXACT_ACCOUNTS_TO_USE
    if start_index == 0 and end_index == 0:
        if config.SETTINGS.EXACT_ACCOUNTS_TO_USE:
            # 按具体编号过滤账户
            accounts_to_process = [
                acc
                for acc in all_accounts
                if acc.index in config.SETTINGS.EXACT_ACCOUNTS_TO_USE
            ]
            logger.info(
                f"Using specific accounts: {config.SETTINGS.EXACT_ACCOUNTS_TO_USE}"
            )
        else:
            # 如果列表为空，使用所有账户
            accounts_to_process = all_accounts
    else:
        # 按范围过滤账户
        accounts_to_process = [
            acc for acc in all_accounts if start_index <= acc.index <= end_index
        ]

    if not accounts_to_process:
        logger.error("No accounts found in specified range")
        return

    # 检查代理是否存在
    if not any(account.proxy for account in accounts_to_process):
        logger.error("No proxies found in accounts data")
        return

    threads = config.SETTINGS.THREADS

    # 创建账户列表并随机打乱
    if config.SETTINGS.SHUFFLE_ACCOUNTS:
        shuffled_accounts = list(accounts_to_process)
        random.shuffle(shuffled_accounts)
    else:
        shuffled_accounts = accounts_to_process

    # 创建账户顺序字符串
    account_order = " ".join(str(acc.index) for acc in shuffled_accounts)
    logger.info(
        f"Starting with accounts {min(acc.index for acc in accounts_to_process)} "
        f"to {max(acc.index for acc in accounts_to_process)}..."
    )
    logger.info(f"Accounts order: {account_order}")

    semaphore = asyncio.Semaphore(value=threads)
    tasks = []

    # 为每个账户创建任务
    for account in shuffled_accounts:
        tasks.append(asyncio.create_task(launch_wrapper(account)))

    await asyncio.gather(*tasks)


async def account_flow(account: Account, config: src.utils.config.Config):
    try:
        pause = random.randint(
            config.SETTINGS.RANDOM_INITIALIZATION_PAUSE[0],
            config.SETTINGS.RANDOM_INITIALIZATION_PAUSE[1],
        )
        logger.info(f"[{account.index}] Sleeping for {pause} seconds before start...")
        await asyncio.sleep(pause)

        instance = src.model.Start(account, config)

        await wrapper(instance.initialize, config)

        await wrapper(instance.flow, config)

        pause = random.randint(
            config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACCOUNTS[0],
            config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACCOUNTS[1],
        )
        logger.info(f"Sleeping for {pause} seconds before next account...")
        await asyncio.sleep(pause)

    except Exception as err:
        logger.error(f"{account.index} | Account flow failed: {err}")


async def wrapper(function, config: src.utils.config.Config, *args, **kwargs):
    attempts = config.SETTINGS.ATTEMPTS
    for attempt in range(attempts):
        result = await function(*args, **kwargs)
        if isinstance(result, tuple) and result and isinstance(result[0], bool):
            if result[0]:
                return result
        elif isinstance(result, bool):
            if result:
                return True

        if attempt < attempts - 1:  # Don't sleep after the last attempt
            pause = random.randint(
                config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
            )
            logger.info(
                f"Sleeping for {pause} seconds before next attempt {attempt+1}/{config.SETTINGS.ATTEMPTS}..."
            )
            await asyncio.sleep(pause)

    return result


def task_exists_in_config(task_name: str, tasks_list: list) -> bool:
    """递归检查任务列表中是否存在指定任务，包括嵌套列表"""
    for task in tasks_list:
        if isinstance(task, list):
            if task_exists_in_config(task_name, task):
                return True
        elif task == task_name:
            return True
    return False

# 配置带认证的代理
# 这个参数有时被Discord要求
# 为代理工作禁用SSL

# 按逗号或空格分割并过滤空字符串
# 使用固定的图片文件夹路径

# 清屏
# 创建带有风格化logo的星空
# 创建渐变文本
# 添加缩进输出
# 创建漂亮的表格
# 添加列
# 添加联系方式行
# 带缩进输出表格
# 输出带编号的选项

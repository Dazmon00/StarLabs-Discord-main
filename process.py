import asyncio
import random
from loguru import logger
from src.model import prepare_data, Start
import src.utils
from src.utils.output import show_dev_info, show_logo, show_menu
from src.utils.reader import read_csv_accounts
from src.utils.constants import ACCOUNTS_FILE, Account


async def start():
    show_logo()
    show_dev_info()
    config = src.utils.get_config()

    task = show_menu(src.utils.constants.MAIN_MENU_OPTIONS)
    if task == "Exit":
        return

    config.DATA_FOR_TASKS = await prepare_data(config, task)
    config.TASK = task

    # 从CSV文件中读取账户
    all_accounts = read_csv_accounts(ACCOUNTS_FILE)

    # 确定账户范围
    start_index = config.SETTINGS.ACCOUNTS_RANGE[0]
    end_index = config.SETTINGS.ACCOUNTS_RANGE[1]

    if start_index == 0 and end_index == 0:
        if config.SETTINGS.EXACT_ACCOUNTS_TO_USE:
            accounts_to_process = [
                acc for acc in all_accounts if acc.index in config.SETTINGS.EXACT_ACCOUNTS_TO_USE
            ]
            logger.info(f"Using specific accounts: {config.SETTINGS.EXACT_ACCOUNTS_TO_USE}")
        else:
            accounts_to_process = all_accounts
    else:
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

    # 使用信号量限制并发
    semaphore = asyncio.Semaphore(value=threads)

    # 定义并行运行的 wrapper
    async def launch_wrapper(account):
        async with semaphore:  # 使用信号量限制并发
            await account_flow(account, config)

    # 并行启动所有账户的任务
    tasks = [launch_wrapper(account) for account in shuffled_accounts]
    await asyncio.gather(*tasks)


async def account_flow(account: Account, config: src.utils.config.Config):
    while True:  # 每个账号独立循环
        try:
            # 初始随机睡眠（短暂，避免所有账号同时启动）
            pause = random.randint(
                config.SETTINGS.RANDOM_INITIALIZATION_PAUSE[0],
                config.SETTINGS.RANDOM_INITIALIZATION_PAUSE[1],
            )
            logger.info(f"[{account.index}] Sleeping for <yellow>{pause}</yellow> seconds before start...")
            await asyncio.sleep(pause)

            # 创建实例并执行流程
            instance = Start(account, config)

            await wrapper(instance.initialize, config)
            logger.success(f"[{account.index}] Initialized successfully")

            await wrapper(instance.flow, config)
            logger.success(f"[{account.index}] Flow completed successfully")

            # 每次循环结束后的随机睡眠（30-60分钟）
            loop_pause = random.randint(1800, 3600)  # 30 到 60 分钟
            logger.info(
                f"[{account.index}] Sleeping for <yellow>{loop_pause // 60}</yellow> minutes "
                f"(<yellow>{loop_pause}</yellow> seconds) before next loop..."
            )
            await asyncio.sleep(loop_pause)

        except Exception as err:
            logger.error(f"[{account.index}] | Account flow failed: {err}")
            # 发生异常时短暂睡眠后重试
            error_pause = random.randint(60, 300)  # 1 到 5 分钟
            logger.info(
                f"[{account.index}] Sleeping for <yellow>{error_pause}</yellow> seconds before retrying..."
            )
            await asyncio.sleep(error_pause)


async def wrapper(function, config: src.utils.config.Config, *args, **kwargs):
    attempts = config.SETTINGS.ATTEMPTS
    for attempt in range(attempts):
        try:
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
                    f"[{function.__self__.account.index}] Sleeping for <yellow>{pause}</yellow> seconds "
                    f"before next attempt {attempt+1}/{attempts}..."
                )
                await asyncio.sleep(pause)
        except Exception as e:
            logger.error(f"[{function.__self__.account.index}] Wrapper attempt {attempt+1}/{attempts} failed: {e}")
            if attempt < attempts - 1:
                pause = random.randint(
                    config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.info(
                    f"[{function.__self__.account.index}] Sleeping for <yellow>{pause}</yellow> seconds "
                    f"before next attempt..."
                )
                await asyncio.sleep(pause)
    return False  # 如果所有尝试都失败，返回 False


def task_exists_in_config(task_name: str, tasks_list: list) -> bool:
    """递归检查任务列表中是否存在指定任务，包括嵌套列表"""
    for task in tasks_list:
        if isinstance(task, list):
            if task_exists_in_config(task_name, task):
                return True
        elif task == task_name:
            return True
    return False


# 主程序入口
if __name__ == "__main__":
    asyncio.run(start())
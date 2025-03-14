import asyncio
import random
from typing import List
from loguru import logger
from src.model import prepare_data
import src.utils
from src.utils.output import show_dev_info, show_logo, show_menu
from src.utils.reader import read_csv_accounts
from src.utils.constants import ACCOUNTS_FILE, Account
import src.model


async def start():
    """程序主入口"""
    show_logo()
    show_dev_info()
    config = src.utils.get_config()

    task = show_menu(src.utils.constants.MAIN_MENU_OPTIONS)
    if task == "Exit": return

    config.DATA_FOR_TASKS = await prepare_data(config, task)
    config.TASK = task

    # 获取并过滤账户
    accounts_to_process = await prepare_accounts(config)
    if not accounts_to_process:
        return

    # 检查代理
    if not any(account.proxy for account in accounts_to_process):
        logger.error("No proxies found in accounts data")
        return

    # 启动账户处理循环
    await run_account_loops(accounts_to_process, config)


async def prepare_accounts(config) -> List[Account]:
    """准备需要处理的账户列表"""
    all_accounts = read_csv_accounts(ACCOUNTS_FILE)
    start_index = config.SETTINGS.ACCOUNTS_RANGE[0]
    end_index = config.SETTINGS.ACCOUNTS_RANGE[1]

    if start_index == 0 and end_index == 0:
        if config.SETTINGS.EXACT_ACCOUNTS_TO_USE:
            accounts = [
                acc for acc in all_accounts
                if acc.index in config.SETTINGS.EXACT_ACCOUNTS_TO_USE
            ]
            logger.info(f"Using specific accounts: {config.SETTINGS.EXACT_ACCOUNTS_TO_USE}")
        else:
            accounts = all_accounts
    else:
        accounts = [
            acc for acc in all_accounts
            if start_index <= acc.index <= end_index
        ]

    if not accounts:
        logger.error("No accounts found in specified range")
        return []

    if config.SETTINGS.SHUFFLE_ACCOUNTS:
        random.shuffle(accounts)

    account_order = " ".join(str(acc.index) for acc in accounts)
    logger.info(f"Starting with accounts {min(acc.index for acc in accounts)} "
                f"to {max(acc.index for acc in accounts)}...")
    logger.info(f"Accounts order: {account_order}")

    return accounts


async def run_account_loops(accounts: List[Account], config):
    """为每个账户创建独立的循环任务"""
    semaphore = asyncio.Semaphore(value=config.SETTINGS.THREADS)
    tasks = [
        asyncio.create_task(account_loop(account, config, semaphore))
        for account in accounts
    ]
    await asyncio.gather(*tasks)


async def account_loop(account: Account, config, semaphore: asyncio.Semaphore):
    """单个账户的无限循环处理"""
    while True:
        try:
            async with semaphore:
                await account_flow(account, config)

            # 单次执行完成后休眠20-40分钟
            sleep_minutes = random.uniform(20, 40)
            sleep_seconds = sleep_minutes * 60
            logger.info(f"[{account.index}] Completed execution, sleeping for {sleep_minutes:.2f} minutes")
            await asyncio.sleep(sleep_seconds)

        except Exception as err:
            logger.error(f"[{account.index}] Loop error: {err}")
            # 发生错误时休眠5分钟后重试
            await asyncio.sleep(300)


async def account_flow(account: Account, config):
    """账户处理流程"""
    try:
        # 初始随机延迟
        initial_pause = random.randint(
            config.SETTINGS.RANDOM_INITIALIZATION_PAUSE[0],
            config.SETTINGS.RANDOM_INITIALIZATION_PAUSE[1],
        )
        logger.info(f"[{account.index}] Sleeping for {initial_pause} seconds before start...")
        await asyncio.sleep(initial_pause)

        instance = src.model.Start(account, config)

        # 初始化
        init_result = await wrapper(instance.initialize, config)
        if not init_result:
            logger.error(f"[{account.index}] Initialization failed")
            return

        # 执行主要流程
        flow_result = await wrapper(instance.flow, config)
        if not flow_result:
            logger.warning(f"[{account.index}] Flow execution failed")

    except Exception as err:
        logger.error(f"[{account.index}] Account flow failed: {err}")
        raise


async def wrapper(function, config, *args, **kwargs):
    """带重试机制的函数包装器"""
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

            if attempt < attempts - 1:
                pause = random.randint(
                    config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.info(
                    f"[{attempt + 1}/{attempts}] Sleeping for {pause} seconds before retry..."
                )
                await asyncio.sleep(pause)

        except Exception as err:
            if attempt < attempts - 1:
                pause = random.randint(
                    config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                    config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                )
                logger.warning(f"Attempt {attempt + 1} failed: {err}, retrying after {pause}s")
                await asyncio.sleep(pause)
            else:
                raise

    return False


if __name__ == "__main__":
    asyncio.run(start())
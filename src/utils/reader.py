import base64
import json
import os
import yaml
import threading
import csv
from loguru import logger
from typing import List, Dict
from src.utils.constants import Account

# 创建全局锁用于同步文件访问
file_read_lock = threading.Lock()


def read_txt_file(file_name: str, file_path: str) -> list:
    """
    使用锁机制安全地读取文本文件

    Args:
        file_name: 用于日志记录的文件名
        file_path: 文件的完整路径

    Returns:
        文件中的行列表，如果文件不存在则返回空列表
    """
    with file_read_lock:
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.warning(f"File {file_path} does not exist.")
                return []

            # 读取文件
            with open(file_path, "r", encoding="utf-8") as file:
                items = [line.strip() for line in file if line.strip()]

            if not items:
                logger.warning(f"File {file_path} is empty.")
                return []

            logger.success(f"Successfully loaded {len(items)} items from {file_name}.")
            return items

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return []


def read_csv_accounts(file_path: str) -> List[Account]:
    """
    从CSV文件读取账号数据。
    读取直到遇到第一个空的DISCORD_TOKEN字段。

    CSV文件必须具有以下格式：
    DISCORD_TOKEN,PROXY,USERNAME,STATUS,PASSWORD,NEW_PASSWORD,NEW_NAME,NEW_USERNAME,MESSAGES_TXT_NAME

    Args:
        file_path (str): CSV文件路径

    Returns:
        List[Account]: 账号对象列表
    """
    accounts = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # 跳过标题行
            reader = csv.DictReader(file)
            
            for row_index, row in enumerate(reader, 1):
                # 获取token值（第一列）
                token = row.get('DISCORD_TOKEN', '').strip()
                
                # 如果token为空，停止读取
                if not token:
                    break
                
                # 获取其他值，将None替换为空字符串
                proxy = row.get('PROXY', '').strip()
                username = row.get('USERNAME', '').strip()
                status = row.get('STATUS', '').strip()
                password = row.get('PASSWORD', '').strip()
                new_password = row.get('NEW_PASSWORD', '').strip()
                new_name = row.get('NEW_NAME', '').strip()
                new_username = row.get('NEW_USERNAME', '').strip()
                messages_txt_name = row.get('MESSAGES_TXT_NAME', '').strip()

                messages_to_send = []
                if messages_txt_name.strip():
                    messages_to_send = read_txt_file(
                        messages_txt_name, f"data/messages/{messages_txt_name}.txt"
                    )

                account = Account(
                    index=row_index,
                    token=token.strip(),
                    proxy=proxy.strip(),
                    username=username.strip(),
                    status=status.strip(),
                    password=password.strip(),
                    new_password=new_password.strip(),
                    new_name=new_name.strip(),
                    new_username=new_username.strip(),
                    messages_to_send=messages_to_send,
                )
                accounts.append(account)
        
        logger.success(f"Successfully loaded {len(accounts)} accounts from data/accounts.csv")
        return accounts
        
    except FileNotFoundError:
        logger.error(f"File {file_path} does not exist.")
        return []
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        return []


async def read_pictures(file_path: str) -> List[str]:
    """
    从指定文件夹读取图片并转换为base64编码

    Args:
        file_path: 图片文件夹路径

    Returns:
        base64编码的图片列表
    """
    encoded_images = []

    # 如果文件夹不存在则创建
    os.makedirs(file_path, exist_ok=True)
    logger.info(f"Reading pictures from {file_path}")

    try:
        # 获取文件列表
        files = os.listdir(file_path)

        if not files:
            logger.warning(f"No files found in {file_path}")
            return encoded_images

        # 处理每个文件
        for filename in files:
            if filename.endswith((".png", ".jpg", ".jpeg")):
                # 构建完整文件路径
                image_path = os.path.join(file_path, filename)

                try:
                    with open(image_path, "rb") as image_file:
                        encoded_image = base64.b64encode(image_file.read()).decode(
                            "utf-8"
                        )
                        encoded_images.append(encoded_image)
                except Exception as e:
                    logger.error(f"Error loading image {filename}: {str(e)}")

    except FileNotFoundError:
        logger.error(f"Directory not found: {file_path}")
    except PermissionError:
        logger.error(f"Permission denied when accessing: {file_path}")
    except Exception as e:
        logger.error(f"Error reading pictures from {file_path}: {str(e)}")

    return encoded_images

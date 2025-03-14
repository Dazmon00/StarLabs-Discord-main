#!/bin/bash

# 定义变量
SCRIPT_PATH="$pwd/start.sh"
DISCORD_DIR="$pwd/StarLabs-Discord-main"
REPO_URL="https://github.com/Dazmon00/StarLabs-Discord-main.git"
SCRIPT_URL="https://raw.githubusercontent.com/Dazmon00/StarLabs-Discord-main/main/start.sh"
OS=$(uname)

# 检查操作系统并设置权限要求
check_permissions() {
    if [ "$OS" = "Linux" ]; then
        echo "当前系统是 Linux"
        if [ "$(id -u)" != "0" ]; then
            echo "此脚本在Linux上需要以 root 用户权限运行。"
            echo "请使用 'sudo -i' 命令切换到 root 用户，或以 'sudo' 运行脚本。"
            exit 1
        fi
    elif [ "$OS" = "Darwin" ]; then # macOS 系统，不要求 root 权限
        echo "检测到macOS系统，无需root权限，继续执行..."
    else
        echo "未知操作系统: $OS"
    fi
}

# 一键下载脚本
download_script() {
    echo "正在下载脚本到 $SCRIPT_PATH..."
    curl -o "$SCRIPT_PATH" "$SCRIPT_URL" || {
        echo "下载失败，请检查网络连接或URL ($SCRIPT_URL)。"
        exit 1
    }
    # 移除Windows换行符，兼容Linux和macOS
    sed -i 's/\r$//' "$SCRIPT_PATH" 2>/dev/null || sed -i '' 's/\r$//' "$SCRIPT_PATH"
    chmod +x "$SCRIPT_PATH"
    echo "脚本下载并设置为可执行完成。"
}

# 检查并安装 Python 3.11
install_python() {
    if command -v python3.11 &>/dev/null; then
        echo "Python 3.11 已安装。"
        return 0
    fi

    echo "未安装 Python 3.11，正在安装..."
    if [ -f /etc/debian_version ]; then
        # Ubuntu/Debian
        apt update -y
        apt install -y software-properties-common
        add-apt-repository ppa:deadsnakes/ppa -y
        apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
    elif [ -f /etc/redhat-release ]; then
        # CentOS/RHEL
        yum install -y epel-release
        yum install -y python3.11 python3.11-devel python3.11-pip
    elif [ "$(uname)" == "Darwin" ]; then
        # macOS
        brew install python@3.11
    else
        echo "不支持的操作系统，请手动安装 Python 3.11。"
        exit 1
    fi
    python3.11 -m pip install --upgrade pip
    echo "Python 3.11 和 pip 安装完成。"
}

# 安装 Discord 工具
install_discord_tool() {
    # 检查并安装 Python
    install_python

    # 检查并安装 git
    if ! command -v git &>/dev/null; then
        echo "未安装 git，正在安装..."
        if [ -f /etc/debian_version ]; then
            apt install -y git
        elif [ -f /etc/redhat-release ]; then
            yum install -y git
        elif [ "$(uname)" == "Darwin" ]; then
            brew install git
        fi
    fi

    # 删除现有目录
    if [ -d "$DISCORD_DIR" ]; then
        echo "检测到 $DISCORD_DIR 目录已存在，正在删除..."
        rm -rf "$DISCORD_DIR"
    fi

    # 克隆仓库
    echo "正在从 GitHub 克隆仓库..."
    git clone "$REPO_URL" "$DISCORD_DIR" || {
        echo "克隆失败，请检查网络连接或仓库地址 ($REPO_URL)。"
        exit 1
    }

    cd "$DISCORD_DIR" || {
        echo "无法进入 $DISCORD_DIR 目录。"
        exit 1
    }

    # 创建并激活虚拟环境
    echo "正在创建和激活虚拟环境..."
    python3.11 -m venv venv
    source "$DISCORD_DIR/venv/bin/activate" || {
        echo "无法激活虚拟环境。"
        exit 1
    }

    # 安装依赖
    echo "正在安装所需的 Python 包..."
    [ ! -f requirements.txt ] && {
        echo "未找到 requirements.txt 文件，无法安装依赖。"
        exit 1
    }
    pip install -r requirements.txt || {
        echo "安装 requirements.txt 失败。"
        exit 1
    }
    pip install httpx || {
        echo "安装 httpx 失败。"
        exit 1
    }

    echo "安装完成！请配置相关文件后运行脚本。"
    exit 0
}

# 运行 Discord 工具
run_discord_tool() {
    # 检查目录
    if [ ! -d "$DISCORD_DIR" ]; then
        echo "未找到 $DISCORD_DIR 目录，请先运行安装选项。"
        read -n 1 -s -r -p "按任意键返回主菜单..."
        return
    fi

    cd "$DISCORD_DIR" || {
        echo "无法进入 $DISCORD_DIR 目录。"
        exit 1
    }

    # 检查并创建虚拟环境
    if [ ! -d "venv" ]; then
        echo "未找到虚拟环境，正在创建..."
        python3.11 -m venv venv
        source venv/bin/activate || {
            echo "无法激活虚拟环境。"
            exit 1
        }
        echo "正在安装依赖..."
        pip install -r requirements.txt || {
            echo "安装 requirements.txt 失败。"
            exit 1
        }
        pip install httpx || {
            echo "安装 httpx 失败。"
            exit 1
        }
    else
        echo "正在激活虚拟环境..."
        source venv/bin/activate || {
            echo "无法激活虚拟环境。"
            exit 1
        }
    fi

    echo "正在启动 StarLabs Discord Bot..."
    python3.11 main.py
}

# 主菜单
main_menu() {
    while true; do
        clear
        echo "脚本由@WBTventures社区 @Dazmon编写，免费开源，请勿相信收费"
        echo "如有问题，可联系推特，仅此只有一个号"
        echo "================================================================"
        echo "退出脚本：按 Ctrl + C"
        echo "请选择操作:"
        echo "1. 安装 Discord AI 聊天脚本"
        echo "2. 运行 Discord AI 聊天脚本"
        echo "3. 退出"

        read -p "请输入选择 (1-3): " choice
        case "$choice" in
            1)
                install_discord_tool
                ;;
            2)
                run_discord_tool
                ;;
            3)
                echo "退出脚本..."
                exit 0
                ;;
            *)
                echo "无效选择，请输入 1、2 或 3。"
                read -n 1 -s -r -p "按任意键继续..."
                ;;
        esac
    done
}

# 主逻辑
check_permissions
# download_script  # 如果需要一键下载功能，取消注释此行
main_menu
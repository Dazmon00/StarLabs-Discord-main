#!/bin/bash

# 脚本保存路径
SCRIPT_PATH="$HOME/Dawn.sh"
Discord_DIR="$HOME/StarLabs-Discord-main"

# 检查是否以 root 用户运行脚本
if [ "$(id -u)" != "0" ]; then
    echo "此脚本需要以 root 用户权限运行。"
    echo "请尝试使用 'sudo -i' 命令切换到 root 用户，然后再次运行此脚本。"
    exit 1
fi

# 安装和配置函数
function install_discord_tool() {
    # 检查 Python 3.11 是否已安装
    function check_python_installed() {
        if command -v python3.11 &>/dev/null; then
            echo "Python 3.11 已安装。"
        else
            echo "未安装 Python 3.11，正在安装..."
            install_python
        fi
    }

    # 安装 Python 3.11
    function install_python() {
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
    # 添加 pip 升级命令
    python3.11 -m pip install --upgrade pip  # 升级 pip
    echo "Python 3.11 和 pip 安装完成。"
    }

    # 检查 Python 版本
    check_python_installed

    # 检查 Dawn 目录是否存在，如果存在则删除	
    if [ -d "$Discord_DIR" ];then	
    echo "检测到 Dawn 目录已存在，正在删除..."	
    rm -rf "$Discord_DIR"	
    echo "Dawn 目录已删除。"	
    fi
    
    # 克隆 GitHub 仓库
    echo "正在从 GitHub 克隆仓库..."
    git clone https://github.com/Dazmon00/StarLabs-Discord-main.git StarLabs-Discord-main

    # 检查克隆操作是否成功
    if [ ! -d "$Discord_DIR" ]; then
        echo "克隆失败，请检查网络连接或仓库地址。"
        exit 1
    fi

    # 进入仓库目录
    cd "$Discord_DIR" || { echo "无法进入 Discord 目录"; exit 1; }

    # 创建并激活虚拟环境
    echo "正在创建和激活虚拟环境..."
    python3.11 -m venv venv
    source "$Discord_DIR/venv/bin/activate"

    # 安装依赖
    echo "正在安装所需的 Python 包..."
    if [ ! -f requirements.txt ]; then
        echo "未找到 requirements.txt 文件，无法安装依赖。"
        exit 1
    fi
    pip install -r requirements.txt
    pip install httpx

    echo "退出脚本"
    # 提示用户按任意键返回主菜单
    exit 0
}

# 安装和配置函数
function run_discord_tool() {
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo "Installing requirements..."
        source venv/bin/activate
        pip install -r requirements.txt
    fi

    echo "Activating virtual environment..."
    source venv/bin/activate

    echo "Starting StarLabs Monad Bot..."
    python3 main.py
}


# 主菜单函数
function main_menu() {
    while true; do
        clear
        echo "脚本由@WBTventures社区 @Dazmon编写，免费开源，请勿相信收费"
        echo "如有问题，可联系推特，仅此只有一个号"
        echo "================================================================"
        echo "退出脚本，请按键盘 ctrl + C 退出即可"
        echo "请选择要执行的操作:"
        echo "1. 安装Discord AI聊天脚本"
        echo "2. 运行Discord AI聊天脚本"
        echo "3. 退出"

        read -p "请输入您的选择 (1，2，3): " choice
        case $choice in
            1)
                install_discord_tool  # Discord AI聊天脚本
                ;;
            2)
                run_discord_tool  # Discord AI聊天脚本
                ;;
            3)
                echo "退出脚本..."
                exit 0
                ;;
            *)
                echo "无效的选择，请重试."
                read -n 1 -s -r -p "按任意键继续..."
                ;;
        esac
    done
}

# 进入主菜单
main_menu

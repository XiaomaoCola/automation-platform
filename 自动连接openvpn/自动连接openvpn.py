import subprocess
# macos和windows就不是这个了，就是import os了


subprocess.Popen([
    "xfce4-terminal",
    # 这个是直接打开一个新的终端窗口（在xfce的桌面下）。
    "--hold",
    # 命令运行完后，窗口会立刻关闭，但是加上hold就会一直保持了。
    "--command",
    # xfce4-terminal的参数，意思是：“打开终端后运行指定命令”
    "sudo openvpn --config /home/zrs/Downloads/zpaul081111.ovpn"
])

# 基本上等于在终端里直接写xfce4-terminal --hold --command "sudo openvpn --config /home/zrs/Downloads/zpaul081111.ovpn"

# 这个文件写好之后，用.py结尾，放在kali系统下面，右键这个文件，有选项open with，然后Set Default Application，
# 然后Use a custom command，填个python。这样设置好之后，就可以双击直接用python打开了。
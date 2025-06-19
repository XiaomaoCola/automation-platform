import tkinter as tk
import os

# 登录函数：打开终端窗口并运行 SSH 命令
def connect(ip, user):
    cmd = f'start cmd /k ssh {user}@{ip}'
    # 这边的`start cmd /k`的意思是打开终端，相当于在终端里输入`start cmd /k`，然后终端又打开了一个终端。
    # f'...'，这是Python 的 f-string（格式化字符串），f'...'字符串里可以用 {} 直接放变量。
    os.system(cmd)

# GUI 创建
root = tk.Tk()
root.title("虚拟机一键登录器")
root.geometry("300x200")

# 虚拟机配置
hosts = {
    "Kali": {"ip": "192.168.50.101", "user": "zrs"},
    "VPN-VM": {"ip": "192.168.50.201", "user": "zrs"},
}
# 这是一个 dictionary（字典），Python 里面最常用的数据结构之一。
# 是两个dictionary的嵌套，叫做nested dictionary。
# 冒号左边的元素叫Key，右边的元素叫Value。



# 创建按钮
row = 0
for name, info in hosts.items():
    # .items() 是把key 和 value 拿出的函数。
    # .items() 是要配合 for 一起使用的，那个name 和 info 是随便叫的， 指代dictionary中的key和value。
    # python3.7之后的directionary是ordered，也就是有顺序的。
    # .items() 应该是和for一起使用， 然后根据dictionary中的顺序，一次一次循环那种感觉。

    btn = tk.Button(root, text=name, width=30, height=3,
                    command=lambda ip=info["ip"], user=info["user"]: connect(ip, user))
    btn.grid(row=row, column=0, padx=20, pady=15)

    # padx=20, pady=15 是在说这个按钮和旁边元素/边框之间的距离。
    row += 1



root.mainloop()
# 这是 tkinter 的规定写法，它的意思是：打开图形界面窗口，并保持一直显示，直到你手动关闭。
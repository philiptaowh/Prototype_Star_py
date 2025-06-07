import math

# 初始化数组，初始值为0，长度为20
a = [0] * 15

while True:
    try:
        # 获取用户输入
        num = int(input("请输入一个介于-50到50的整数："))
        if not (-100 <= num <= 100):
            print("输入超出范围，请重新输入。")
            continue
        
        # 更新数组：移除最旧的元素，添加新元素到末尾
        a.pop(0)
        a.append(num)
        
        # 计算总和
        total = 0.0
        total += a[14]
        for x in range(14):
            total += a[x] * math.exp((x - 15) / 2)
        
        print(f"当前数组的加权和为：{total}")
        print(a)
        
    except ValueError:
        print("输入无效，请输入一个整数。")
    except KeyboardInterrupt:
        print("\n程序已终止。")
        break
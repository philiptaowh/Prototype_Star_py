import time
import random
import numpy as np

# 心理功总值
n = 100
# 心理功变化量
dn = 0

# 收获
k = 0
# 输入收获
def input_k():
    global k
    while 1:
        k = float(input())

# 激励&失望函数
def v1(k):
    if k > 0.1:
        return 10*(1-np.exp(-2*k+0.1))-1
    elif k < -0.1:
        return -10*(1-np.exp(2*k-0.1))-1
    else:
        return -1

# 触摸随机情况函数
flag_v2 = 0
def v2():
    global flag_v2
    if flag_v2 == 0:
        if random.randint(0, 99) >= 89:
            flag_v2 = 20
        return 0
    else:
        flag_v2 -= 1
        return 20/(21 - flag_v2)

# 运动随机情况函数
flag_v3 = 0
def v3():
    global flag_v3
    if flag_v3 == 0:
        if random.randint(0, 99) >= 59:
            flag_v2 = 10
        return 0
    else:
        flag_v2 -= 1
        return 10

# 遗忘函数
def v4(dn):
    if dn > 0:
        return np.log2(dn)
    elif dn < 0:
        return -np.log2(-dn)
    else:
        return 0
    
# 幸福函数
flag_v5 = 0
def v5(k,flag_v3):
    global flag_v5
    if k > -0.1 and k < 0.1 and flag_v3 != 0:
        if flag_v5 == 0:
            if random.randint(0, 99) >= 39:
                flag_v5 = 20
            return 0
        else:
            flag_v5 -= 1
            return 11
    else:
        flag_v5 = 0
        return 0


while 1:
    d1 = v1(k)
    d2 = v2()
    d3 = - v3()
    d4 = v4(dn)
    d5 = v5(k,flag_v3)
    dn = v1(k) + v2() - v3() + v4(dn) + v5(k,flag_v3)
    n = 100 + dn
    print(n)
    time.sleep(0.5)

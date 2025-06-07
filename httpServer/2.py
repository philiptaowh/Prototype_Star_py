
import re

def extract_number(s):
    match = re.search(r'-?\d+', s)
    return int(match.group()) if match else None

while 1:
    test = input("输入一个示例")
    print(extract_number(test))
    print(type(extract_number(test)))
    print("\n")
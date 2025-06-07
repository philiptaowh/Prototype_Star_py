import os
import json
import requests

LLM_API_URL_conversation = "https://qianfan.baidubce.com/v2/app/conversation"
LLM_API_URL_run = "https://qianfan.baidubce.com/v2/app/conversation/runs"
LLM_API_URL_file = "https://qianfan.baidubce.com/v2/app/conversation/file/upload"
Conversation_ID = ""
test_File = "image1.jpg"

# 大模型创建对话
def create_llm():
    global Conversation_ID
    try:
        # 新建对话
        payload = json.dumps({
              "app_id": "851e5985-9f1d-4eef-88eb-7a9f429da3e2",
        }, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer bce-v3/ALTAK-BSx79U9x4vqNeDAMFIYq9/4bb4fb9a66f47f666e0c8fe8b742935ca26e2dd0'
        }
          
        response = requests.request("POST", LLM_API_URL_conversation, headers=headers, data=payload.encode("utf-8"))
        
        # 提取对话ID
        Conversation_ID = response.text.split("\"")[7]

        return response
    except Exception as e:
        print(f"[LLM ERROR] API调用失败: {str(e)}")
        return None
    
# 大模型上传文件
def update_llm(fileName):
    global Conversation_ID
    try:
        # 新建对话
        payload = {
              "app_id": "851e5985-9f1d-4eef-88eb-7a9f429da3e2",
              "conversation_id": Conversation_ID
        }

        headers = {
            'Authorization': 'Bearer bce-v3/ALTAK-BSx79U9x4vqNeDAMFIYq9/4bb4fb9a66f47f666e0c8fe8b742935ca26e2dd0'
        }
        files = [
            ('file',("image.jpg",open(fileName,'rb'),'image/jpeg'))# 字段名, (服务器接收到的文件名,文件数据,文件种类)
        ]
        response = requests.request("POST", LLM_API_URL_file, headers=headers, data=payload, files=files)

        # 提取图片ID
        image_ID = response.text.split("\"")[7]

        return image_ID
    except Exception as e:
        print(f"[LLM ERROR] API调用失败: {str(e)}")
        return None

# 大模型进行对话（带图片）
def query_llm(question, pic_ID):
    global Conversation_ID
    try:         
        # 发起对话
        
        payload = json.dumps({
        "app_id": "851e5985-9f1d-4eef-88eb-7a9f429da3e2",
        "query": question,
        "conversation_id": Conversation_ID,
        "stream": False,
        "file_ids": [
            pic_ID
        ]
        }, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer bce-v3/ALTAK-BSx79U9x4vqNeDAMFIYq9/4bb4fb9a66f47f666e0c8fe8b742935ca26e2dd0'
        }
        
        raw_response = requests.request("POST", LLM_API_URL_run, headers=headers, data=payload.encode("utf-8"))
        response = json.loads(raw_response.text)
        print(response["answer"])

        return response
    except Exception as e:
        print(f"[LLM ERROR] API调用失败: {str(e)}")
        return None

create_llm()
print(Conversation_ID)
img_ID = update_llm(test_File)
query_llm("分析应该如何行动",img_ID)
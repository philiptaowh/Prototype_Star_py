import os
import json
import requests

LLM_API_URL_conversation = "https://qianfan.baidubce.com/v2/app/conversation"
LLM_API_URL_run = "https://qianfan.baidubce.com/v2/app/conversation/runs"
Conversation_ID = ""

# 大模型创建对话
def create_llm():
    global Conversation_ID
    try:
        # 新建对话
        payload = json.dumps({
              "app_id": "96f41255-639c-4b93-8342-4dc8aeae3f84",
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
    
# 大模型进行对话
def query_llm(question):
    global Conversation_ID
    try:         
        # 发起对话
        payload = json.dumps({
            "app_id": "96f41255-639c-4b93-8342-4dc8aeae3f84",
            "query": question,
            "conversation_id": Conversation_ID,
            "stream": False
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
query_llm("当前温度：20")

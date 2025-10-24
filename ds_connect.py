# 化学笺集自动化滴定项目的一部分，用于连接大模型
# 作者：李峙德
# 邮箱：contact@chemview.net
# 最后更新：2025-10-24
import requests
import json

config_file='config.json'
with open(config_file, 'r') as f:
    config = json.load(f)

req_url=config['req_url']
api_key=config['api_key']

def llm_get_color(substance_name):
    llm_req_url = req_url
    llm_payload = {
        "model": "Pro/deepseek-ai/DeepSeek-V3",
        "messages": [
            {
                "role": "user",
                "content": f"我正在进行滴定实验，实验所用的体系是{substance_name}（格式是“滴定液 被滴定液 指示剂”），溶液浓度并不高，较稀，返回到达终点时溶液颜色的十六进制颜色，也就是指示剂变色后的颜色，示例‘#C77400’，!!确保正确!!，不要返回其它内容，如果你认为这不是一个化学实验应该有的体系，返回#333333"
            }
        ]
    }
    llm_req_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    llm_response=requests.request("POST", llm_req_url, json=llm_payload, headers=llm_req_headers)
    llm_response_content=json.loads(llm_response.text)["choices"][0]["message"]["content"]
    return llm_response_content
from core import AgentManager
import os
import logging

log = logging.getLogger('easyAgent')
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.DEBUG) 

base_url = "http://127.0.0.1:9999/v1"
api_key = "None"
model_name = "openai/gpt-oss-20b"
# model_name = "qwen/qwen3-4b"
agent_path = os.path.join(os.path.dirname(__file__), "plugin")
start_agent_name = "entrance_agent"
end_agent_name = "general_agent"

if __name__ == "__main__":
    agent_manager  = AgentManager(
                        plugin_src=agent_path, 
                        base_url=base_url, 
                        api_key=api_key, 
                        model_name=model_name,
                        start_agent_name=start_agent_name,
                        end_agent_name=end_agent_name
                    )
    response = agent_manager("abc写了一本书，帮我查询一下这本书的出版信息")
    # response = agent_manager("圆周率精确到3位小数是多少？")
    # response = agent_manager("先帮我查一下呼啸山庄的作者是谁，然后再帮我查一下id为2的书籍的出版信息")
    print(response)

    # print(agent_manager.agent_loader.to_json())

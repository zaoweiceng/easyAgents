#!/usr/bin/env python3
"""
easyAgent Web/SSE流式响应示例

演示如何在Web应用中使用SSE (Server-Sent Events) 提供流式响应

依赖安装:
    pip install flask

使用方法:
    python examples/streaming_sse.py

然后访问:
    - 同步接口: http://localhost:5000/chat/sync
    - 流式接口: http://localhost:5000/chat/stream

测试:
    curl -X POST http://localhost:5000/chat/sync \
         -H "Content-Type: application/json" \
         -d '{"query": "查询图书信息"}'

    curl -X POST http://localhost:5000/chat/stream \
         -H "Content-Type: application/json" \
         -d '{"query": "查询图书信息"}'
"""

import sys
import os
from flask import Flask, Response, request, jsonify

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import AgentManager
from config import get_config
import json

app = Flask(__name__)

# 全局AgentManager实例
agent_manager = None


def init_agent_manager():
    """初始化AgentManager"""
    global agent_manager
    if agent_manager is None:
        config = get_config()
        agent_manager = AgentManager(
            plugin_src=config.get_agent_config()['plugin_src'],
            base_url=config.get_llm_config()['base_url'],
            api_key=config.get_llm_config()['api_key'],
            model_name=config.get_llm_config()['model_name']
        )


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "easyAgent-streaming"})


@app.route('/chat/sync', methods=['POST'])
def chat_sync():
    """
    同步响应接口（向后兼容）

    请求格式:
        {
            "query": "用户查询内容"
        }

    响应格式:
        {
            "status": "success",
            "response": [...]
        }
    """
    try:
        init_agent_manager()

        data = request.get_json()
        query = data.get('query', '')

        if not query:
            return jsonify({"error": "缺少query参数"}), 400

        # 同步调用
        response = agent_manager(query, stream=False)

        return jsonify({
            "status": "success",
            "response": response
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/chat/stream', methods=['POST'])
def chat_stream():
    """
    流式响应接口（SSE）

    请求格式:
        {
            "query": "用户查询内容"
        }

    响应格式 (Server-Sent Events):
        data: {"type": "metadata", "data": {...}, "metadata": {...}}

        data: {"type": "agent_start", "data": {"agent_name": "...", ...}}

        data: {"type": "delta", "data": {"content": "文", ...}}

        data: {"type": "delta", "data": {"content": "本", ...}}

        data: {"type": "delta", "data": {"content": "片段", ...}}

        data: {"type": "agent_end", "data": {...}}

        data: [DONE]
    """
    try:
        init_agent_manager()

        data = request.get_json()
        query = data.get('query', '')

        if not query:
            return jsonify({"error": "缺少query参数"}), 400

        def generate():
            """生成SSE事件流"""
            try:
                for event in agent_manager(query, stream=True):
                    # 转换为SSE格式
                    sse_data = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    yield sse_data

                # 发送完成标记
                yield "data: [DONE]\n\n"

            except Exception as e:
                # 发送错误事件
                error_event = {
                    "type": "error",
                    "data": {"error_message": str(e)},
                    "metadata": {}
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/', methods=['GET'])
def index():
    """首页 - 提供简单的测试界面"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>easyAgent 流式响应示例</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            .container {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
            }
            textarea {
                width: 100%;
                height: 80px;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-bottom: 10px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin-right: 10px;
            }
            button:hover {
                background-color: #45a049;
            }
            #output {
                margin-top: 20px;
                padding: 15px;
                background-color: #f5f5f5;
                border-radius: 4px;
                min-height: 200px;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .agent-start {
                color: #2196F3;
                font-weight: bold;
            }
            .agent-end {
                color: #4CAF50;
                font-weight: bold;
            }
            .delta {
                color: #333;
            }
            .error {
                color: #f44336;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 easyAgent 流式响应示例</h1>

            <textarea id="query" placeholder="输入您的查询，例如：查询图书信息">abc写了一本书，帮我查询一下这本书的出版信息</textarea>

            <button onclick="sendSync()">同步发送</button>
            <button onclick="sendStream()">流式发送</button>
            <button onclick="clearOutput()">清空输出</button>

            <div id="output"></div>
        </div>

        <script>
            function clearOutput() {
                document.getElementById('output').innerText = '';
            }

            function appendToOutput(text, className = '') {
                const output = document.getElementById('output');
                const span = document.createElement('span');
                span.className = className;
                span.textContent = text;
                output.appendChild(span);
                output.scrollTop = output.scrollHeight;
            }

            async function sendSync() {
                const query = document.getElementById('query').value;
                if (!query) {
                    alert('请输入查询内容');
                    return;
                }

                clearOutput();
                appendToOutput('正在发送同步请求...\\n\\n', 'info');

                try {
                    const response = await fetch('/chat/sync', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query})
                    });

                    const result = await response.json();
                    appendToOutput(JSON.stringify(result, null, 2), 'delta');
                } catch (error) {
                    appendToOutput('错误: ' + error.message, 'error');
                }
            }

            async function sendStream() {
                const query = document.getElementById('query').value;
                if (!query) {
                    alert('请输入查询内容');
                    return;
                }

                clearOutput();
                appendToOutput('正在发送流式请求...\\n\\n', 'info');

                try {
                    const response = await fetch('/chat/stream', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query})
                    });

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const {done, value} = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\\n');

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const data = line.slice(6);

                                if (data === '[DONE]') {
                                    appendToOutput('\\n\\n✓ 完成\\n', 'agent-end');
                                    break;
                                }

                                try {
                                    const event = JSON.parse(data);
                                    handleEvent(event);
                                } catch (e) {
                                    // 忽略解析错误
                                }
                            }
                        }
                    }
                } catch (error) {
                    appendToOutput('\\n错误: ' + error.message, 'error');
                }
            }

            function handleEvent(event) {
                const type = event.type;
                const data = event.data;

                switch (type) {
                    case 'delta':
                        const content = data.content;
                        if (content) {
                            appendToOutput(content, 'delta');
                        }
                        break;

                    case 'agent_start':
                        appendToOutput('\\n▶ ' + data.agent_name + ' 开始处理...\\n', 'agent-start');
                        break;

                    case 'agent_end':
                        appendToOutput('\\n✓ ' + data.agent_name + ' 完成\\n', 'agent-end');
                        break;

                    case 'error':
                        appendToOutput('\\n✗ 错误: ' + data.error_message + '\\n', 'error');
                        break;

                    case 'metadata':
                        // 可以显示元数据信息
                        break;
                }
            }
        </script>
    </body>
    </html>
    """
    return html


if __name__ == '__main__':
    print("=" * 70)
    print("easyAgent Web/SSE 流式响应服务器")
    print("=" * 70)
    print("\n启动服务器...")
    print("\n访问地址:")
    print("  - 首页: http://localhost:5000/")
    print("  - 同步API: http://localhost:5000/chat/sync")
    print("  - 流式API: http://localhost:5000/chat/stream")
    print("\n按 Ctrl+C 停止服务器\n")
    print("=" * 70)

    app.run(port=5000, debug=True)

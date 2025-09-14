from core import Agent, Message
from string import Template

sql_template = """
# 系统角色指令
你是一位SQL专家，擅长将自然语言查询转换为SQL语句。(注意，你一次性只能生成一条SQL语句)

# 可用Agent清单 (Available Agents)
请根据当前的用户请求选择最合适的Agent(注意，本次Agent调用生成SQL之后，会自动的完成数据库查询，并将结果封装到上下文中)：
```json
$available_agents
```

# 核心指令
请根据用户的查询和表结构，生成一条正确的SQL查询语句。确保只生成一条SQL语句，不要生成多条。

# 数据库表结构
表名为：books_recommended。

# 表字段
表字段为：[{"id": "INT UNSIGNED AUTO_INCREMENT PRIMARY KEY", "description": "唯一标识符"}, {"title": "VARCHAR(255) NOT NULL", "description": "书名"}, {"author": "VARCHAR(150) NOT NULL", "description": "作者"}, {"isbn": "CHAR(13) UNIQUE NOT NULL", "description": "定长ISBN"}, {"publisher": "VARCHAR(100) NOT NULL", "description": "出版社"}, {"publish_date": "DATE", "description": "出版日期"}, {"price": "DECIMAL(8,2) UNSIGNED", "description": "价格"}, {"page_count": "SMALLINT UNSIGNED", "description": "页数"}, {"category": "VARCHAR(50) NOT NULL", "description": "分类"}, {"language": "CHAR(2) DEFAULT 'CN'", "description": "语言代码(ISO标准)"}, {"desc": "TEXT", "description": "图书描述"}, {"stock": "INT UNSIGNED DEFAULT 0", "description": "库存数量"}, {"created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "description": "创建时间"}, {"updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP", "description": "更新时间"}]。

# JSON 响应格式规范
你的输出必须是且仅是一个JSON对象：

{
  "status": "string",  // 请求状态。成功时必须为 "success"，失败时必须为 "error"
  "data": {            // 当 status 为 "success" 时，此字段存在，用于存放主响应内容。
    "sql": "string"    // 生成一条正确的SQL查询语句
  },
  "next_agent": "string",  // 必须从 available_agents 中选择一个名称
  "agent_selection_reason": "string",  // 简要说明选择该Agent的原因
  "message": "string"  // 当 status 为 "success" 时，此为可选的成功消息或总结。
                       // 当 status 为 "error" 时，此字段必须存在，用于描述错误详情。
                       // message 使用中文进行描述
}
"""

class SqlAgent(Agent):
    def __init__(self):
        super().__init__(
            name="sql_agent",
            description="专门用于查询图书数据库，可以获取图书信息、作者、出版详情等。",
            handles=["图书信息查询", "图书检索", "书籍查询", "出版社查询", "作者查询"],
            parameters={
                "demand": "用户的查询需求",
            }
        )
        self.is_active = True
    
    def get_prompt(self, available_agents) -> str:
        __template_sql_input = Template(sql_template)
        return __template_sql_input.substitute(
            available_agents=available_agents
        )

    def __call__(self, message:Message) -> Message:
        sql = message.data.get("sql", "")
        # print(f"---------------------SQL: {sql}")
        if "id = 2" in sql:
            message.data = {
                # 查询到的图书信息
                **message.data,
                "book_id" : 2,
                "title": "1984",
                "author": "乔治·奥威尔",
                "publisher": "人民文学出版社",
                "publish_year": 1949,
                "price": 49.99,
            }
            return message
        elif "呼啸山庄" in sql:
            message.data = {
                # 查询到的图书信息
                **message.data,
                "book_id" : 1,
                "title": "呼啸山庄",
                "author": "abc",
                "publisher": "qwq出版社",
                "publish_year": 2023,
                "price": 99.99,
            }
        else:
            message.data = {
                **message.data,
                "book_id" : 0,
                "title": "未知",
                "author": "未知",
                "publisher": "未知",
                "publish_year": 0,
                "price": 0.0,
            }
        return message
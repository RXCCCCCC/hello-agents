from dotenv import load_dotenv
# 加载 .env 文件中的环境变量
load_dotenv()

import os
from serpapi import SerpApiClient
from typing import Dict, Any


def _build_search_params(query: str, api_key: str) -> list[dict[str, str]]:
    """
    Build search parameter candidates.

    We avoid hard-coding locale parameters because some combinations such as
    gl=cn/hl=zh-cn can cause SerpApi to return no results for otherwise valid
    queries. Locale can still be provided through environment variables.
    """
    base_params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
    }

    localized_params = dict(base_params)
    gl = os.getenv("SERPAPI_GL")
    hl = os.getenv("SERPAPI_HL")
    if gl:
        localized_params["gl"] = gl
    if hl:
        localized_params["hl"] = hl

    candidates = [base_params]
    if localized_params != base_params:
        candidates.insert(0, localized_params)
    return candidates


def _extract_search_summary(results: Dict[str, Any]) -> str | None:
    answer_box_list = results.get("answer_box_list") or []
    if isinstance(answer_box_list, list):
        direct_answers = []
        for item in answer_box_list:
            if isinstance(item, dict):
                for key in ("answer", "snippet", "title"):
                    value = item.get(key)
                    if value:
                        direct_answers.append(str(value))
                        break
            elif item:
                direct_answers.append(str(item))
        if direct_answers:
            return "\n".join(direct_answers)

    answer_box = results.get("answer_box") or {}
    for key in ("answer", "snippet", "title"):
        value = answer_box.get(key)
        if isinstance(value, list) and value:
            return "\n".join(str(item) for item in value)
        if value:
            return str(value)

    knowledge_graph = results.get("knowledge_graph") or {}
    if knowledge_graph.get("description"):
        return str(knowledge_graph["description"])

    organic_results = results.get("organic_results") or []
    if organic_results:
        snippets = []
        for i, res in enumerate(organic_results[:3]):
            lines = []
            title = res.get("title")
            snippet = res.get("snippet")
            link = res.get("link")
            if title:
                lines.append(f"[{i+1}] {title}")
            if snippet:
                lines.append(str(snippet))
            if link:
                lines.append(str(link))
            if lines:
                snippets.append("\n".join(lines))
        if snippets:
            return "\n\n".join(snippets)

    return None

def search(query: str) -> str:
    """
    一个基于SerpApi的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回直接答案或知识图谱信息。
    """
    print(f"🔍 正在执行 [SerpApi] 网页搜索: {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误：SERPAPI_API_KEY 未在 .env 文件中配置。"

        last_error = None
        for params in _build_search_params(query, api_key):
            client = SerpApiClient(params)
            results = client.get_dict()

            if results.get("error"):
                last_error = results["error"]
                continue

            summary = _extract_search_summary(results)
            if summary:
                return summary

        if last_error:
            return f"搜索服务返回错误：{last_error}"

        return f"对不起，没有找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"

class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告：工具 '{name}' 已存在，将被覆盖。")
        
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> callable:
        """
        根据名称获取一个工具的执行函数。
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])


# --- 工具初始化与使用示例 ---
if __name__ == '__main__':
    # 1. 初始化工具执行器
    toolExecutor = ToolExecutor()

    # 2. 注册我们的实战搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)
    
    # 3. 打印可用的工具
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 4. 智能体的Action调用，这次我们问一个实时性的问题
    print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    tool_name = "Search"
    tool_input = "英伟达最新的GPU型号是什么"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误：未找到名为 '{tool_name}' 的工具。")

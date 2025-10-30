"""
大模型服务集成模块
"""
import json
from typing import AsyncGenerator, Dict, List, Any, Optional
import httpx
from openai import AsyncOpenAI
from config import settings
import asyncio


class LLMService:
    """大模型服务"""
    
    def __init__(self):
        self.clients: Dict[str, AsyncOpenAI] = {}
        self._init_clients()
    
    def _init_clients(self):
        """初始化各个大模型客户端"""
        
        # 创建自定义httpx客户端，禁用缓冲以支持真正的流式传输
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
        
        # DeepSeek
        if settings.DEEPSEEK_API_KEY:
            self.clients["deepseek"] = AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_API_BASE,
                http_client=http_client,
                max_retries=2
            )
        
        # Qwen (通义千问)
        if settings.QWEN_API_KEY:
            self.clients["qwen"] = AsyncOpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_API_BASE,
                http_client=http_client,
                max_retries=2
            )
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """获取可用的模型列表"""
        models = {}
        
        if "deepseek" in self.clients:
            models["deepseek"] = [
                "deepseek-chat",
                "deepseek-reasoner"
            ]
        
        if "qwen" in self.clients:
            models["qwen"] = [
                "qwen-max",
                "qwen3-max",
                "qwen-plus",
                "qwen-vl-plus"
            ]
        
        return models
    
    async def chat_completion(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ):
        """
        调用大模型进行对话
        
        Args:
            provider: 模型提供商 (deepseek, qwen)
            model: 模型名称
            messages: 对话消息列表
            tools: 可用的工具列表
            stream: 是否流式输出
            **kwargs: 其他参数
        
        Returns:
            如果 stream=True，返回 AsyncGenerator[str, None]
            如果 stream=False，返回 Dict[str, Any]
        """
        client = self.clients.get(provider)
        if not client:
            raise ValueError(f"未配置的模型提供商: {provider}")
        
        # 构建请求参数
        params = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        # 如果有工具，添加到参数中
        if tools and len(tools) > 0:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        
        if stream:
            # 返回流式生成器
            return self._stream_completion(client, params)
        else:
            # 返回非流式结果
            return await self._non_stream_completion(client, params)
    
    async def _stream_completion(
        self,
        client: AsyncOpenAI,
        params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        try:
            stream = await client.chat.completions.create(**params)
            
            # 用于收集工具调用（因为流式响应中工具调用可能分多个chunk）
            tool_calls_buffer = {}
            finish_reason = None
            
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    
                    # 文本内容
                    if delta.content:
                        yield json.dumps({
                            "type": "content",
                            "content": delta.content
                        }) + "\n"
                        # 强制yield，确保立即传输
                        await asyncio.sleep(0)
                    
                    # 工具调用（需要累积完整的参数）
                    if delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            index = tool_call.index
                            if index not in tool_calls_buffer:
                                tool_calls_buffer[index] = {
                                    "id": tool_call.id or "",
                                    "type": "function",
                                    "function": {
                                        "name": tool_call.function.name or "",
                                        "arguments": ""
                                    }
                                }
                            
                            # 累积函数名和参数
                            if tool_call.function.name:
                                tool_calls_buffer[index]["function"]["name"] = tool_call.function.name
                            if tool_call.function.arguments:
                                tool_calls_buffer[index]["function"]["arguments"] += tool_call.function.arguments
                    
                    # 结束
                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
            
            # 如果有工具调用，返回完整的工具调用信息
            if tool_calls_buffer:
                tool_calls = list(tool_calls_buffer.values())
                yield json.dumps({
                    "type": "tool_calls",
                    "tool_calls": tool_calls,
                    "finish_reason": finish_reason
                }) + "\n"
            else:
                # 没有工具调用，正常结束
                yield json.dumps({
                    "type": "done",
                    "finish_reason": finish_reason
                }) + "\n"
                        
        except Exception as e:
            yield json.dumps({
                "type": "error",
                "error": str(e)
            }) + "\n"
    
    async def _non_stream_completion(
        self,
        client: AsyncOpenAI,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """非流式对话"""
        try:
            response = await client.chat.completions.create(**params)
            choice = response.choices[0]
            
            result = {
                "message": {
                    "role": choice.message.role,
                    "content": choice.message.content
                },
                "finish_reason": choice.finish_reason
            }
            
            # 如果有工具调用
            if choice.message.tool_calls:
                result["message"]["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in choice.message.tool_calls
                ]
            
            return result
            
        except Exception as e:
            return {
                "error": str(e)
            }


# 全局LLM服务实例
llm_service = LLMService()


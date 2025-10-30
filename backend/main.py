"""
FastAPI主程序
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from config import settings
from mcp_client import mcp_client, MCPServer
from llm_service import llm_service


# ============= 应用生命周期 =============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    print("🚀 Kylin MCP Client API 启动中...")
    print(f"📡 服务地址: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API文档: http://{settings.HOST}:{settings.PORT}/docs")
    
    # 加载已保存的MCP服务器配置
    print("📂 加载MCP服务器配置...")
    await mcp_client.load_config()
    
    yield
    
    # Shutdown
    print("👋 Kylin MCP Client API 关闭中...")
    await mcp_client.close()


# 创建FastAPI应用
app = FastAPI(
    title="Kylin MCP Client API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= 数据模型 =============

class MCPServerCreate(BaseModel):
    name: str
    type: str  # "local" 或 "remote"
    config: Dict[str, Any]


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    provider: str  # deepseek, qwen
    model: str
    messages: List[Dict[str, Any]]
    stream: bool = True
    use_mcp_tools: bool = True


class ToolCallRequest(BaseModel):
    server_id: str
    tool_name: str
    arguments: Dict[str, Any]


# ============= API路由 =============

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Kylin MCP Client API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


# ----------- MCP服务器管理 -----------

@app.get("/mcp/servers")
async def get_servers():
    """获取所有MCP服务器"""
    return {"servers": mcp_client.get_servers()}


@app.post("/mcp/servers")
async def add_server(server_data: MCPServerCreate):
    """添加MCP服务器"""
    server = MCPServer(
        id=str(uuid.uuid4()),
        name=server_data.name,
        type=server_data.type,
        config=server_data.config,
        enabled=True
    )
    
    success, error = await mcp_client.add_server(server)
    if success:
        return {"success": True, "server": server.__dict__}
    else:
        raise HTTPException(status_code=400, detail=error or "添加服务器失败")


@app.patch("/mcp/servers/{server_id}")
async def update_server(server_id: str, server_data: MCPServerUpdate):
    """更新MCP服务器配置"""
    success, error = await mcp_client.update_server(
        server_id=server_id,
        name=server_data.name,
        config=server_data.config
    )
    if success:
        return {"success": True, "message": "服务器配置已更新"}
    else:
        raise HTTPException(status_code=400, detail=error or "更新服务器配置失败")


@app.post("/mcp/servers/{server_id}/enable")
async def enable_server(server_id: str):
    """启用MCP服务器"""
    success, error = await mcp_client.enable_server(server_id)
    if success:
        return {"success": True, "message": "服务器已启用"}
    else:
        raise HTTPException(status_code=400, detail=error or "启用服务器失败")


@app.post("/mcp/servers/{server_id}/disable")
async def disable_server(server_id: str):
    """禁用（停止）MCP服务器"""
    success, error = await mcp_client.disable_server(server_id)
    if success:
        return {"success": True, "message": "服务器已禁用"}
    else:
        raise HTTPException(status_code=400, detail=error or "禁用服务器失败")


@app.post("/mcp/servers/{server_id}/restart")
async def restart_server(server_id: str):
    """重启MCP服务器"""
    success, error = await mcp_client.restart_server(server_id)
    if success:
        return {"success": True, "message": "服务器已重启"}
    else:
        raise HTTPException(status_code=400, detail=error or "重启服务器失败")


@app.delete("/mcp/servers/{server_id}")
async def delete_server(server_id: str):
    """删除MCP服务器"""
    success = await mcp_client.remove_server(server_id)
    if success:
        return {"success": True}
    else:
        raise HTTPException(status_code=404, detail="服务器不存在")


@app.get("/mcp/tools")
async def get_tools():
    """获取所有可用的MCP工具"""
    return {"tools": mcp_client.get_all_tools()}


@app.post("/mcp/tools/call")
async def call_tool(request: ToolCallRequest):
    """调用MCP工具"""
    result = await mcp_client.call_tool(
        request.server_id,
        request.tool_name,
        request.arguments
    )
    return result


# ----------- 大模型管理 -----------

@app.get("/llm/models")
async def get_models():
    """获取可用的大模型列表"""
    return {"models": llm_service.get_available_models()}


@app.post("/llm/chat")
async def chat(request: ChatRequest):
    """非流式对话"""
    # 获取MCP工具
    tools = None
    if request.use_mcp_tools:
        tools = mcp_client.get_all_tools()
    
    # 调用大模型
    result = await llm_service.chat_completion(
        provider=request.provider,
        model=request.model,
        messages=request.messages,
        tools=tools,
        stream=False
    )
    
    return result


# ----------- WebSocket聊天 -----------

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket流式聊天"""
    await websocket.accept()
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            provider = request_data.get("provider")
            model = request_data.get("model")
            messages = request_data.get("messages", [])
            use_mcp_tools = request_data.get("use_mcp_tools", True)
            
            # 获取MCP工具
            tools = None
            if use_mcp_tools:
                tools = mcp_client.get_all_tools()
            
            # 工具调用循环（最多10轮，防止无限循环）
            max_iterations = 10
            current_messages = messages.copy()
            
            for iteration in range(max_iterations):
                # 流式调用大模型
                stream_generator = await llm_service.chat_completion(
                    provider=provider,
                    model=model,
                    messages=current_messages,
                    tools=tools,
                    stream=True
                )
                
                # 收集助手消息内容和工具调用
                assistant_content = ""
                assistant_tool_calls = []
                
                async for chunk in stream_generator:
                    chunk_data = json.loads(chunk)
                    
                    if chunk_data["type"] == "content":
                        assistant_content += chunk_data["content"]
                        # 将内容流式发送给前端
                        await websocket.send_text(chunk)
                        # 确保立即发送，不缓冲
                        await asyncio.sleep(0)
                    
                    elif chunk_data["type"] == "tool_calls":
                        # 收到完整的工具调用请求
                        assistant_tool_calls = chunk_data["tool_calls"]
                        
                        # 通知前端有工具调用
                        for tool_call in assistant_tool_calls:
                            await websocket.send_text(json.dumps({
                                "type": "tool_call",
                                "tool_call": tool_call
                            }))
                    
                    elif chunk_data["type"] == "error":
                        # 错误直接传递给前端
                        await websocket.send_text(chunk)
                        raise Exception(chunk_data["error"])
                
                # 如果没有工具调用，结束循环
                if not assistant_tool_calls:
                    await websocket.send_text(json.dumps({"type": "done"}))
                    break
                
                # 添加助手消息（包含工具调用）到历史
                current_messages.append({
                    "role": "assistant",
                    "content": assistant_content or None,
                    "tool_calls": assistant_tool_calls
                })
                
                # 执行工具调用
                for tool_call in assistant_tool_calls:
                    function_name = tool_call["function"]["name"]
                    
                    # 解析 server_id 和 tool_name (格式: server_id_tool_name)
                    # 首先尝试从所有工具中查找匹配的工具来获取正确的 server_id 和 tool_name
                    all_tools = mcp_client.get_all_tools()
                    tool_info = None
                    for tool in all_tools:
                        if tool["function"]["name"] == function_name:
                            tool_info = tool
                            break
                    
                    if tool_info:
                        # 使用工具定义中保存的 server_id 和 tool_name
                        server_id = tool_info["server_id"]
                        tool_name = tool_info["tool_name"]
                    else:
                        # 如果找不到工具定义，尝试按照命名规则解析
                        # 遍历所有已知的 server_id，找到最长匹配的前缀
                        server_ids = list(mcp_client.servers.keys())
                        matched_server_id = None
                        for sid in server_ids:
                            if function_name.startswith(f"{sid}_"):
                                # 选择最长匹配的 server_id（避免歧义）
                                if matched_server_id is None or len(sid) > len(matched_server_id):
                                    matched_server_id = sid
                        
                        if matched_server_id:
                            server_id = matched_server_id
                            tool_name = function_name[len(matched_server_id) + 1:]  # +1 跳过下划线
                        else:
                            error_msg = f"无法解析工具名称: {function_name}。请确保格式为 'server_id_tool_name'"
                            print(error_msg)
                            print(f"可用的服务器ID: {server_ids}")
                            current_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": json.dumps({"error": error_msg})
                            })
                            continue
                    
                    # 解析参数
                    try:
                        arguments = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError as e:
                        error_msg = f"工具参数解析失败: {str(e)}"
                        print(error_msg)
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps({"error": error_msg})
                        })
                        continue
                    
                    # 调用工具
                    print(f"执行工具调用: {server_id}/{tool_name}")
                    tool_result = await mcp_client.call_tool(
                        server_id=server_id,
                        tool_name=tool_name,
                        arguments=arguments
                    )
                    
                    # 通知前端工具执行结果
                    await websocket.send_text(json.dumps({
                        "type": "tool_result",
                        "tool_call_id": tool_call["id"],
                        "tool_name": function_name,
                        "result": tool_result
                    }))
                    
                    # 添加工具结果到消息历史
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(tool_result)
                    })
                
                # 继续下一轮对话（让AI处理工具结果）
            
            # 如果达到最大迭代次数
            if iteration >= max_iterations - 1:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "达到最大工具调用次数限制"
                }))
                
    except WebSocketDisconnect:
        print("WebSocket连接断开")
    except Exception as e:
        print(f"WebSocket错误: {e}")
        import traceback
        traceback.print_exc()
        await websocket.send_text(json.dumps({
            "type": "error",
            "error": str(e)
        }))


# ----------- 配置管理 -----------

@app.get("/config")
async def get_config():
    """获取配置信息"""
    return {
        "has_deepseek": settings.DEEPSEEK_API_KEY is not None,
        "has_qwen": settings.QWEN_API_KEY is not None,
    }


@app.post("/config/api-key")
async def update_api_key(data: Dict[str, str]):
    """更新API密钥"""
    provider = data.get("provider")
    api_key = data.get("api_key")
    
    if provider == "deepseek":
        settings.DEEPSEEK_API_KEY = api_key
    elif provider == "qwen":
        settings.QWEN_API_KEY = api_key
    else:
        raise HTTPException(status_code=400, detail="未知的提供商")
    
    # 重新初始化LLM服务
    llm_service._init_clients()
    
    return {"success": True}


# ============= 主函数 =============

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
        ws_ping_interval=None,  # 禁用WebSocket ping，避免干扰流式传输
        ws_ping_timeout=None,
        timeout_keep_alive=300  # 延长连接保持时间
    )


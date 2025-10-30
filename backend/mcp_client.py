"""
MCP客户端管理模块
"""
import asyncio
import json
import os
import sys
import traceback
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import httpx
from datetime import datetime


@dataclass
class MCPServer:
    """MCP服务器配置"""
    id: str
    name: str
    type: str  # "local" 或 "remote"
    config: Dict[str, Any]
    enabled: bool = True
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_id: str


class LocalMCPConnection:
    """本地MCP服务器连接（通过stdio）"""
    
    def __init__(self, server_id: str, config: Dict[str, Any]):
        self.server_id = server_id
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.read_task: Optional[asyncio.Task] = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    async def start(self) -> Tuple[bool, str]:
        """启动本地MCP服务器进程，返回(成功标志, 错误信息)"""
        try:
            command = self.config.get("command", [])
            env = self.config.get("env", {})
            cwd = self.config.get("cwd", None)
            
            if not command:
                error = "配置错误: 缺少启动命令(command)"
                print(f"[{self.server_id}] {error}")
                return False, error
            
            # 使用标准 subprocess.Popen 创建子进程（兼容所有平台和事件循环）
            # 确保继承当前进程的环境变量
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # Windows 特殊处理：如果命令是 npx，尝试使用完整路径
            if sys.platform == 'win32' and command[0] == 'npx':
                # 尝试常见的 npx 路径
                npx_paths = [
                    r'C:\Program Files\nodejs\npx.cmd',
                    r'C:\Program Files (x86)\nodejs\npx.cmd',
                    os.path.join(os.environ.get('APPDATA', ''), 'npm', 'npx.cmd'),
                ]
                for npx_path in npx_paths:
                    if os.path.exists(npx_path):
                        command[0] = npx_path
                        print(f"[{self.server_id}] 使用 npx 路径: {npx_path}")
                        break
            
            # 在线程池中创建进程，避免事件循环限制
            loop = asyncio.get_event_loop()
            self.process = await loop.run_in_executor(
                self.executor,
                lambda: subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=process_env,
                    cwd=cwd,
                    bufsize=0,  # 无缓冲
                    shell=False  # 不使用 shell
                )
            )
            
            # 启动读取任务
            self.read_task = asyncio.create_task(self._read_loop())
            
            # 发送初始化请求（带超时）
            try:
                init_result = await asyncio.wait_for(
                    self.send_request("initialize", {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "clientInfo": {
                            "name": "kylin-mcp-client",
                            "version": "1.0.0"
                        }
                    }),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                # 获取stderr输出帮助诊断
                stderr_output = ""
                if self.process and self.process.stderr:
                    try:
                        stderr_data = await loop.run_in_executor(
                            self.executor,
                            lambda: self.process.stderr.read(1024)
                        )
                        stderr_output = stderr_data.decode('utf-8', errors='ignore')
                    except:
                        pass
                
                error = f"初始化超时: 服务器未响应"
                if stderr_output:
                    error += f"\n进程错误输出: {stderr_output}"
                print(f"[{self.server_id}] {error}")
                await self.stop()
                return False, error
            
            if "error" in init_result:
                error = f"MCP初始化失败: {init_result['error']}"
                print(f"[{self.server_id}] {error}")
                await self.stop()
                return False, error
            
            # 发送 initialized 通知
            await self.send_notification("notifications/initialized", {})
            
            print(f"[{self.server_id}] 本地MCP服务器启动成功")
            return True, ""
            
        except FileNotFoundError as e:
            error = f"命令未找到: {command[0] if command else 'unknown'}"
            print(f"[{self.server_id}] 启动失败: {error}")
            await self.stop()
            return False, error
        except Exception as e:
            error_detail = str(e) if str(e) else repr(e)
            error = f"启动异常: {error_detail}"
            print(f"[{self.server_id}] 启动失败: {error}")
            print(f"[{self.server_id}] 堆栈跟踪:\n{traceback.format_exc()}")
            await self.stop()
            return False, error
    
    async def stop(self):
        """停止本地MCP服务器进程"""
        if self.read_task:
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass
        
        if self.process:
            loop = asyncio.get_event_loop()
            try:
                self.process.terminate()
                # 在线程池中等待进程结束
                await asyncio.wait_for(
                    loop.run_in_executor(self.executor, self.process.wait),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.process.kill()
                await loop.run_in_executor(self.executor, self.process.wait)
            except Exception as e:
                print(f"[{self.server_id}] 停止进程失败: {e}")
        
        # 关闭线程池
        if self.executor:
            self.executor.shutdown(wait=False)
    
    async def _read_loop(self):
        """读取服务器输出"""
        try:
            loop = asyncio.get_event_loop()
            while self.process and self.process.stdout:
                # 在线程池中读取一行
                line = await loop.run_in_executor(
                    self.executor,
                    self.process.stdout.readline
                )
                if not line:
                    break
                
                try:
                    message = json.loads(line.decode().strip())
                    await self._handle_message(message)
                except json.JSONDecodeError as e:
                    print(f"[{self.server_id}] JSON解析错误: {e}, 内容: {line}")
                except Exception as e:
                    print(f"[{self.server_id}] 处理消息失败: {e}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[{self.server_id}] 读取循环错误: {e}")
    
    async def _handle_message(self, message: Dict[str, Any]):
        """处理服务器消息"""
        if "id" in message:
            # 响应消息
            request_id = message["id"]
            if request_id in self.pending_requests:
                future = self.pending_requests.pop(request_id)
                if "error" in message:
                    future.set_result({"error": message["error"]})
                else:
                    future.set_result(message.get("result", {}))
        else:
            # 通知消息（可以记录日志或处理事件）
            method = message.get("method", "")
            if method:
                print(f"[{self.server_id}] 收到通知: {method}")
    
    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送JSON-RPC请求"""
        if not self.process or not self.process.stdin:
            return {"error": "进程未启动"}
        
        self.request_id += 1
        request_id = self.request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        # 创建Future等待响应
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            # 发送请求（在线程池中执行写操作）
            request_str = json.dumps(request) + "\n"
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self.process.stdin.write(request_str.encode()) or self.process.stdin.flush()
            )
            
            # 等待响应（30秒超时）
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            return {"error": "请求超时"}
        except Exception as e:
            self.pending_requests.pop(request_id, None)
            return {"error": f"请求失败: {str(e)}"}
    
    async def send_notification(self, method: str, params: Dict[str, Any]):
        """发送JSON-RPC通知（不需要响应）"""
        if not self.process or not self.process.stdin:
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        try:
            notification_str = json.dumps(notification) + "\n"
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self.process.stdin.write(notification_str.encode()) or self.process.stdin.flush()
            )
        except Exception as e:
            print(f"[{self.server_id}] 发送通知失败: {e}")


class MCPClient:
    """MCP客户端"""
    
    def __init__(self, data_dir: str = "./data/mcp_servers"):
        self.servers: Dict[str, MCPServer] = {}
        self.tools: Dict[str, List[MCPTool]] = {}  # server_id -> tools
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.local_connections: Dict[str, LocalMCPConnection] = {}  # server_id -> connection
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "servers.json")
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
    
    def _save_config(self):
        """保存服务器配置到文件"""
        try:
            # 将服务器配置转换为可序列化的格式
            config_data = {
                "servers": [asdict(server) for server in self.servers.values()]
            }
            
            # 写入配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 服务器配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ 保存服务器配置失败: {e}")
            return False
    
    async def load_config(self):
        """从文件加载服务器配置"""
        if not os.path.exists(self.config_file):
            print(f"⚠️  配置文件不存在: {self.config_file}")
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            servers_data = config_data.get("servers", [])
            print(f"📂 从配置文件加载 {len(servers_data)} 个服务器...")
            
            # 加载每个服务器
            loaded_count = 0
            failed_servers = []
            
            for server_data in servers_data:
                try:
                    server = MCPServer(
                        id=server_data["id"],
                        name=server_data["name"],
                        type=server_data["type"],
                        config=server_data["config"],
                        enabled=server_data.get("enabled", True),
                        created_at=server_data.get("created_at", "")
                    )
                    
                    # 添加服务器（不保存配置，避免重复保存）
                    success, error = await self.add_server(server, save_config=False)
                    if success:
                        loaded_count += 1
                        print(f"  ✅ 已加载: {server.name} ({server.type})")
                    else:
                        failed_servers.append((server.name, error))
                        print(f"  ❌ 加载失败: {server.name} - {error}")
                        
                except Exception as e:
                    server_name = server_data.get("name", "未知")
                    failed_servers.append((server_name, str(e)))
                    print(f"  ❌ 加载服务器配置失败: {server_name} - {e}")
            
            print(f"✅ 成功加载 {loaded_count}/{len(servers_data)} 个服务器")
            if failed_servers:
                print(f"⚠️  失败的服务器:")
                for name, error in failed_servers:
                    print(f"    - {name}: {error}")
            
        except json.JSONDecodeError as e:
            print(f"❌ 配置文件格式错误: {e}")
        except Exception as e:
            print(f"❌ 加载服务器配置失败: {e}")
    
    async def add_server(self, server: MCPServer, save_config: bool = True) -> Tuple[bool, str]:
        """添加MCP服务器，返回(成功标志, 错误信息)"""
        try:
            self.servers[server.id] = server
            
            # 启动服务器连接并获取工具列表
            if server.enabled:
                if server.type == "local":
                    # 创建并启动本地连接
                    connection = LocalMCPConnection(server.id, server.config)
                    success, error = await connection.start()
                    if success:
                        self.local_connections[server.id] = connection
                        await self._fetch_tools(server.id)
                        # 保存配置
                        if save_config:
                            self._save_config()
                        return True, ""
                    else:
                        # 清理已添加的服务器
                        del self.servers[server.id]
                        return False, error
                else:
                    # 远程服务器直接获取工具
                    await self._fetch_tools(server.id)
            
            # 保存配置
            if save_config:
                self._save_config()
            return True, ""
        except Exception as e:
            # 清理可能已添加的服务器
            self.servers.pop(server.id, None)
            error_msg = f"添加服务器失败: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    async def update_server(self, server_id: str, name: Optional[str] = None, 
                          config: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        更新MCP服务器配置
        参数:
            server_id: 服务器ID
            name: 新的服务器名称（可选）
            config: 新的配置信息（可选）
        返回:
            (成功标志, 错误信息)
        """
        if server_id not in self.servers:
            return False, f"服务器不存在: {server_id}"
        
        server = self.servers[server_id]
        old_enabled = server.enabled
        
        try:
            # 更新配置
            if name is not None:
                server.name = name
            if config is not None:
                server.config = config
            
            # 如果服务器已启用，需要重启以应用新配置
            if server.enabled and server.type == "local":
                print(f"[{server_id}] 重启服务器以应用新配置...")
                
                # 停止旧连接
                if server_id in self.local_connections:
                    await self.local_connections[server_id].stop()
                    del self.local_connections[server_id]
                
                # 启动新连接
                connection = LocalMCPConnection(server_id, server.config)
                success, error = await connection.start()
                if success:
                    self.local_connections[server_id] = connection
                    await self._fetch_tools(server_id)
                else:
                    # 如果重启失败，恢复旧状态
                    server.enabled = False
                    self._save_config()
                    return False, f"重启服务器失败: {error}"
            
            # 保存配置
            self._save_config()
            print(f"✅ 服务器 '{server.name}' 配置已更新")
            return True, ""
            
        except Exception as e:
            error_msg = f"更新服务器配置失败: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    async def enable_server(self, server_id: str) -> Tuple[bool, str]:
        """
        启用MCP服务器
        返回: (成功标志, 错误信息)
        """
        if server_id not in self.servers:
            return False, f"服务器不存在: {server_id}"
        
        server = self.servers[server_id]
        
        if server.enabled:
            return True, "服务器已经是启用状态"
        
        try:
            server.enabled = True
            
            # 启动服务器连接
            if server.type == "local":
                connection = LocalMCPConnection(server_id, server.config)
                success, error = await connection.start()
                if success:
                    self.local_connections[server_id] = connection
                    await self._fetch_tools(server_id)
                else:
                    server.enabled = False
                    self._save_config()
                    return False, f"启动服务器失败: {error}"
            else:
                # 远程服务器直接获取工具
                await self._fetch_tools(server_id)
            
            # 保存配置
            self._save_config()
            print(f"✅ 服务器 '{server.name}' 已启用")
            return True, ""
            
        except Exception as e:
            server.enabled = False
            error_msg = f"启用服务器失败: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    async def disable_server(self, server_id: str) -> Tuple[bool, str]:
        """
        禁用（停止）MCP服务器
        返回: (成功标志, 错误信息)
        """
        if server_id not in self.servers:
            return False, f"服务器不存在: {server_id}"
        
        server = self.servers[server_id]
        
        if not server.enabled:
            return True, "服务器已经是禁用状态"
        
        try:
            # 停止本地连接
            if server.type == "local" and server_id in self.local_connections:
                await self.local_connections[server_id].stop()
                del self.local_connections[server_id]
            
            # 清除工具列表
            if server_id in self.tools:
                self.tools[server_id] = []
            
            server.enabled = False
            
            # 保存配置
            self._save_config()
            print(f"✅ 服务器 '{server.name}' 已禁用")
            return True, ""
            
        except Exception as e:
            error_msg = f"禁用服务器失败: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    async def restart_server(self, server_id: str) -> Tuple[bool, str]:
        """
        重启MCP服务器
        返回: (成功标志, 错误信息)
        """
        if server_id not in self.servers:
            return False, f"服务器不存在: {server_id}"
        
        server = self.servers[server_id]
        
        if not server.enabled:
            return False, "服务器未启用，无法重启"
        
        try:
            print(f"[{server_id}] 正在重启服务器...")
            
            # 停止服务器
            success, error = await self.disable_server(server_id)
            if not success:
                return False, f"停止服务器失败: {error}"
            
            # 重新启用服务器
            success, error = await self.enable_server(server_id)
            if not success:
                return False, f"启动服务器失败: {error}"
            
            print(f"✅ 服务器 '{server.name}' 已重启")
            return True, ""
            
        except Exception as e:
            error_msg = f"重启服务器失败: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    async def remove_server(self, server_id: str) -> bool:
        """移除MCP服务器"""
        if server_id in self.servers:
            # 停止本地连接
            if server_id in self.local_connections:
                await self.local_connections[server_id].stop()
                del self.local_connections[server_id]
            
            del self.servers[server_id]
            if server_id in self.tools:
                del self.tools[server_id]
            
            # 保存配置
            self._save_config()
            return True
        return False
    
    async def _fetch_tools(self, server_id: str):
        """从MCP服务器获取工具列表"""
        server = self.servers.get(server_id)
        if not server:
            return
        
        try:
            if server.type == "remote":
                # 远程服务器通过HTTP获取工具
                url = server.config.get("url", "")
                response = await self.http_client.post(
                    f"{url}/tools/list",
                    json={}
                )
                if response.status_code == 200:
                    data = response.json()
                    tools = []
                    for tool_data in data.get("tools", []):
                        tool = MCPTool(
                            name=tool_data["name"],
                            description=tool_data["description"],
                            input_schema=tool_data["inputSchema"],
                            server_id=server_id
                        )
                        tools.append(tool)
                    self.tools[server_id] = tools
                    print(f"[{server_id}] 获取到 {len(tools)} 个远程工具")
            else:
                # 本地服务器通过stdio获取工具
                connection = self.local_connections.get(server_id)
                if not connection:
                    print(f"[{server_id}] 本地连接不存在")
                    self.tools[server_id] = []
                    return
                
                result = await connection.send_request("tools/list", {})
                
                if "error" in result:
                    print(f"[{server_id}] 获取工具列表失败: {result['error']}")
                    self.tools[server_id] = []
                else:
                    tools = []
                    for tool_data in result.get("tools", []):
                        tool = MCPTool(
                            name=tool_data["name"],
                            description=tool_data["description"],
                            input_schema=tool_data.get("inputSchema", {}),
                            server_id=server_id
                        )
                        tools.append(tool)
                    self.tools[server_id] = tools
                    print(f"[{server_id}] 获取到 {len(tools)} 个本地工具")
                
        except Exception as e:
            print(f"获取工具列表失败 [{server_id}]: {e}")
            self.tools[server_id] = []
    
    async def call_tool(
        self, 
        server_id: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用MCP工具"""
        server = self.servers.get(server_id)
        if not server:
            available_servers = list(self.servers.keys())
            return {
                "error": f"服务器不存在: {server_id}",
                "available_servers": available_servers,
                "hint": f"请确保已添加并启动服务器。可用的服务器: {', '.join(available_servers) if available_servers else '无'}"
            }
        
        if not server.enabled:
            return {"error": f"服务器已禁用: {server_id}"}
        
        try:
            if server.type == "remote":
                # 远程服务器通过HTTP调用
                url = server.config.get("url", "")
                response = await self.http_client.post(
                    f"{url}/tools/call",
                    json={
                        "name": tool_name,
                        "arguments": arguments
                    }
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"调用失败: {response.status_code}"}
            else:
                # 本地服务器通过stdio调用
                connection = self.local_connections.get(server_id)
                if not connection:
                    return {"error": "本地连接不存在"}
                
                result = await connection.send_request("tools/call", {
                    "name": tool_name,
                    "arguments": arguments
                })
                
                return result
                
        except Exception as e:
            return {"error": f"调用工具失败: {str(e)}"}
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        all_tools = []
        for server_id, tools in self.tools.items():
            server = self.servers.get(server_id)
            if server and server.enabled:
                for tool in tools:
                    all_tools.append({
                        "type": "function",
                        "function": {
                            "name": f"{server_id}_{tool.name}",
                            "description": tool.description,
                            "parameters": tool.input_schema
                        },
                        "server_id": server_id,
                        "tool_name": tool.name
                    })
        return all_tools
    
    def get_servers(self) -> List[Dict[str, Any]]:
        """获取所有服务器信息"""
        result = []
        for server in self.servers.values():
            server_dict = asdict(server)
            # 添加连接状态
            if server.type == "local":
                server_dict["connected"] = server.id in self.local_connections
            else:
                server_dict["connected"] = True  # 远程服务器假设总是可连接
            # 添加工具数量
            server_dict["tool_count"] = len(self.tools.get(server.id, []))
            result.append(server_dict)
        return result
    
    async def close(self):
        """关闭客户端"""
        # 停止所有本地连接
        for connection in self.local_connections.values():
            await connection.stop()
        self.local_connections.clear()
        
        # 关闭HTTP客户端
        await self.http_client.aclose()


# 全局MCP客户端实例
mcp_client = MCPClient()


# -*- coding: utf-8 -*-
import socket
import threading
import json
from simple_pid import PID

HOST = "0.0.0.0"  # 服务端监听所有网络接口
PORT = 21793      # 服务端端口号
Terminator = "\n"  # 结束符

class PIDServer:
    def __init__(self):
        self.server_socket = None
        self.clients = {}  # 存储客户端连接和对应的PID控制器
        
    def start(self):
        """启动PID服务端"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            print(f"PID Server started, listening on {HOST}:{PORT}")
            
            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"New connection from {addr}")
                    # 为每个客户端创建独立的线程处理
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    # 保存客户端连接和PID控制器
                    self.clients[addr] = {
                        'socket': client_socket,
                        'thread': client_thread,
                        'pid': None
                    }
                except Exception as e:
                    print(f"Error accepting connection: {e}")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, addr):
        """处理客户端连接"""
        try:
            while True:
                # 接收客户端消息（最多 1024 字节）
                data = client_socket.recv(1024)
                if not data:
                    break  # 客户端断开连接
                
                stat, output = self.handle_client_message(addr, data)
                
                # 返回数据给客户端
                message = json.dumps({"stat": stat, "data": {"output": output}}) + Terminator
                client_socket.send(message.encode('utf-8'))
                
                if output == "end":  # 结束仿真
                    break
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            if addr in self.clients:
                del self.clients[addr]
            print(f"Client {addr} disconnected")
    
    def handle_client_message(self, addr, data):
        """处理客户端消息"""
        # 默认返回
        stat = True
        output = 0
        
        # 解析消息
        try:
            message = data.decode('utf-8')
            print(f"\nFrom {addr} get msg: {message}")
            message_dict = json.loads(message)
        except json.JSONDecodeError:
            print(f"Failed to decode JSON message from {addr}. msg:{message}")
            stat = False
            return stat, output
        except Exception as e:
            print(f"msg handle error from {addr}: {e}")
            stat = False
            return stat, output
        
        # 处理消息
        try:
            action = message_dict.get("action")
            data = message_dict.get("data")
            
            if action == "init":
                # 初始化PID控制器
                pid_params = data.get("pid_params")
                setpoint = data.get("setpoint")
                current = data.get("current")
                
                # 创建PID控制器并保存
                pid_controller = PID(pid_params["kp"], pid_params["ki"], pid_params["kd"], setpoint=setpoint)
                pid_controller.output_limits = tuple(pid_params["output_limits"])  # 设置输出范围
                self.clients[addr]['pid'] = pid_controller
                
                print(f"Initialized PID controller for {addr} with params: {pid_params}, setpoint: {setpoint}")
                
                # 计算PID控制器的输出（水泵电压V）
                output = pid_controller(current)
                print(f"PID output for {addr}: {output:.2f}")
                
            elif action == "get":
                # 获取pid输出
                setpoint = data.get("setpoint")
                current = data.get("current")
                print(f"Get current value from {addr}: setpoint: {setpoint}, current: {current}")
                
                if addr in self.clients and self.clients[addr]['pid'] is not None:
                    pid_controller = self.clients[addr]['pid']
                    output = pid_controller(current)
                    print(f"PID output for {addr}: {output:.2f}")
                else:
                    stat = False
                    print(f"No PID controller initialized for {addr}")
                    
            elif action == "end":
                # 结束仿真
                setpoint = data.get("setpoint")
                current = data.get("current")
                
                print(f"Simulation ended for {addr}. setpoint: {setpoint}, current: {current}")
                output = "end"
        except Exception as e:
            print(f"msg handle error for {addr}: {e}")
            stat = False
        
        return stat, output
    
    def stop(self):
        """停止服务端"""
        # 关闭所有客户端连接
        for addr, client_info in list(self.clients.items()):
            try:
                client_info['socket'].close()
            except:
                pass
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("PID Server stopped")

if __name__ == "__main__":
    server = PIDServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("Keyboard interrupt received. Server stopped.")
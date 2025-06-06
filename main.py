# -*- coding: utf-8 -*-
import socket
import threading
import json
import logging
from datetime import datetime
import os
from simple_pid import PID

HOST = "0.0.0.0"  # 服务端监听所有网络接口
PORT = 21793      # 服务端端口号
Terminator = "\n"  # 结束符

class PIDServer:
    def __init__(self):
        self.server_socket = None
        self.clients = {}  # 存储客户端连接和对应的PID控制器
        self._setup_logging()  # 初始化基础日志
        
    def _setup_logging(self, log_file=None):
        """配置基础日志系统"""
        if not os.path.exists('log'):
            os.makedirs('log')
        
        handlers = [logging.StreamHandler()]  # 控制台输出
        
        if log_file:
            # 如果有指定日志文件，则使用指定的日志文件
            handlers.append(logging.FileHandler(log_file))
        else:
            # 默认日志文件
            handlers.append(logging.FileHandler('pid_server.log'))
            
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        self.logger = logging.getLogger('PIDServer')
        
    def _setup_client_logging(self, addr):
        """为特定客户端设置专用日志文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"log/pid_client_{addr[0]}_{addr[1]}_{timestamp}.log"
        
        # 移除现有的文件处理器
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
        
        # 添加新的文件处理器
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        
        return log_filename
        
    def _log_client_action(self, addr, action, data=None):
        """记录客户端操作的专用方法"""
        log_msg = f"Client {addr} - Action: {action}"
        if data:
            log_msg += f" - Data: {data}"
        self.logger.info(log_msg)
        
    def start(self):
        """启动PID服务端"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            self.logger.info(f"PID Server started, listening on {HOST}:{PORT}")
            
            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    self.logger.info(f"New connection from {addr}")
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
                    self.logger.error(f"Error accepting connection: {e}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
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
            self.logger.error(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
            if addr in self.clients:
                del self.clients[addr]
            self.logger.info(f"Client {addr} disconnected")
    
    def handle_client_message(self, addr, data):
        """处理客户端消息"""
        # 默认返回
        stat = True
        output = 0
        
        # 解析消息
        try:
            message = data.decode('utf-8')
            self._log_client_action(addr, "received", message)
            message_dict = json.loads(message)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON message from {addr}. msg:{message}")
            stat = False
            return stat, output
        except Exception as e:
            self.logger.error(f"msg handle error from {addr}: {e}")
            stat = False
            return stat, output
        
        # 处理消息
        try:
            action = message_dict.get("action")
            data = message_dict.get("data")
            
            if action == "init":
                # 初始化PID控制器（无条件重置）
                pid_params = data.get("pid_params")
                setpoint = data.get("setpoint", 0)  # 默认0（兼容旧客户端）
                current = data.get("current", 0)
                
                # 创建新的PID控制器
                pid_controller = PID(pid_params["kp"], pid_params["ki"], pid_params["kd"], setpoint=setpoint)
                pid_controller.output_limits = tuple(pid_params["output_limits"])
                self.clients[addr]['pid'] = pid_controller
                
                # 为客户端设置专用日志文件（如果尚未设置）
                if 'log_file' not in self.clients[addr]:
                    log_file = self._setup_client_logging(addr)
                    self.clients[addr]['log_file'] = log_file
                    self.logger.info(f"Created dedicated log file: {log_file}")
                
                self._log_client_action(addr, "init", 
                                    f"params: {pid_params}, setpoint: {setpoint}, current: {current}")
                
                # 计算PID控制器的输出（水泵电压V）
                output = pid_controller(current)
                self.logger.info(f"PID output for {addr}: {output:.2f}")
                
            elif action == "get":
                # 获取pid输出
                setpoint = data.get("setpoint")
                current = data.get("current")
                self._log_client_action(addr, "get", 
                                    f"setpoint: {setpoint}, current: {current}")
                
                if addr in self.clients and self.clients[addr]['pid'] is not None:
                    pid_controller = self.clients[addr]['pid']
                    pid_controller.setpoint = setpoint  # 更新设定值
                    output = pid_controller(current)
                    self.logger.info(f"PID output for {addr}: {output:.2f}")
                else:
                    stat = False
                    self.logger.warning(f"No PID controller initialized for {addr}")
                    
            elif action == "end":
                # 结束仿真
                setpoint = data.get("setpoint")
                current = data.get("current")
                
                self._log_client_action(addr, "end", 
                                    f"setpoint: {setpoint}, current: {current}")
                output = "end"
        except Exception as e:
            self.logger.error(f"msg handle error for {addr}: {e}")
            stat = False
        
        return stat, output

    def stop(self):
        """停止服务端"""
        # 关闭所有客户端连接
        for addr, client_info in list(self.clients.items()):
            try:
                client_info['socket'].close()
            except Exception as e:
                self.logger.error(f"Error closing client socket {addr}: {e}")
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                self.logger.error(f"Error closing server socket: {e}")
        self.logger.info("PID Server stopped")

if __name__ == "__main__":
    server = PIDServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        server.logger.info("Keyboard interrupt received. Server stopped.")

# -*- coding: utf-8 -*-
import socket
import time
import json
from simple_pid import PID

HOST = "10.78.112.154" # 服务端IP地址
PORT = 21793 # 服务端端口号

Terminator = "\n" # 结束符

global PID_client, PID_controller

"""
服务端消息格式
{
    "action": "init",
    "data": {
        "pid_params": {        
            "kp": 1.0,
            "ki": 0.1,
            "kd": 0.05,
            "output_limits": [0, 15]
        },
        "setpoint": 10.0,
        "current": 0.0
    }
}

{
    "action": "get",
    "data": {
        "setpoint": 10.0,
        "current": 5.0
    }
}

{
    "action": "end",
    "data": {
        "setpoint": 10.0,
        "current": 5.0
    }
}
"""

"""
返回数据格式
{
    "stat": True/False,
    "data": {
        "output": 5.0
    }
}
"""

def create_client():
    global PID_client
    #创建一个socket对象
    PID_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def connect_to_server():
    global PID_client
    try:
        # 连接服务器
        PID_client.connect((HOST, PORT))
        print(f"connected to {HOST}:{PORT}")

        while True:
            # 接收服务器消息（最多 1024 字节）
            data = PID_client.recv(1024)
            if not data:
                continue  # 暂时没收到数据，继续等待

            stat, output = handle_server_messages(data)
            if stat: # 处理消息成功，返回数据
                if output == "end": # 结束仿真
                    return True
            else: # 报错
                pass

            # 返回数据
            message = json.dumps({"stat": stat, "data": {"output": output}}) + Terminator
            PID_client.send(message.encode('utf-8'))

    except Exception as e:
        print(f"Error: {e}")
        return False
    
def handle_server_messages(data):
    global PID_controller

    # 默认返回
    stat = True
    output = 0
    
    # 解析消息
    try:
        message = data.decode('utf-8')
        print(f"\nget msg: {message}")
        message_dict = json.loads(message)
    except json.JSONDecodeError:
        print(f"Failed to decode JSON message. msg:{message}")
        stat = False
    except Exception as e:
        print(f"msg handle error: {e}")
        stat = False
    
    # 处理消息
    try:
        action = message_dict.get("action")
        data = message_dict.get("data")
        if action == "init":
            # 初始化PID控制器
            pid_params = data.get("pid_params")
            setpoint = data.get("setpoint")
            current = data.get("current")
            
            # 创建PID控制器
            PID_controller = PID(pid_params["kp"], pid_params["ki"], pid_params["kd"], setpoint=setpoint)
            PID_controller.output_limits = tuple(pid_params["output_limits"])  # 设置输出范围
            print(f"Initialized PID controller with params: {pid_params}, setpoint: {setpoint}")

            # 计算PID控制器的输出（水泵电压V）
            output = PID_controller(current)
            print(f"PID output: {output:.2f}")
            
        elif action == "get":
            # 获取pid输出
            setpoint = data.get("setpoint")
            current = data.get("current")
            print(f"Get current value: setpoint: {setpoint}, current: {current}")

            output = PID_controller(current)
            print(f"PID output: {output:.2f}")
            
        elif action == "end":
            # 结束仿真
            setpoint = data.get("setpoint")
            current = data.get("current")

            print(f"Simulation ended. setpoint: {setpoint}, current: {current}")
            output = "end"
    except Exception as e:
        print(f"msg handle error: {e}")
        stat = False

    return stat, output


if __name__ == "__main__":
    create_client()
    try:
        while True:
            # 连接服务器
            stat = connect_to_server()
            if not stat:
                print("Retrying connection in 5 seconds...")
                time.sleep(5)
            else:
                break
    except KeyboardInterrupt:
        # 关闭客户端
        PID_client.close()
        print("Keyboard interrupt received. Exit.")
    
    
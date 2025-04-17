# -*- coding: utf-8 -*-
import socket

host = "10.78.112.154" # 服务端IP地址
port = 21793 # 服务端端口号

Terminator = "\n" # 结束符

#创建一个socket对象
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    # 连接服务器
    client.connect((host, port))
    print(f"connected to {host}:{port}")
    
    while True:
        # 接收服务器消息（最多 1024 字节）
        data = client.recv(1024)
        if not data:
            continue  # 暂时没收到数据，继续等待
        
        message = data.decode('utf-8')
        print(f"get msg: {message}")
        
        # 发送相同的消息回去
        client.send(message.encode('utf-8'))
        
except ConnectionResetError:
    print("Connection error lost.")
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
    print("Connection lost.")

#关闭客户端
client.close()

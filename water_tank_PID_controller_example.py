import time
import numpy as np
import matplotlib.pyplot as plt
from simple_pid import PID

# 水箱参数
A = 1.0  # 水箱横截面积 (m^2)
a = 0.5  # 出水流速常数 (m^2.5/s)
b = 1.1  # 进水流速常数 (m^3/V·s)
H = 0.0  # 初始水位 (m)
Vol = H * A  # 初始水体积 (m^3)
# PID 控制器参数
setpoint = 2.0  # 目标水位 (m)
Kp = 5
Ki = 1
Kd = 0.8
pid = PID(Kp, Ki, Kd, setpoint=setpoint)  # 设置pid参数与目标值
pid.output_limits = (0, 15)  # 输出电压 V 的范围 (0V - 15V)

dt = 0.01  # 时间步长 (s)
time_steps = 300  # 仿真步数

# 记录数据用于绘图
time_log = []
H_log = []
V_log = []

for step in range(time_steps):
    # 计算 PID 控制器的输出（泵的电压 V）
    V = pid(H)
    print(f"Step {step}: Setpoint: {setpoint}, Current Level: {H:.2f}, Voltage: {V:.2f}")
    
    # 计算流入和流出速率
    inflow = b * V  # 进水速率 (m^3/s)
    outflow = a * np.sqrt(max(H, 0))  # 出水速率 (m^3/s)
    
    # 更新水体积和水位
    Vol += (inflow - outflow) * dt
    H = max(Vol / A, 0)  # 确保水位不为负值
    
    # 记录数据
    time_log.append(step * dt)
    H_log.append(H)
    V_log.append(V)
    
    # 短暂延迟模拟实时控制
    time.sleep(0.01)

# 绘制结果
plt.figure(figsize=(10, 5))
plt.subplot(2, 1, 1)
plt.plot(time_log, H_log, label='Water Level (m)')
plt.axhline(setpoint, color='r', linestyle='--', label='Setpoint')
plt.xlabel('Time (s)')
plt.ylabel('Water Level (m)')
plt.legend()
plt.grid()

plt.subplot(2, 1, 2)
plt.plot(time_log, V_log, label='Pump Voltage (V)', color='g')
plt.xlabel('Time (s)')
plt.ylabel('Voltage (V)')
plt.legend()
plt.grid()

plt.tight_layout()
plt.show()

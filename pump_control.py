# 化学笺集自动化滴定项目的一部分，用于控制滴定泵
# 作者：李峙德
# 邮箱：contact@chemview.net
# 最后更新：2025-9-26
import serial
import time

# 串口控制
class SerialPort:
    def __init__(self, com, baud=9600, timeout=3):
        self.com = com
        self.baud = baud
        self.timeout = timeout
        self.serial_port = serial.Serial(com, baud)
        time.sleep(2)

    def send(self, command):
        if not command.endswith('\n'):
            command += '\n'
        self.serial_port.write(command.encode())
        time.sleep(0.1)

    def close(self):
        self.serial_port.close()


# 泵控制
class Pump:
    def __init__(self, port, model='Arduino'):
        self.model = model
        self.serial_port = SerialPort(port)

    def setrate(self, rate):
        rate_lst = rate.split('.')

        if self.model == 'QHZS':
            self.serial_port.send(f'Q1H{rate_lst[0]}D')
            self.serial_port.send(f'Q2H{rate_lst[1]}D')
            self.serial_port.send('Q6H1D')
        elif self.model == 'Harvard':
            self.serial_port.send(f'MLM {float(rate)}')
        elif self.model == 'Arduino':
            if len(rate_lst[0]) == 1:  # 如果整数部分只有1位
                rate_str = '0' + rate_lst[0] + rate_lst[1].ljust(2, '0')
            else:
                rate_str = rate_lst[0] + rate_lst[1].ljust(2, '0')
            self.serial_port.send(f'SETRATE {rate_str}')

    def start(self):
        if self.model == 'QHZS':
            self.serial_port.send('Q6H2D')
        elif self.model == 'Harvard':
            self.serial_port.send('RUN')
        elif self.model == 'Arduino':
            self.serial_port.send('RUN')

    def stop(self):
        if self.model == 'QHZS':
            self.serial_port.send('Q6H6D')
        elif self.model == 'Harvard':
            self.serial_port.send('STP')
        elif self.model == 'Arduino':
            self.serial_port.send('STOP')

    def release(self):
        self.stop()
        self.serial_port.close()
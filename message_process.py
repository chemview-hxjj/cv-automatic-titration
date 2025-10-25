# 化学笺集自动化滴定项目的一部分，用于实现消息提醒及日志记录
# 作者：李峙德
# 邮箱：contact@chemview.net
# 最后更新：2025-10-25
# send wa 等待 cs 硬件连接就绪 ce 硬件连接错误 te 滴定过程错误 se 停止错误 re 润洗错误 le 释放错误 i* 初始化平均颜色 f* 终点平均颜色 me 大模型预测错误
# alert ep 滴定终点 rs 取样区域太小
# log et 终点判定条件 ef 恢复原色 ri 润洗 rl 释放 pr 大模型预测 gc 配置已保存 ve 视频流生成错误 ar API返回配置 cw 创建窗口错误 ms 手动停止
# box ru 正在滴定
import time
import pymsgbox
import plyer

class MessageProcessor:

    def __init__(self):
        self.message=None
        self.webmsg={'wa':'等待', 'cs':'就绪', 'ce':'硬件连接错误', 'te':'滴定过程错误', 'se':'停止错误', 're':'润洗错误', 'le':'释放错误', 'me':'大模型预测错误'}
        self.alertmsg={'ep':'到达滴定终点！消耗滴定液体积', 'rs':'取样区域太小，请重新选择！'}
        self.boxmsg={'ru':'正在滴定...'}
        self.logmsg={'wa':'WAITING', 
                     'cs':'READY', 
                     'ce':'HWCONNECTIONERROR', 
                     'te':'TITRATIONERROR', 
                     'se':'STOPERROR', 
                     're':'RINSEERROR', 
                     'le':'RELEASEERROR', 
                     'ep':'ENDPOINTVOLUME', 
                     'ru':'RUNTITRATION',  
                     'et':'NEARENDPOINT', 
                     'ef':'COLORRECOVERED',
                     'ri':'RINSE', 
                     'rl':'RELEASE', 
                     'pr':'LLMPREDICT', 
                     'il':'SETLEFTINITIALHSVCOLOR', 
                     'im':'SETMIDDLEINITIALHSVCOLOR', 
                     'ir':'SETRIGHTINITIALHSVCOLOR', 
                     'fl':'FINALLEFTHSVCOLOR', 
                     'fm':'FINALMIDDELHSVCOLOR', 
                     'fr':'FINALRIGHTHSVCOLOR', 
                     'gc':'GETSAVEDCONFIG', 
                     've':'VIDEOGENERATEERROR', 
                     'ar':'APIRETURNEDCONFIG', 
                     'cw':'CREATWINDOWERROR',
                     'ms':'STOP', 
                     'av':'INITIALAVERAGEHSVCOLOR', 
                     'ig':'INITIALRANGE', 
                     'rs':'ROIRANGETOOSMALL', 
                     'pe':'PREVIEWERROR', 
                     'me':'LLMPREDICTERROR'}

    def send(self, msg, d=''):
        try:
            if d:
                self.message=f'{self.webmsg[msg]}：{d}'
            else:
                self.message=self.webmsg[msg]
            self.log(msg, d)
        except Exception as e:
            print(e)

    def alert(self, msg, d=''):
        try:
            self.log(msg, d)
            if d:
                pymsgbox.alert(text=f'{self.alertmsg[msg]}：{d}', title='化学笺集自动化滴定项目')
            else:
                pymsgbox.alert(text=self.alertmsg[msg], title='化学笺集自动化滴定项目')
        except Exception as e:
            print(e)

    def box(self, msg, d=''):
        try:
            self.log(msg, d)
            if d:
                plyer.notification.notify(
                    title='化学笺集自动化滴定项目',
                    message=f'{self.boxmsg[msg]}：{d}',
                    app_name="化学笺集自动化滴定项目",
                    timeout=3,
                )
            else:
                plyer.notification.notify(
                    title='化学笺集自动化滴定项目',
                    message=self.boxmsg[msg],
                    app_name="化学笺集自动化滴定项目",
                    timeout=3,
                )
        except Exception as e:
            print(e)

    def log(self, msg, d=''):
        try:
            t=time.strftime('%H:%M:%S', time.localtime())
            with open('cat.log', 'a') as file:
                file.write(f'\n{t} {self.logmsg[msg]}{d}')
        except Exception as e:
            print(e)

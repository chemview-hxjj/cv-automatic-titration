# 化学笺集自动化滴定项目的一部分，用于实现颜色识别及相关功能
# 作者：李峙德，刘一弘
# 邮箱：contact@chemview.net
# 最后更新：2025-10-24
import cv2
from collections import deque
import time
import threading
import numpy as np
import cap_process
import pump_control
import ds_connect

class ColorDetect:

    def __init__(self,threshold,threshold_times,sequence_length=5):
        self.proc=None
        self.initialized=False
        self.l_reference_hsv=None
        self.m_reference_hsv=None
        self.r_reference_hsv=None
        self.threshold=threshold
        self.threshold_times=threshold_times
        self.h_h=deque(maxlen=sequence_length)
        self.s_h=deque(maxlen=sequence_length)
        self.v_h=deque(maxlen=sequence_length)
        self.l_current_hsv=None
        self.m_current_hsv=None
        self.r_current_hsv=None
        self.mp=None

    def _initialize(self):
        time.sleep(1)
        self.proc.create_roi_mask()
        self.l_reference_hsv,self.m_reference_hsv,self.r_reference_hsv=self.proc.get_hsv_values()
        self.mp.log('il',self.l_reference_hsv)
        self.mp.log('im',self.m_reference_hsv)
        self.mp.log('ir',self.r_reference_hsv)
        self.initialized=True

    def is_color_changed(self):
        if not self.initialized:
            self._initialize()

        self.l_current_hsv, self.m_current_hsv, self.r_current_hsv = self.proc.get_hsv_values()

        ## Middle ##
        # 计算与参考颜色的差异
        m_h_diff = abs(self.m_current_hsv[0] - self.m_reference_hsv[0])
        m_s_diff = abs(self.m_current_hsv[1] - self.m_reference_hsv[1])
        m_v_diff = abs(self.m_current_hsv[2] - self.m_reference_hsv[2])

        # 存储历史值
        self.h_h.append(m_h_diff)
        self.s_h.append(m_s_diff)
        self.v_h.append(m_v_diff)
        
        # 权重更大
        m_h_change = m_h_diff > self.threshold # 相较于后续的*self.threshold_times阈值*1倍数更小，因此权重更大
        m_s_change = m_s_diff > self.threshold     
        m_v_change = m_v_diff > self.threshold * 3 # V通道更敏感

        ## Right ##
        # 计算与参考颜色的差异
        r_h_diff = abs(self.r_current_hsv[0] - self.r_reference_hsv[0])
        r_s_diff = abs(self.r_current_hsv[1] - self.r_reference_hsv[1])
        r_v_diff = abs(self.r_current_hsv[2] - self.r_reference_hsv[2])
        
        # 因环境影响，权重较弱
        r_h_change = r_h_diff > self.threshold * self.threshold_times # 为阈值加权，因此整体权重变弱
        r_s_change = r_s_diff > self.threshold * self.threshold_times
        r_v_change = r_v_diff > self.threshold * 3 * self.threshold_times # V通道更敏感

        ## Left ##
        # 计算与参考颜色的差异
        l_h_diff = abs(self.l_current_hsv[0] - self.l_reference_hsv[0])
        l_s_diff = abs(self.l_current_hsv[1] - self.l_reference_hsv[1])
        l_v_diff = abs(self.l_current_hsv[2] - self.l_reference_hsv[2])
        
        # 因环境影响，权重较弱
        l_h_change = l_h_diff > self.threshold * self.threshold_times # 为阈值加权，因此整体权重变弱
        l_s_change = l_s_diff > self.threshold * self.threshold_times 
        l_v_change = l_v_diff > self.threshold * 3 * self.threshold_times # V通道更敏感

        # 检查是否有任何一个通道变化明显
        m_any_changed = m_h_change or m_s_change or m_v_change # 中间部分hsv变化
        r_any_changed = r_h_change or r_s_change or r_v_change # 右侧部分hsv变化
        l_any_changed = l_h_change or l_s_change or l_v_change # 左侧部分hsv变化
        any_changed = m_any_changed or r_any_changed or l_any_changed #整体hsv变化

        return any_changed

    def is_color_homo(self):
        if not self.initialized:
            self._initialize()

        l_current_hsv, m_current_hsv, r_current_hsv = self.proc.get_hsv_values()

        h_homo=abs(l_current_hsv[0]-m_current_hsv[0])+abs(r_current_hsv[0]-m_current_hsv[0])
        s_homo=abs(l_current_hsv[1]-m_current_hsv[1])+abs(r_current_hsv[1]-m_current_hsv[1])
        v_homo=abs(l_current_hsv[2]-m_current_hsv[2])+abs(r_current_hsv[2]-m_current_hsv[2])

        homo=h_homo<self.threshold and s_homo<self.threshold and v_homo<self.threshold*2

        return homo

# 9.22 Charlotte_liu修改
class Timer:

    def __init__(self):
        self.time_dict = {'elapsed':0.0,'start':0.0,'pause':0.0}
        self.started = False
        self.paused = False

    def start(self):
        self.time_dict['start']=time.time()
        self.started = True

    def update_time(self):
        elapsed=time.time()-self.time_dict['start']
        self.time_dict['elapsed']=elapsed

    def pause(self):
        if self.started:
            elapsed = time.time()-self.time_dict['start']
            self.time_dict['elapsed']+=elapsed
            self.time_dict['pause']=time.time()
            self.paused=True

    def reset(self): #
        self.time_dict = {'elapsed': 0.0, 'start': 0.0, 'pause': 0.0}
        self.started = False
        self.paused = False

class Titration:

    def __init__(self,rate='05.00',port='COM1',cap_num=0,threshold=30,threshold_times=1.5):
        self.rate=rate
        self.port=port
        self.cap_num=cap_num
        self.threshold=threshold
        self.threshold_times=threshold_times
        self.usemask=True
        self.cd=None
        self.pump=None
        self.cap=None
        self.running=False
        self.endpoint=False
        self.volume=0
        self.time=0
        self.mp=None
        self._titration_thread = None
        self.predict_color=None
        self.predict_hsv=None
        self.timer_normal=None
        self.timer_elapsed=None
        self.ispreview=True

    def _run_con(self):
        try:
            self.mp.send('wa')
            self.cd=ColorDetect(self.threshold,self.threshold_times)
            self.cd.mp=self.mp

            self.pump=pump_control.Pump(self.port)
            self.pump.setrate(self.rate)

            self.cap=cap_process.Cap(int(self.cap_num))
            self.cd.proc=cap_process.HSVProcessor()
            self.cd.proc.mp=self.mp
            self.cd.proc.frame=self.cap.get_frame()
            self.cd.proc.usemask=self.usemask
            self.mp.send('cs')
            time.sleep(1)
            self.preview()
        except Exception as e:
            self.mp.send('ce',f'{e}')

    def con(self):
        # 连接硬件
        con_thread = threading.Thread(target=self._run_con)
        con_thread.daemon = True
        con_thread.start()
    
    def _run_preview(self):
        time.sleep(1)
        try:
            while self.ispreview:
                self.cd.proc.frame=self.cap.get_frame()
                frame_copy=self.cd.proc.show_frame_window()
        except Exception as e:
                self.mp.log('pe',f'{e}')
        
    def preview(self):
        self._preview_thread = threading.Thread(target=self._run_preview)
        self._preview_thread.daemon = True
        self._preview_thread.start()

    def _run_titration(self):
        self.ispreview=False
        self.volume=0
        self.time=0
        self.timer_normal = Timer()
        self.timer_elapsed = Timer()
        pump_stopped = False
        last_elapsed = 0
        pump_lock = threading.Lock()

        def safe_pump_operation(operation):
            with pump_lock:
                if operation == 'start':
                    self.pump.start()
                    return True
                elif operation == 'stop':
                    self.pump.stop()
                    return True
            return False

        if self.running:
            if safe_pump_operation('start'):
                self.timer_normal.start()

        while self.running:
            try:
                self.cd.proc.frame = self.cap.get_frame()
                is_color_changed = self.cd.is_color_changed()
                # is_color_homo = self.cd.is_color_homo()
                frame_copy=self.cd.proc.show_frame_window()

                if is_color_changed:
                    if self.timer_normal.started and last_elapsed:
                        if safe_pump_operation('stop'):
                            pump_stopped = True

                        self.timer_normal.pause()
                        time_elapsed = self.timer_normal.time_dict['elapsed']
                        self.time += time_elapsed
                        volume_increment = float(self.rate) / 60 * time_elapsed
                        self.volume += volume_increment
                        self.endpoint = True
                        self.mp.log('et')
                        self.timer_normal.reset()

                    if not self.timer_elapsed.started or self.timer_elapsed.paused:
                        self.timer_elapsed.start()

                    self.timer_elapsed.update_time()

                    if self.timer_elapsed.time_dict['elapsed'] >= 15 and self.running:
                        self.mp.alert('ep',f'{self.volume:.2f} mL')
                        self.running=False
                        self.mp.log('fl',self.cd.l_current_hsv)
                        self.mp.log('fm',self.cd.m_current_hsv)
                        self.mp.log('fr',self.cd.r_current_hsv)
                        self.timer_elapsed.reset()
                        self.stop()

                else:
                    if self.timer_elapsed.started and not self.timer_elapsed.paused:
                        last_elapsed = self.timer_elapsed.time_dict['elapsed']
                        self.timer_elapsed.pause()
                        self.endpoint = False
                        self.mp.log('ef')
                        self.timer_elapsed.reset()

                    if pump_stopped:
                        if safe_pump_operation('start'):
                            pump_stopped = False 

                    if not self.timer_normal.started or self.timer_normal.paused:
                        self.timer_normal.start()

            except Exception as e:
                self.release()
                self.running=False
                self.mp.send('te',f'{e}')

    def run(self):
        if not self.running:
            self.running = True
            self._titration_thread = threading.Thread(target=self._run_titration)
            self._titration_thread.daemon = True
            self._titration_thread.start()
            self.mp.box('ru')

    def stop(self):
        try:
            self.pump.stop()
            self.running = False
            self.endpoint=False
            self.pump.setrate(self.rate)
            self.volume=0
            self.time=0
            self.timer_normal.reset()
            self.timer_elapsed.reset()
            time.sleep(0.1)
            self.ispreview=True
            self.preview()
            self.mp.log('ms')
        except Exception as e:
            self.mp.send('se',f'{e}')

    def _run_rinse(self):
        try:
            self.pump.setrate('15.00')
            self.pump.start()
            time1=time.time()
            time2=time1
            while time2-time1<60:
                time2=time.time()
            self.pump.setrate(self.rate)
            self.pump.stop()
        except Exception as e:
            self.mp.send('re',f'{e}')

    def rinse(self):
        rinse_thread = threading.Thread(target=self._run_rinse)
        rinse_thread.daemon = True
        rinse_thread.start()
        self.mp.log('ri')

    def release(self):
        try:
            self.stop()
            self.pump.release()
            self.mp.log('rl')
        except Exception as e:
            self.mp.send('le',f'{e}')

    def llm_predict(self,exptype):
        try:
            predict_color=ds_connect.llm_get_color(exptype)
            self.predict_color=predict_color
            def hex_to_hsv(hex_color):
                hex_color = hex_color.lstrip('#')
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                bgr_array = np.uint8([[[b, g, r]]])
                hsv_array = cv2.cvtColor(bgr_array, cv2.COLOR_BGR2HSV)
                h, s, v = hsv_array[0][0]
                return [h, s, v]
            predict_hsv=hex_to_hsv(predict_color)
            self.predict_hsv=predict_hsv
            self.mp.log('pr')
        except Exception as e:
            self.mp.send('me',f'{e}')
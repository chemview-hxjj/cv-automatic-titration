# 化学笺集自动化滴定项目的一部分，用于捕获及处理图像
# 作者：刘一弘，李峙德
# 邮箱：contact@chemview.net
# 最后更新：2025-10-18
import cv2
import numpy as np

class Cap:

    def __init__(self,cap_num):
        self.cap_num=cap_num
        self.cap=None
        self.frame=None

    def open_cap(self):
        self.cap = cv2.VideoCapture(int(self.cap_num))
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1.0) # 打开自动曝光
        self.cap.set(cv2.CAP_PROP_AUTO_WB, 1.0)
        self.cap.set(cv2.CAP_PROP_AUTO_WB, 0.0)

        if not self.cap.isOpened():
            raise Exception('CapConnectionError')

    def close_cap(self):
        self.cap.release()

    def get_frame(self):
        if not self.cap:
            self.open_cap()

        ret,frame = self.cap.read()
        if not ret:
            raise Exception('CapReadError')

        self.frame=frame

        return frame

class HSVProcessor:

    def __init__(self):
        # 初始化变量
        self.drawing = False
        self.ix, self.iy = -1, -1
        self.fx, self.fy = -1, -1
        self.sample_roi = None
        self.hsv_lower = np.array([0, 0, 0])
        self.hsv_upper = np.array([179, 255, 255])
        self.frame = None
        self.frame_copy=None
        self.usemask=True
        self.left_avg = None
        self.middle_avg = None
        self.right_avg = None
        self.mp=None

    def get_hsv_values(self):
        # 转换为HSV
        hsv_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)

        if self.usemask:
            # 创建掩膜
            mask = cv2.inRange(hsv_frame, self.hsv_lower, self.hsv_upper)
            # 应用掩膜
            masked_frame = cv2.bitwise_and(self.frame, self.frame, mask=mask)

            # 将图像分为左、中、右三部分
            x, y, w, h = self.sample_roi
            part_width = w // 3

            left_part = masked_frame[y:y + h, x:x + part_width]
            middle_part = masked_frame[y:y + h, x + part_width:x + 2 * part_width]
            right_part = masked_frame[y:y + h, x + 2 * part_width:x + 3 * part_width]

        else:
            x, y, w, h = self.sample_roi
            part_width = w // 3

            left_part = hsv_frame[y:y + h, x:x + part_width]
            middle_part = hsv_frame[y:y + h, x + part_width:x + 2 * part_width]
            right_part = hsv_frame[y:y + h, x + 2 * part_width:x + 3 * part_width]

        # 计算各部分的平均HSV值
        left_hsv = cv2.cvtColor(left_part, cv2.COLOR_BGR2HSV)
        middle_hsv = cv2.cvtColor(middle_part, cv2.COLOR_BGR2HSV)
        right_hsv = cv2.cvtColor(right_part, cv2.COLOR_BGR2HSV)

        # 计算平均值
        def avg_hsv_nonblack(hsv_img):
            # 创建非黑色掩膜
            non_black_mask = np.any(hsv_img != [0, 0, 0], axis=-1)
            if np.any(non_black_mask):
                return np.mean(hsv_img[non_black_mask], axis=0)
            return np.array([0, 0, 0])

        left_avg = avg_hsv_nonblack(left_hsv)
        middle_avg = avg_hsv_nonblack(middle_hsv)
        right_avg = avg_hsv_nonblack(right_hsv)

        self.left_avg=left_avg
        self.middle_avg=middle_avg
        self.right_avg=right_avg

        return left_avg, middle_avg, right_avg

    def show_frame_window(self):
        frame_copy=self.frame.copy()

        # 显示取样区域
        if self.sample_roi is not None:
            x, y, w, h = self.sample_roi
            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # 绘制分割线
            part_width = w // 3
            cv2.line(frame_copy, (x + part_width, y), (x + part_width, y + h), (255, 0, 0), 1)
            cv2.line(frame_copy, (x + 2 * part_width, y), (x + 2 * part_width, y + h), (255, 0, 0), 1)

        # 在图像上显示HSV值
        if self.left_avg is not None and self.middle_avg is not None and self.right_avg is not None:
            # 格式化HSV值为整数
            left_text = f"L: H{int(self.left_avg[0])} S{int(self.left_avg[1])} V{int(self.left_avg[2])}"
            middle_text = f"M: H{int(self.middle_avg[0])} S{int(self.middle_avg[1])} V{int(self.middle_avg[2])}"
            right_text = f"R: H{int(self.right_avg[0])} S{int(self.right_avg[1])} V{int(self.right_avg[2])}"
            
            # 设置文本位置和样式
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            color = (255, 255, 255)  # 白色文字
            
            # 在图像顶部显示HSV值
            cv2.putText(frame_copy, left_text, (20, 30), font, font_scale, color, thickness)
            cv2.putText(frame_copy, middle_text, (20, 60), font, font_scale, color, thickness)
            cv2.putText(frame_copy, right_text, (20, 90), font, font_scale, color, thickness)

        self.frame_copy=frame_copy

        return frame_copy

    def create_roi_mask(self):
        frame_copy = self.frame.copy()

        cv2.namedWindow("Create ROI", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Create ROI", self._mouse_callback)
        cv2.imshow("Create ROI", frame_copy)

        k = cv2.waitKey(0) & 0xFF
        if k == 27:
            cv2.destroyAllWindows()

    def _show_adjust_window(self):
        cv2.namedWindow('HSV Adjustments')

        # 将HSV值转换为整数
        h_low_int = int(self.hsv_lower[0])
        h_high_int = int(self.hsv_upper[0])
        s_low_int = int(self.hsv_lower[1])
        s_high_int = int(self.hsv_upper[1])
        v_low_int = int(self.hsv_lower[2])
        v_high_int = int(self.hsv_upper[2])

        # 创建轨迹栏
        cv2.createTrackbar('H Low', 'HSV Adjustments', h_low_int, 179, self._nothing)
        cv2.createTrackbar('H High', 'HSV Adjustments', h_high_int, 179, self._nothing)
        cv2.createTrackbar('S Low', 'HSV Adjustments', s_low_int, 255, self._nothing)
        cv2.createTrackbar('S High', 'HSV Adjustments', s_high_int, 255, self._nothing)
        cv2.createTrackbar('V Low', 'HSV Adjustments', v_low_int, 255, self._nothing)
        cv2.createTrackbar('V High', 'HSV Adjustments', v_high_int, 255, self._nothing)

    def _update_hsv_region(self):
        h_low = cv2.getTrackbarPos('H Low', 'HSV Adjustments')
        h_high = cv2.getTrackbarPos('H High', 'HSV Adjustments')
        s_low = cv2.getTrackbarPos('S Low', 'HSV Adjustments')
        s_high = cv2.getTrackbarPos('S High', 'HSV Adjustments')
        v_low = cv2.getTrackbarPos('V Low', 'HSV Adjustments')
        v_high = cv2.getTrackbarPos('V High', 'HSV Adjustments')

        # 更新HSV范围
        self.hsv_lower = np.array([h_low, s_low, v_low])
        self.hsv_upper = np.array([h_high, s_high, v_high])

    def _show_mask_window(self):
        hsv_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_frame, self.hsv_lower, self.hsv_upper)
        cv2.imshow("Mask Preview", mask)

    def _nothing(self, x):
        pass

    def _mouse_callback(self, event, x, y, a, b):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y
            self.fx, self.fy = x, y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.fx, self.fy = x, y
                # 绘制临时矩形
                temp_frame = self.frame.copy()
                cv2.rectangle(temp_frame, (self.ix, self.iy), (self.fx, self.fy), (0, 255, 0), 2)
                cv2.imshow("Create ROI", temp_frame)

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.fx, self.fy = x, y
            # 确保矩形有效
            if abs(self.fx - self.ix) > 5 and abs(self.fy - self.iy) > 5:
                # 保存ROI坐标
                self.sample_roi = (min(self.ix, self.fx), min(self.iy, self.fy),
                                   abs(self.fx - self.ix), abs(self.fy - self.iy))

                # 计算平均HSV值
                temp_frame = self.frame.copy()
                roi_frame = temp_frame[self.iy:self.fy, self.ix:self.fx]
                hsv_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
                avg_hsv = np.mean(hsv_roi, axis=(0, 1))

                # 设置初始HSV范围
                self.hsv_lower = np.array([
                    max(0, int(avg_hsv[0] - 10)),
                    max(0, int(avg_hsv[1] - 40)),
                    max(0, int(avg_hsv[2] - 40))
                ])
                self.hsv_upper = np.array([
                    min(179, int(avg_hsv[0] + 10)),
                    min(255, int(avg_hsv[1] + 40)),
                    min(255, int(avg_hsv[2] + 40))
                ])

                self.mp.log('av',f'{avg_hsv}')
                self.mp.log('ig',f'{self.hsv_lower}{self.hsv_upper}')
            else:
                self.mp.alert('rs')

            if self.usemask:
                self._show_adjust_window()

                while True:
                    self._update_hsv_region()
                    self._show_mask_window()
                    k = cv2.waitKey(1) & 0xFF
                    if k == 27:
                        cv2.destroyAllWindows()
                        break
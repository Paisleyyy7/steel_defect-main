from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QGridLayout, QSizePolicy, QFrame
)
from qfluentwidgets import (
    PushButton, ComboBox, SpinBox, InfoBar, InfoBarPosition, CardWidget,
    ElevatedCardWidget, TitleLabel, BodyLabel, CaptionLabel, PrimaryPushButton, 
    FluentIcon, ToggleButton, SmoothScrollArea, ProgressBar, HeaderCardWidget
)


class RealtimeInferenceView(QWidget):
    """实时推理视图，包含摄像头预览和推理结果显示"""

    # 定义信号
    camera_selected_signal = pyqtSignal(int)  # 摄像头选择信号
    toggle_camera_signal = pyqtSignal()  # 开关摄像头信号
    start_inference_signal = pyqtSignal(bool)  # 开始/停止推理信号
    inference_interval_changed_signal = pyqtSignal(int)  # 推理间隔时间变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RealtimeInferenceView")
        
        # 初始化UI组件
        self._init_ui()
        
    def _init_ui(self):
        """初始化UI布局和组件"""
        # 主滚动区域
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # 顶部标题栏
        header_layout = QHBoxLayout()
        title = TitleLabel("实时推理监控")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 状态指示器
        self.status_indicator = BodyLabel("● 等待启动")
        self.status_indicator.setStyleSheet("color: #6c757d; font-weight: bold;")
        header_layout.addWidget(self.status_indicator)
        
        main_layout.addLayout(header_layout)
        
        # 顶部区域：控制面板
        control_panel = ElevatedCardWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(20, 15, 20, 15)
        control_layout.setSpacing(20)
        
        # 摄像头控制组
        camera_group = QFrame()
        camera_group_layout = QHBoxLayout(camera_group)
        camera_group_layout.setContentsMargins(0, 0, 0, 0)
        
        camera_label = BodyLabel("摄像头:")
        camera_label.setStyleSheet("font-weight: bold;")
        self.camera_select = ComboBox()
        self.camera_select.setPlaceholderText("选择摄像头")
        self.camera_select.setMinimumWidth(150)
        
        self.toggle_camera_btn = PrimaryPushButton("启动摄像头")
        self.toggle_camera_btn.setIcon(FluentIcon.PLAY)
        self.toggle_camera_btn.setFixedHeight(32)
        
        camera_group_layout.addWidget(camera_label)
        camera_group_layout.addWidget(self.camera_select)
        camera_group_layout.addWidget(self.toggle_camera_btn)
        
        # 推理控制组
        inference_group = QFrame()
        inference_group_layout = QHBoxLayout(inference_group)
        inference_group_layout.setContentsMargins(0, 0, 0, 0)
        
        model_label = BodyLabel("模型:")
        model_label.setStyleSheet("font-weight: bold;")
        self.model_select = ComboBox()
        self.model_select.setPlaceholderText("选择模型")
        self.model_select.setMinimumWidth(150)
        
        interval_label = BodyLabel("间隔:")
        interval_label.setStyleSheet("font-weight: bold;")
        self.inference_interval = SpinBox()
        self.inference_interval.setRange(1, 60)
        self.inference_interval.setValue(5)
        self.inference_interval.setSuffix("秒")
        self.inference_interval.setFixedWidth(140)
        
        self.toggle_inference_btn = PrimaryPushButton("开始推理")
        self.toggle_inference_btn.setIcon(FluentIcon.PLAY)
        self.toggle_inference_btn.setFixedHeight(32)
        self.toggle_inference_btn.setEnabled(False)
        
        inference_group_layout.addWidget(model_label)
        inference_group_layout.addWidget(self.model_select)
        inference_group_layout.addWidget(interval_label)
        inference_group_layout.addWidget(self.inference_interval)
        inference_group_layout.addWidget(self.toggle_inference_btn)        
        control_layout.addWidget(camera_group)
        control_layout.addWidget(QFrame())  # 分隔符
        control_layout.addWidget(inference_group)
        control_layout.addStretch()
        
        main_layout.addWidget(control_panel)
        
        # 中间区域：图像预览
        preview_section = QHBoxLayout()
        preview_section.setSpacing(24)
        
        # 左侧：摄像头预览
        camera_section = HeaderCardWidget()
        camera_section.setTitle("摄像头预览")
        
        # 摄像头预览容器
        camera_preview_frame = QFrame()
        camera_preview_frame.setFrameStyle(QFrame.Shape.Box)
        camera_preview_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
            }
        """)
        camera_preview_layout = QVBoxLayout(camera_preview_frame)
        camera_preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.camera_preview_label = QLabel("等待摄像头启动...")
        self.camera_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_preview_label.setMinimumSize(460, 345)
        self.camera_preview_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 14px;
                background: transparent;
                border: none;
            }
        """)
        camera_preview_layout.addWidget(self.camera_preview_label)
        camera_section.viewLayout.addWidget(camera_preview_frame)
        
        # 右侧：推理结果预览
        result_card = HeaderCardWidget()
        result_card.setTitle('推理结果')
        
        # 结果预览容器
        result_preview_frame = QFrame()
        result_preview_frame.setFrameStyle(QFrame.Shape.Box)
        result_preview_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
            }
        """)
        result_preview_layout = QVBoxLayout(result_preview_frame)
        result_preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.result_preview_label = QLabel("等待推理结果...")
        self.result_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_preview_label.setMinimumSize(460, 345)
        self.result_preview_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 14px;
                background: transparent;
                border: none;
            }
        """)
        result_preview_layout.addWidget(self.result_preview_label)
        result_card.viewLayout.addWidget(result_preview_frame)
        
        preview_section.addWidget(camera_section)
        preview_section.addWidget(result_card)
        
        main_layout.addLayout(preview_section)
        
        # 底部区域：统计信息
        stats_card = HeaderCardWidget()
        stats_card.setTitle('实时统计')
        
        # 统计数据布局
        stats_vbox = QVBoxLayout()
        stats_vbox.setSpacing(12)
        stats_vbox.setContentsMargins(0, 0, 0, 0)
        
        # 统计网格
        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        
        # 总帧数
        total_layout = QHBoxLayout()
        total_layout.addWidget(BodyLabel("总计帧数:"))
        self.total_frames_label = BodyLabel("0")
        self.total_frames_label.setStyleSheet("font-weight: bold;")
        total_layout.addWidget(self.total_frames_label)
        total_layout.addStretch()
        stats_vbox.addLayout(total_layout)
        
        # 缺陷帧数
        defect_frames_layout = QHBoxLayout()
        defect_frames_layout.addWidget(BodyLabel("缺陷帧数:"))
        self.defect_frames_label = BodyLabel("0")
        self.defect_frames_label.setStyleSheet("font-weight: bold;")
        defect_frames_layout.addWidget(self.defect_frames_label)
        defect_frames_layout.addStretch()
        stats_vbox.addLayout(defect_frames_layout)
        
        # 缺陷比例
        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(BodyLabel("缺陷比例:"))
        self.defect_ratio_label = BodyLabel("0%")
        self.defect_ratio_label.setStyleSheet("font-weight: bold;")
        ratio_layout.addWidget(self.defect_ratio_label)
        ratio_layout.addStretch()
        stats_vbox.addLayout(ratio_layout)
        
        # 缺陷总数
        count_layout = QHBoxLayout()
        count_layout.addWidget(BodyLabel("缺陷总数:"))
        self.defect_count_label = BodyLabel("0")
        self.defect_count_label.setStyleSheet("font-weight: bold;")
        count_layout.addWidget(self.defect_count_label)
        count_layout.addStretch()
        stats_vbox.addLayout(count_layout)        
        
        # 将布局添加到HeaderCardWidget的viewLayout中
        stats_card.viewLayout.addLayout(stats_vbox)
        main_layout.addWidget(stats_card)
        
        # 设置滚动区域
        scroll.setWidget(main_widget)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
          # 连接信号
        self.camera_select.currentIndexChanged.connect(
            lambda idx: self.camera_selected_signal.emit(idx)
        )
        self.toggle_camera_btn.clicked.connect(self.toggle_camera_signal)
        self.toggle_inference_btn.clicked.connect(self._toggle_inference)
        self.inference_interval.valueChanged.connect(self.inference_interval_changed_signal)
        
    def update_camera_list(self, camera_list):
        """更新摄像头列表"""
        try:
            self.camera_select.clear()
            
            for camera in camera_list:
                # 使用摄像头列表中的id作为userData
                camera_id = camera.get('id')
                description = camera.get('description', f"摄像头 {camera_id}")
                self.camera_select.addItem(description, userData=camera_id)
            
            # 如果有摄像头，选择第一个
            if self.camera_select.count() > 0:
                self.camera_select.setCurrentIndex(0)
            
        except Exception as e:
            self.show_error("错误", f"更新摄像头列表失败: {str(e)}")
            
    def update_model_list(self, model_list):
        """更新模型列表"""
        self.model_select.clear()
        for model in model_list:
            self.model_select.addItem(model)
            
    def update_camera_frame(self, frame):
        """更新摄像头画面"""
        if frame is not None:
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            scaled_pixmap = pixmap.scaled(
                self.camera_preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.camera_preview_label.setPixmap(scaled_pixmap)
            
    def update_result_frame(self, frame):
        """更新推理结果画面"""
        if frame is not None:
            # 确保是RGB格式
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img)
                scaled_pixmap = pixmap.scaled(
                    self.result_preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.result_preview_label.setPixmap(scaled_pixmap)
            
    def set_camera_state(self, is_running):
        """设置摄像头状态"""
        if is_running:
            self.toggle_camera_btn.setText("关闭摄像头")
            self.toggle_camera_btn.setIcon(FluentIcon.PAUSE)
            self.camera_select.setEnabled(False)
            self.status_indicator.setText("● 摄像头运行中")
            self.status_indicator.setStyleSheet("color: #28a745; font-weight: bold;")
        else:
            self.toggle_camera_btn.setText("启动摄像头")
            self.toggle_camera_btn.setIcon(FluentIcon.PLAY)
            self.camera_select.setEnabled(True)
            self.toggle_inference_btn.setText("开始推理")
            self.toggle_inference_btn.setIcon(FluentIcon.PLAY)
            self.toggle_inference_btn.setEnabled(False)
            self.camera_preview_label.setText("等待摄像头启动...")
            self.camera_preview_label.setPixmap(QPixmap())
            self.status_indicator.setText("● 等待启动")
            self.status_indicator.setStyleSheet("color: #6c757d; font-weight: bold;")
            
    def set_inference_state(self, is_running):
        """设置推理状态"""
        if is_running:
            self.toggle_inference_btn.setText("停止推理")
            self.toggle_inference_btn.setIcon(FluentIcon.PAUSE)
            self.inference_interval.setEnabled(False)
            self.model_select.setEnabled(False)
            self.status_indicator.setText("● 推理进行中")
            self.status_indicator.setStyleSheet("color: #007bff; font-weight: bold;")
        else:
            self.toggle_inference_btn.setText("开始推理")
            self.toggle_inference_btn.setIcon(FluentIcon.PLAY)
            self.inference_interval.setEnabled(True)
            self.model_select.setEnabled(True)
            
    def _toggle_inference(self):
        """切换推理状态"""
        is_running = self.toggle_inference_btn.text() == "停止推理"
        self.start_inference_signal.emit(not is_running)        
    def update_statistics(self, total_frames, defect_frames, defect_count):
        """更新统计信息"""
        self.total_frames_label.setText(str(total_frames))
        self.defect_frames_label.setText(str(defect_frames))
        self.defect_count_label.setText(str(defect_count))
        
        # 计算比例
        if total_frames > 0:
            defect_ratio = (defect_frames / total_frames) * 100
            self.defect_ratio_label.setText(f"{defect_ratio:.1f}%")
        else:
            self.defect_ratio_label.setText("0%")
            
    def enable_inference_controls(self, enabled):
        """启用或禁用推理控制"""
        self.toggle_inference_btn.setEnabled(enabled)
        
    def show_notification(self, title, message, duration=3000):
        """显示通知消息"""
        InfoBar.success(
            title=title,
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=self
        )
        
    def show_error(self, title, message, duration=3000):
        """显示错误消息"""
        InfoBar.error(
            title=title,
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=self
        )
        
    def get_current_model(self):
        """获取当前选择的模型"""
        return self.model_select.currentText()
        
    def get_inference_interval(self):
        """获取推理间隔"""
        return self.inference_interval.value()
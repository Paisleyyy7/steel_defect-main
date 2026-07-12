from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QFrame, QScrollArea
from qfluentwidgets import (
    PushButton, ComboBox, SpinBox, InfoBar, InfoBarPosition, CardWidget,
    ElevatedCardWidget, TitleLabel, BodyLabel, CaptionLabel, PrimaryPushButton, 
    FluentIcon, ToggleButton, SmoothScrollArea, HeaderCardWidget
)


class CameraView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.init_ui()
        # 控制变量：用于控制拍摄状态
        self.captured_image = None  # 存储拍摄的图像
        self.capture_status = False  # False: 未拍摄，True: 已拍摄

    def init_ui(self):
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
        title = TitleLabel("摄像头拍摄")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 状态指示器
        self.status_indicator = BodyLabel("● 就绪")
        self.status_indicator.setStyleSheet("color: #28a745; font-weight: bold;")
        header_layout.addWidget(self.status_indicator)
        
        main_layout.addLayout(header_layout)
        
        # 主要内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)
        
        # 左侧：摄像头区域
        camera_section = ElevatedCardWidget()
        camera_section.setFixedWidth(600)
        camera_layout = QVBoxLayout(camera_section)
        camera_layout.setContentsMargins(20, 20, 20, 20)
        camera_layout.setSpacing(16)
        
        # 摄像头控制区域
        control_card = HeaderCardWidget()
        control_card.setTitle("摄像头控制")
        
        control_layout = QHBoxLayout()
        control_layout.setSpacing(20)
        
        # 摄像头选择
        camera_label = BodyLabel("摄像头:")
        camera_label.setStyleSheet("font-weight: bold;")
        self.camera_select = ComboBox()
        self.camera_select.setPlaceholderText("选择摄像头")
        self.camera_select.setMinimumWidth(200)
        

        
        # 操作按钮
        self.toggle_camera_btn = PrimaryPushButton("启动摄像头")
        self.toggle_camera_btn.setIcon(FluentIcon.PLAY)
        self.toggle_camera_btn.setFixedHeight(36)
        
        self.capture_btn = PushButton("拍照")
        self.capture_btn.setIcon(FluentIcon.CAMERA)
        self.capture_btn.setFixedHeight(36)
        self.capture_btn.setEnabled(False)
        
        control_layout.addWidget(camera_label)
        control_layout.addWidget(self.camera_select)

        control_layout.addStretch()
        control_layout.addWidget(self.toggle_camera_btn)
        control_layout.addWidget(self.capture_btn)
        
        control_card.viewLayout.addLayout(control_layout)
        main_layout.addWidget(control_card)

        # 摄像头预览区域
        preview_card = HeaderCardWidget()
        preview_card.setTitle("摄像头预览")
        
        # 预览容器
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.Shape.Box)
        preview_frame.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border: 2px solid rgba(0, 0, 0, 0.1);
                border-radius: 12px;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.camera_display = QLabel("等待摄像头启动...")
        self.camera_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_display.setMinimumSize(640, 480)
        self.camera_display.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)
        preview_layout.addWidget(self.camera_display)
        # 兼容旧方法引用
        self.camera_preview = self.camera_display
        preview_card.viewLayout.addWidget(preview_frame)
        main_layout.addWidget(preview_card)

        # 拍照结果预览区域
        result_card = HeaderCardWidget()
        result_card.setTitle("拍照结果")
        result_layout = QVBoxLayout()
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(8)
        self.preview_label = QLabel("点击拍摄按钮来捕获图像")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(320, 240)
        self.preview_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 16px;
                background: #f8f9fa;
                border: 1px dashed #cccccc;
                border-radius: 8px;
            }
        """)
        result_layout.addWidget(self.preview_label)
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.retake_btn = PushButton("重拍")
        self.retake_btn.setIcon(FluentIcon.SYNC)  # 替换为可用图标
        self.retake_btn.setEnabled(False)
        self.inference_btn = PrimaryPushButton("推理")
        self.inference_btn.setIcon(FluentIcon.ACCEPT_MEDIUM)
        self.inference_btn.setEnabled(False)
        btn_layout.addWidget(self.retake_btn)
        btn_layout.addWidget(self.inference_btn)
        btn_layout.addStretch()
        result_layout.addLayout(btn_layout)
        # 推理进度条
        from qfluentwidgets import ProgressBar
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        result_layout.addWidget(self.progress_bar)
        result_card.viewLayout.addLayout(result_layout)
        main_layout.addWidget(result_card)

        # 启动摄像头按钮兼容
        self.start_camera_btn = self.toggle_camera_btn

        # 模型选择下拉框（如有需要）
        self.model_select = ComboBox()
        self.model_select.setPlaceholderText("选择模型")
        self.model_select.setMinimumWidth(200)
        # 可根据需要将其添加到布局中

        # 设置滚动区域
        scroll.setWidget(main_widget)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        
        self.setObjectName("cameraView")

    def update_camera_list(self, camera_list):
        """更新可用摄像头列表"""
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
            self.status_indicator.setText("● 摄像头列表更新失败")
            self.status_indicator.setStyleSheet("color: #dc3545; font-weight: bold;")

    def update_model_list(self, model_list):
        """更新模型列表"""
        self.model_select.clear()
        for model in model_list:
            # 确保明确使用addItem的正确参数形式，避免将model误解为图标
            self.model_select.addItem(model)

    def update_camera_frame(self, frame):
        """更新摄像头预览帧"""
        try:
            if frame is not None:
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                q_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                if q_image.isNull():
                    return
                    
                pixmap = QPixmap.fromImage(q_image)
                if pixmap.isNull():
                    return
                    
                scaled_pixmap = pixmap.scaled(
                    self.camera_preview.width(), self.camera_preview.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.camera_preview.setPixmap(scaled_pixmap)
        except Exception as e:
            self.status_indicator.setText("● 摄像头预览更新失败")
            self.status_indicator.setStyleSheet("color: #dc3545; font-weight: bold;")
    
    def show_captured_image(self, image):
        """显示拍摄的图片"""
        try:
            self.captured_image = image
            if image is not None:
                h, w, ch = image.shape
                bytes_per_line = ch * w
                q_image = QImage(image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.width(), self.preview_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
                
                # 更新按钮状态
                self.retake_btn.setEnabled(True)
                self.inference_btn.setEnabled(True)
                self.capture_btn.setEnabled(False)
                self.capture_status = True
                self.status_indicator.setText("● 已拍摄，可以开始推理")
                self.status_indicator.setStyleSheet("color: #007bff; font-weight: bold;")
            else:
                self.status_indicator.setText("● 图像捕获失败")
                self.status_indicator.setStyleSheet("color: #dc3545; font-weight: bold;")
        except Exception as e:
            self.status_indicator.setText(f"● 显示图像出错: {str(e)}")
            self.status_indicator.setStyleSheet("color: #dc3545; font-weight: bold;")
    
    def clear_captured_image(self):
        """清除拍摄的图片"""
        self.captured_image = None
        self.preview_label.setText("点击拍摄按钮来捕获图像")
        self.preview_label.setPixmap(QPixmap())
        
        # 更新按钮状态
        self.retake_btn.setEnabled(False)
        self.inference_btn.setEnabled(False)
        self.capture_btn.setEnabled(True)
        self.capture_status = False
    
    def start_inference_progress(self):
        """开始推理进度显示"""
        self.progress_bar.setVisible(True)
        self.inference_btn.setEnabled(False)
        self.retake_btn.setEnabled(False)
        self.start_camera_btn.setEnabled(False)
        self.status_indicator.setText("● 正在推理中...")
        self.status_indicator.setStyleSheet("color: #ffc107; font-weight: bold;")
    
    def stop_inference_progress(self):
        """停止推理进度显示"""
        self.progress_bar.setVisible(False)
        self.inference_btn.setEnabled(True)
        self.retake_btn.setEnabled(True)
        self.start_camera_btn.setEnabled(True)
        self.status_indicator.setText("● 推理完成")
        self.status_indicator.setStyleSheet("color: #28a745; font-weight: bold;")
    
    def reset_ui(self):
        """重置界面状态"""
        self.clear_captured_image()
        self.camera_preview.setText("摄像头未启动")
        self.camera_preview.setPixmap(QPixmap())
        self.start_camera_btn.setText("启动摄像头")
        self.start_camera_btn.setIcon(FluentIcon.PLAY)
        self.start_camera_btn.setEnabled(True)
        self.camera_select.setEnabled(True)
        self.capture_btn.setEnabled(False)
        self.status_indicator.setText("● 就绪")
        self.status_indicator.setStyleSheet("color: #28a745; font-weight: bold;")
    
    def disable_camera_controls(self):
        """禁用所有摄像头控件，用于状态变更期间"""
        self.start_camera_btn.setEnabled(False)
        self.camera_select.setEnabled(False)
        self.capture_btn.setEnabled(False)
    
    def enable_camera_controls(self, camera_active=False):
        """启用摄像头控件"""
        self.start_camera_btn.setEnabled(True)
        self.camera_select.setEnabled(not camera_active)  # 摄像头活动时不允许切换
        self.capture_btn.setEnabled(camera_active)  # 只有摄像头启动时才能拍照

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QFrame)
from qfluentwidgets import (CardWidget, PushButton, ComboBox, FluentIcon, ProgressRing, 
                            HeaderCardWidget, TitleLabel, BodyLabel, CaptionLabel, 
                            ElevatedCardWidget, SmoothScrollArea)

import cv2
import numpy as np

from ml.detector import InferenceResult

"""
推理页面设计
- 功能区域：
    1. 模型选择：用户可以从已加载的模型中选择一个用于推理
    2. 图像选择：用户可以选择待检测的钢铁图像文件
    3. 推理结果展示：展示原始图像和标注后的图像对比
    4. 缺陷信息统计：显示检测到的缺陷类型和数量
"""

class InferenceView(QWidget):
    """
    推理界面视图类

    负责展示推理相关的UI元素，包括模型选择、图像选择、推理结果展示等
    """
    def __init__(self):
        """初始化推理视图组件和布局"""
        super().__init__()
        self.setObjectName("inference_view")
        self.progress_bar = None

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
        title = TitleLabel("图像推理")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)

        # 工具栏卡片
        self.toolbar_card = HeaderCardWidget("控制面板")
        toolbar_layout = QHBoxLayout()
        
        self.select_model_checkbox = ComboBox()
        self.select_model_checkbox.setPlaceholderText("选择模型")
        self.add_image_btn = PushButton(FluentIcon.FOLDER_ADD, '选择文件')
        
        toolbar_layout.addWidget(BodyLabel("模型:"))
        toolbar_layout.addWidget(self.select_model_checkbox)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.add_image_btn)
        
        self.toolbar_card.viewLayout.addLayout(toolbar_layout)
        main_layout.addWidget(self.toolbar_card)

        # 内容卡片
        content_card = HeaderCardWidget("推理结果")
        content_layout = QVBoxLayout()
        content_layout.setSpacing(24)

        # 图片预览区域
        preview_card = HeaderCardWidget("图像预览")
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(24)

        # 原始图像预览
        original_frame = QFrame()
        original_frame.setFrameStyle(QFrame.Shape.Box)
        original_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
            }
        """)
        original_layout = QVBoxLayout(original_frame)
        original_layout.setContentsMargins(0, 0, 0, 0)

        self.original_image = QLabel()
        self.original_image.setMinimumSize(400, 300)
        self.original_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        original_layout.addWidget(self.original_image)
        preview_layout.addWidget(original_frame)

        # 结果图像预览
        result_frame = QFrame()
        result_frame.setFrameStyle(QFrame.Shape.Box)
        result_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
            }
        """)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(0, 0, 0, 0)

        self.result_image = QLabel()
        self.result_image.setMinimumSize(400, 300)
        self.result_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        result_layout.addWidget(self.result_image)
        preview_layout.addWidget(result_frame)

        preview_card.viewLayout.addLayout(preview_layout)
        content_layout.addWidget(preview_card)

        # 缺陷信息区域
        defect_card = HeaderCardWidget("缺陷信息")
        defect_layout = QVBoxLayout()
        defect_layout.setSpacing(16)
        
        # 摘要信息
        summary_layout = QHBoxLayout()
        self.model_name_label = BodyLabel("使用模型: 无")
        self.defect_count_label = BodyLabel("缺陷总数: 0")
        summary_layout.addWidget(self.model_name_label)
        summary_layout.addWidget(self.defect_count_label)
        summary_layout.addStretch()
        defect_layout.addLayout(summary_layout)
        
        # 缺陷详情表格
        self.defect_table = QTableWidget(0, 2)
        self.defect_table.setHorizontalHeaderLabels(["缺陷类型", "数量"])
        header = self.defect_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        defect_layout.addWidget(self.defect_table)
        
        defect_card.viewLayout.addLayout(defect_layout)
        content_layout.addWidget(defect_card)
        
        content_card.viewLayout.addLayout(content_layout)
        main_layout.addWidget(content_card)

        # 设置滚动区域
        scroll.setWidget(main_widget)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def init_data(self, model_list):
        """
        初始化数据

        Args:
            model_list (list): 可用的模型名称列表
        """
        if not model_list:
            return

        self.select_model_checkbox.clear()
        self.select_model_checkbox.addItems(model_list)
        self.update()

    def start_progress(self):
        """添加并显示进度条"""
        if self.progress_bar:
            self.progress_bar.deleteLater()

        # 进度条
        self.progress_bar = ProgressRing()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedSize(50, 50)

        # 将进度条插入到工具栏卡片的布局中
        toolbar_layout = self.toolbar_card.layout()
        if toolbar_layout and isinstance(toolbar_layout, QHBoxLayout):
            toolbar_layout.insertWidget(2, self.progress_bar)

    def update_progress(self, value):
        """
        更新进度条值

        Args:
            value (int): 进度值，范围0-100
        """
        if self.progress_bar:
            try:
                value = max(0, min(100, value))  # 确保值在0-100之间
                self.progress_bar.setValue(value)
                self.update()
            except Exception as e:
                self.stop_progress()

    def stop_progress(self):
        """
        移除进度条
        """
        if self.progress_bar:
            toolbar_layout = self.toolbar_card.layout()
            if toolbar_layout:
                toolbar_layout.removeWidget(self.progress_bar)
            self.progress_bar.deleteLater()
            self.progress_bar = None
            self.update()

    def show_inference_images(self, result: InferenceResult):
        """
        显示推理前后的图像对比和缺陷信息
        
        Args:
            result (InferenceResult): 推理结果对象
        """
        if result is None:
            return

        # 将 numpy 数组转换为 QPixmap
        def to_pixmap(img, label):
            if img is None:
                return QPixmap()

            try:
                h, w, c = img.shape
                # 确保颜色空间正确：OpenCV的BGR格式需要转换为Qt的RGB格式
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                qimg = QImage(rgb_img.data, w, h, w * c, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                # 按 label 尺寸等比缩放
                scaled_pixmap = pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                return scaled_pixmap
            except Exception as e:
                return QPixmap()

        # 设置图片
        self.original_image.setPixmap(to_pixmap(result.original_image, self.original_image))
        self.result_image.setPixmap(to_pixmap(result.annotated_image, self.result_image))

        # 更新缺陷信息摘要
        self.model_name_label.setText(f"使用模型: {result.model_name or '无'}")
        self.defect_count_label.setText(f"缺陷总数: {result.defect_count or 0}")

        # 更新缺陷详情表格
        self.defect_table.setRowCount(0)
        if result.defect_ids and len(result.defect_ids) > 0:
            self.defect_table.setRowCount(len(result.defect_ids))
            for row, (defect_type, count) in enumerate(result.defect_ids.items()):
                self.defect_table.setItem(row, 0, QTableWidgetItem(str(defect_type)))
                if (result.model_name == "精细分析"):
                    proportion = result.metadata[row]['proportion'] if result.metadata else 0
                    self.defect_table.setItem(row, 1, QTableWidgetItem(f"缺陷占比：{(proportion * 100):.3f}%"))
                else:
                    self.defect_table.setItem(row, 1, QTableWidgetItem(str(count)))
        else:
            self.defect_table.setRowCount(1)
            self.defect_table.setItem(0, 0, QTableWidgetItem("无缺陷"))
            self.defect_table.setItem(0, 1, QTableWidgetItem("0"))










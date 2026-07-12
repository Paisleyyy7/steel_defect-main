from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout, QSplitter, QScrollArea, QWidget
from qfluentwidgets import CardWidget


class MessageBox(QDialog):
    def __init__(self, original_image : QImage, annotated_image : QImage, parent=None, defects=None):
        super().__init__(parent)
        self.setWindowTitle("图片详情")
        self.setGeometry(200, 200, 1000, 600)
        self.setMinimumSize(800, 400)

        main_layout = QHBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # 图片区域容器
        image_container = QWidget()
        image_layout = QHBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(10)

        # 原始图片卡片
        self.original_card = CardWidget()
        self.original_card.setFixedWidth(400)
        original_layout = QVBoxLayout()
        original_layout.setContentsMargins(10, 10, 10, 10)
        original_layout.setSpacing(5)
        original_layout.addWidget(QLabel("原始图片:"), 0, Qt.AlignmentFlag.AlignTop)
        self.original_image_label = QLabel()
        self.original_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        original_layout.addWidget(self.original_image_label, 1)
        self.original_card.setLayout(original_layout)

        # 标记后图片卡片
        self.annotated_card = CardWidget()
        self.annotated_card.setFixedWidth(400)
        annotated_layout = QVBoxLayout()
        annotated_layout.setContentsMargins(10, 10, 10, 10)
        annotated_layout.setSpacing(5)
        annotated_layout.addWidget(QLabel("标记后图片:"), 0, Qt.AlignmentFlag.AlignTop)
        self.annotated_image_label = QLabel()
        self.annotated_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        annotated_layout.addWidget(self.annotated_image_label, 1)
        self.annotated_card.setLayout(annotated_layout)

        image_layout.addWidget(self.original_card)
        image_layout.addWidget(self.annotated_card)

        # 缺陷信息区域
        defect_container = QWidget()
        defect_layout = QVBoxLayout(defect_container)
        defect_layout.setContentsMargins(10, 10, 10, 10)
        defect_layout.setSpacing(5)
        defect_layout.addWidget(QLabel("缺陷类型及数量:"), 0, Qt.AlignmentFlag.AlignTop)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(5)

        if defects:
            for defect in defects:
                label = QLabel(f"• {defect['defect_name']}: {defect['count']}")
                label.setWordWrap(True)
                scroll_layout.addWidget(label)
        else:
            no_defect_label = QLabel("无缺陷")
            no_defect_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_layout.addWidget(no_defect_label)

        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        defect_layout.addWidget(scroll_area)

        # 设置Splitter比例
        splitter.addWidget(image_container)
        splitter.addWidget(defect_container)
        splitter.setSizes([600, 200])

        self.set_images(original_image, annotated_image)

    def set_images(self, original_image : QImage, annotated_image : QImage):
        max_width = 380  # 调整为合理的显示尺寸
        max_height = 380
        self._set_pixmap(self.original_image_label, original_image, max_width, max_height)
        self._set_pixmap(self.annotated_image_label, annotated_image, max_width, max_height)

    def _set_pixmap(self, label, image_data : QImage, max_width, max_height):
        if image_data is None or image_data.isNull():
            label.setText("无图片")
            return

        # 直接从 QImage 转换为 QPixmap
        pixmap = QPixmap.fromImage(image_data)
        if pixmap.isNull():
            label.setText("无图片")
            return

        scaled_pixmap = pixmap.scaled(
            max_width, max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)
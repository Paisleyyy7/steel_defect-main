from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import PrimaryPushButton, PushButton, InfoBar, InfoBarPosition, CardWidget


class ConfirmDialog(QDialog):
    """
    确认对话框，用于确认用户操作。
    如是否保存推理结果到数据库等确认操作。
    """
    def __init__(self, title="确认", content="是否继续？", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 180)  # 增加高度以确保内容显示完整
        self.setMinimumSize(350, 150)  # 增加最小尺寸
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)  # 增加边距
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)  # 增加卡片内边距
        
        # 内容标签
        content_label = QLabel(content)
        content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("font-size: 14px;")  # 调整字体大小
        card_layout.addWidget(content_label)
        card_layout.addSpacing(15)  # 增加间距
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        
        # 取消按钮
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # 确认按钮
        self.confirm_btn = PrimaryPushButton("确认")
        self.confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.confirm_btn)
        
        card_layout.addLayout(button_layout)
        main_layout.addWidget(card)
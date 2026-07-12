# filepath: d:\Desktop\Project\steel_defect\app\views\billing_view.py
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QPushButton, QLabel, QFormLayout, QMessageBox, 
                             QHeaderView, QTableWidgetItem, QInputDialog, QApplication)
from PyQt6.QtGui import QColor
from qfluentwidgets import (CardWidget, InfoBar, InfoBarPosition, PrimaryPushButton, 
                            PushButton, LineEdit, ComboBox, DoubleSpinBox,
                            TableWidget, HeaderCardWidget, BodyLabel,
                            SmoothMode, ToolButton, StrongBodyLabel, FluentIcon)

from app.models.billing_model import BillingModel


class BillingView(QWidget):
    """计费管理视图"""
    
    # 系统固定的四种推理模型
    SYSTEM_MODELS = {
        '目标定位': '基于YOLOv11的目标检测模型，用于定位钢材表面缺陷',
        '精细分析': '基于UNet的语义分割模型，用于精细分析缺陷区域',
        '快速分类': '基于MobileNetV4的轻量级分类模型，快速检测常见缺陷',
        '复杂分类': '基于MobileNetV4的复杂分类模型，检测多种复杂缺陷类型'
    }
    
    # 信号定义
    user_create_requested = pyqtSignal(str, str, float)  # name, email, initial_balance
    user_update_requested = pyqtSignal(int, str, str)  # user_id, name, email
    user_delete_requested = pyqtSignal(int)  # user_id
    user_recharge_requested = pyqtSignal(int, float, str)  # user_id, amount, description
    user_token_regenerate_requested = pyqtSignal(int)  # user_id - 重新生成token信号
    pricing_update_requested = pyqtSignal(str, float, str)  # model_name, price, description
    page_changed_signal = pyqtSignal(int)
    page_size_changed_signal = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.setObjectName("billing_view")  
        self.billing_model = BillingModel()
        
        # 分页相关属性
        self.current_page = 1
        self.total_pages = 1
        self.page_sizes = [10, 20, 50, 100]  # 预设的每页显示数量选项
        self.page_size = 10  # 默认每页显示10条
        
        # 添加弹窗状态跟踪
        self.token_dialog = None
        
        self.setup_model_connections()
        self.init_ui()
        self.load_data()
        self.initialize_system_models()  # 初始化系统模型定价
        
        # 定时刷新数据
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_data)
        self.refresh_timer.start(30000)  # 30秒刷新一次

    def setup_model_connections(self):
        """设置模型信号连接"""
        self.billing_model.users_updated.connect(self.update_users_table)
        self.billing_model.pricing_updated.connect(self.update_pricing_table)
        self.billing_model.api_calls_updated.connect(self.update_api_calls_table)
        self.billing_model.statistics_updated.connect(self.update_statistics)
        self.billing_model.operation_success.connect(self.show_success_message)
        self.billing_model.operation_error.connect(self.show_error_message)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("计费管理系统")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
          # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 统计报告标签页 - 移到第一个
        self.stats_tab = self.create_stats_tab()
        self.tab_widget.addTab(self.stats_tab, "统计报告")
        
        # 用户管理标签页
        self.user_tab = self.create_user_tab()
        self.tab_widget.addTab(self.user_tab, "用户管理")
        
        # 模型定价标签页
        self.pricing_tab = self.create_pricing_tab()
        self.tab_widget.addTab(self.pricing_tab, "模型定价")
        
        # API调用记录标签页
        self.calls_tab = self.create_calls_tab()
        self.tab_widget.addTab(self.calls_tab, "调用记录")
        
        layout.addWidget(self.tab_widget)

    def create_user_tab(self):
        """创建用户管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 用户操作区域
        user_card = HeaderCardWidget("添加新用户")
        user_layout = QVBoxLayout()
        user_card.viewLayout.addLayout(user_layout)
        
        # 添加用户表单
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setSpacing(5)
        
        self.user_name_input = LineEdit()
        self.user_name_input.setPlaceholderText("请输入用户名")
        form_layout.addRow("用户名:", self.user_name_input)
        
        self.user_email_input = LineEdit()
        self.user_email_input.setPlaceholderText("请输入邮箱地址")
        form_layout.addRow("邮箱:", self.user_email_input)
        
        self.initial_balance_input = DoubleSpinBox()
        self.initial_balance_input.setRange(0, 10000)
        self.initial_balance_input.setDecimals(2)
        self.initial_balance_input.setSingleStep(10)
        self.initial_balance_input.setValue(0)
        form_layout.addRow("初始余额:", self.initial_balance_input)
        
        user_layout.addLayout(form_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 0)
        
        self.add_user_btn = PrimaryPushButton("添加用户")
        self.add_user_btn.setFixedWidth(120)
        self.add_user_btn.clicked.connect(self.add_user)
        button_layout.addWidget(self.add_user_btn)
        button_layout.addStretch()
        
        user_layout.addLayout(button_layout)
        layout.addWidget(user_card)
        
        # 用户表格
        table_card = HeaderCardWidget("用户列表")
        self.users_table = TableWidget()
        self.users_table.scrollDelagate.verticalSmoothScroll.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.users_table.setBorderRadius(8)
        self.users_table.setBorderVisible(True)
        self.users_table.setColumnCount(7)  # 增加token列
        self.users_table.setHorizontalHeaderLabels(["ID", "用户名", "邮箱", "余额", "Token", "创建时间", "操作"])
        header = self.users_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) 
        self.users_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.users_table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.users_table.setAlternatingRowColors(True)
        
        table_card.viewLayout.addWidget(self.users_table)
        layout.addWidget(table_card)
        
        # 分页控件
        pagination_card = HeaderCardWidget("分页控制")
        pagination_layout = QHBoxLayout()
        
        self.users_page_size_combo = ComboBox()
        self.users_page_size_combo.addItems([str(size) for size in self.page_sizes])
        self.users_page_size_combo.setCurrentText(str(self.page_size))
        self.users_page_size_combo.setFixedWidth(80)
        
        self.users_first_page_btn = PushButton("首页")
        self.users_prev_btn = ToolButton(FluentIcon.LEFT_ARROW)
        self.users_page_edit = LineEdit()
        self.users_page_edit.setFixedWidth(50)
        self.users_page_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.users_page_total_label = StrongBodyLabel('/ 1')
        self.users_next_btn = ToolButton(FluentIcon.RIGHT_ARROW)
        self.users_last_page_btn = PushButton("尾页")
        self.users_goto_btn = PushButton('跳转')
        
        pagination_layout.addWidget(BodyLabel('每页显示:'))
        pagination_layout.addWidget(self.users_page_size_combo)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.users_first_page_btn)
        pagination_layout.addWidget(self.users_prev_btn)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.users_page_edit)
        pagination_layout.addWidget(self.users_page_total_label)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.users_next_btn)
        pagination_layout.addWidget(self.users_last_page_btn)
        pagination_layout.addSpacing(20)
        pagination_layout.addWidget(self.users_goto_btn)
        pagination_layout.addStretch()
        
        pagination_card.viewLayout.addLayout(pagination_layout)
        layout.addWidget(pagination_card)
        
        # 绑定分页事件
        self.users_first_page_btn.clicked.connect(lambda: self.change_users_page(1))
        self.users_prev_btn.clicked.connect(self.prev_users_page)
        self.users_next_btn.clicked.connect(self.next_users_page)
        self.users_last_page_btn.clicked.connect(lambda: self.change_users_page(self.total_pages))
        self.users_goto_btn.clicked.connect(self.jump_to_users_page)
        self.users_page_size_combo.currentTextChanged.connect(
            lambda x: self.change_users_page_size(int(x))
        )
        
        return widget

    def create_pricing_tab(self):
        """创建模型定价标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        
        # 定价操作区域
        pricing_card = HeaderCardWidget("模型价格设置")
        pricing_layout = QVBoxLayout()
        pricing_card.viewLayout.addLayout(pricing_layout)
        
        # 模型选择和定价表单
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setSpacing(15)
        
        # 模型选择下拉框（只能从预设模型中选择）
        self.model_selector = ComboBox()
        self.model_selector.addItems(list(self.SYSTEM_MODELS.keys()))
        self.model_selector.currentTextChanged.connect(self.on_model_selected)
        form_layout.addRow("选择模型:", self.model_selector)
        
        self.model_price_input = DoubleSpinBox()
        self.model_price_input.setRange(0, 9999)
        self.model_price_input.setDecimals(4)
        self.model_price_input.setSuffix(" 元/次")
        form_layout.addRow("价格:", self.model_price_input)
        
        pricing_layout.addLayout(form_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 0)
        
        self.update_model_btn = PrimaryPushButton("更新价格")
        self.update_model_btn.setFixedWidth(120)
        self.update_model_btn.clicked.connect(self.update_model_pricing)
        button_layout.addWidget(self.update_model_btn)
        
        self.reset_default_btn = PushButton("恢复默认价格")
        self.reset_default_btn.setFixedWidth(120)
        self.reset_default_btn.clicked.connect(self.reset_default_pricing)
        button_layout.addWidget(self.reset_default_btn)
        
        button_layout.addStretch()
        pricing_layout.addLayout(button_layout)
        
        layout.addWidget(pricing_card)
        
        # 定价表格
        table_card = HeaderCardWidget("模型定价列表")
        self.pricing_table = TableWidget()
        self.pricing_table.scrollDelagate.verticalSmoothScroll.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.pricing_table.setBorderRadius(8)
        self.pricing_table.setBorderVisible(True)
        self.pricing_table.setColumnCount(5)
        self.pricing_table.setHorizontalHeaderLabels(["模型名称", "价格(元/次)", "描述", "状态", "更新时间"])
        header = self.pricing_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pricing_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.pricing_table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.pricing_table.setAlternatingRowColors(True)
        self.pricing_table.itemSelectionChanged.connect(self.on_pricing_selection_changed)
        
        table_card.viewLayout.addWidget(self.pricing_table)
        layout.addWidget(table_card)
        
        # 分页控件
        pagination_card = HeaderCardWidget("分页控制")
        pagination_layout = QHBoxLayout()
        
        self.pricing_page_size_combo = ComboBox()
        self.pricing_page_size_combo.addItems([str(size) for size in self.page_sizes])
        self.pricing_page_size_combo.setCurrentText(str(self.page_size))
        self.pricing_page_size_combo.setFixedWidth(80)
        
        self.pricing_first_page_btn = PushButton("首页")
        self.pricing_prev_btn = ToolButton(FluentIcon.LEFT_ARROW)
        self.pricing_page_edit = LineEdit()
        self.pricing_page_edit.setFixedWidth(50)
        self.pricing_page_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pricing_page_total_label = StrongBodyLabel('/ 1')
        self.pricing_next_btn = ToolButton(FluentIcon.RIGHT_ARROW)
        self.pricing_last_page_btn = PushButton("尾页")
        self.pricing_goto_btn = PushButton('跳转')
        
        pagination_layout.addWidget(BodyLabel('每页显示:'))
        pagination_layout.addWidget(self.pricing_page_size_combo)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.pricing_first_page_btn)
        pagination_layout.addWidget(self.pricing_prev_btn)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.pricing_page_edit)
        pagination_layout.addWidget(self.pricing_page_total_label)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.pricing_next_btn)
        pagination_layout.addWidget(self.pricing_last_page_btn)
        pagination_layout.addSpacing(20)
        pagination_layout.addWidget(self.pricing_goto_btn)
        pagination_layout.addStretch()
        
        pagination_card.viewLayout.addLayout(pagination_layout)
        layout.addWidget(pagination_card)
        
        # 绑定分页事件
        self.pricing_first_page_btn.clicked.connect(lambda: self.change_pricing_page(1))
        self.pricing_prev_btn.clicked.connect(self.prev_pricing_page)
        self.pricing_next_btn.clicked.connect(self.next_pricing_page)
        self.pricing_last_page_btn.clicked.connect(lambda: self.change_pricing_page(self.total_pages))
        self.pricing_goto_btn.clicked.connect(self.jump_to_pricing_page)
        self.pricing_page_size_combo.currentTextChanged.connect(
            lambda x: self.change_pricing_page_size(int(x))
        )
        
        return widget

    def create_calls_tab(self):
        """创建API调用记录标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 调用记录表格
        table_card = HeaderCardWidget("API调用记录")
        self.calls_table = TableWidget()
        self.calls_table.scrollDelagate.verticalSmoothScroll.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.calls_table.setBorderRadius(8)
        self.calls_table.setBorderVisible(True)
        self.calls_table.setColumnCount(7)
        self.calls_table.setHorizontalHeaderLabels(["调用ID", "用户", "模型", "费用", "调用时间", "状态", "描述"])
        header = self.calls_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.calls_table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.calls_table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.calls_table.setAlternatingRowColors(True)
        
        table_card.viewLayout.addWidget(self.calls_table)
        layout.addWidget(table_card)
        
        # 分页控件
        pagination_card = HeaderCardWidget("分页控制")
        pagination_layout = QHBoxLayout()
        
        self.calls_page_size_combo = ComboBox()
        self.calls_page_size_combo.addItems([str(size) for size in self.page_sizes])
        self.calls_page_size_combo.setCurrentText(str(self.page_size))
        self.calls_page_size_combo.setFixedWidth(80)
        
        self.calls_first_page_btn = PushButton("首页")
        self.calls_prev_btn = ToolButton(FluentIcon.LEFT_ARROW)
        self.calls_page_edit = LineEdit()
        self.calls_page_edit.setFixedWidth(50)
        self.calls_page_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.calls_page_total_label = StrongBodyLabel('/ 1')
        self.calls_next_btn = ToolButton(FluentIcon.RIGHT_ARROW)
        self.calls_last_page_btn = PushButton("尾页")
        self.calls_goto_btn = PushButton('跳转')
        
        pagination_layout.addWidget(BodyLabel('每页显示:'))
        pagination_layout.addWidget(self.calls_page_size_combo)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.calls_first_page_btn)
        pagination_layout.addWidget(self.calls_prev_btn)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.calls_page_edit)
        pagination_layout.addWidget(self.calls_page_total_label)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.calls_next_btn)
        pagination_layout.addWidget(self.calls_last_page_btn)
        pagination_layout.addSpacing(20)
        pagination_layout.addWidget(self.calls_goto_btn)
        pagination_layout.addStretch()
        
        pagination_card.viewLayout.addLayout(pagination_layout)
        layout.addWidget(pagination_card)
        
        # 绑定分页事件
        self.calls_first_page_btn.clicked.connect(lambda: self.change_calls_page(1))
        self.calls_prev_btn.clicked.connect(self.prev_calls_page)
        self.calls_next_btn.clicked.connect(self.next_calls_page)
        self.calls_last_page_btn.clicked.connect(lambda: self.change_calls_page(self.total_pages))
        self.calls_goto_btn.clicked.connect(self.jump_to_calls_page)
        self.calls_page_size_combo.currentTextChanged.connect(
            lambda x: self.change_calls_page_size(int(x))
        )
        
        return widget

    def create_stats_tab(self):
        """创建统计报告标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(30)
        
        # 添加垂直间距，使内容居中
        layout.addStretch()
        
        # 统计卡片容器
        cards_layout = QHBoxLayout()
        cards_layout.addStretch()  # 左侧弹性空间
        
        # 总用户数卡片
        self.total_users_card = CardWidget()
        self.total_users_card.setFixedSize(220, 140)
        total_users_layout = QVBoxLayout(self.total_users_card)
        total_users_layout.setContentsMargins(15, 15, 15, 15)
        total_users_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_users_label = QLabel("总用户数")
        self.total_users_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_users_label.setStyleSheet("font-size: 16px; color: #666666; margin-bottom: 8px;")
        self.total_users_value = QLabel("0")
        self.total_users_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_users_value.setStyleSheet("font-size: 36px; font-weight: bold; color: #0078d4;")
        total_users_layout.addWidget(self.total_users_label)
        total_users_layout.addWidget(self.total_users_value)
        cards_layout.addWidget(self.total_users_card)
        
        # 添加卡片之间的间距
        cards_layout.addSpacing(30)
        
        # 总调用次数卡片
        self.total_calls_card = CardWidget()
        self.total_calls_card.setFixedSize(220, 140)
        total_calls_layout = QVBoxLayout(self.total_calls_card)
        total_calls_layout.setContentsMargins(15, 15, 15, 15)
        total_calls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_calls_label = QLabel("总调用次数")
        self.total_calls_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_calls_label.setStyleSheet("font-size: 16px; color: #666666; margin-bottom: 8px;")
        self.total_calls_value = QLabel("0")
        self.total_calls_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_calls_value.setStyleSheet("font-size: 36px; font-weight: bold; color: #107c10;")
        total_calls_layout.addWidget(self.total_calls_label)
        total_calls_layout.addWidget(self.total_calls_value)
        cards_layout.addWidget(self.total_calls_card)
        
        # 添加卡片之间的间距
        cards_layout.addSpacing(30)
        
        # 总收入卡片
        self.total_revenue_card = CardWidget()
        self.total_revenue_card.setFixedSize(220, 140)
        total_revenue_layout = QVBoxLayout(self.total_revenue_card)
        total_revenue_layout.setContentsMargins(15, 15, 15, 15)
        total_revenue_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_revenue_label = QLabel("总收入")
        self.total_revenue_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_revenue_label.setStyleSheet("font-size: 16px; color: #666666; margin-bottom: 8px;")
        self.total_revenue_value = QLabel("0.00 元")
        self.total_revenue_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_revenue_value.setStyleSheet("font-size: 36px; font-weight: bold; color: #d83b01;")
        total_revenue_layout.addWidget(self.total_revenue_label)
        total_revenue_layout.addWidget(self.total_revenue_value)
        cards_layout.addWidget(self.total_revenue_card)
        
        cards_layout.addStretch()  # 右侧弹性空间
        layout.addLayout(cards_layout)
        
        # 添加垂直间距，使内容居中
        layout.addStretch()
        return widget

    def load_data(self):
        """加载所有数据"""
        self.billing_model.load_all_users()
        self.billing_model.load_model_pricing(page=self.current_page, page_size=self.page_size)
        self.billing_model.load_api_calls(page=self.current_page, page_size=self.page_size)
        self.billing_model.load_statistics()

    def refresh_users(self):
        """刷新用户数据"""
        self.billing_model.load_all_users()

    def refresh_pricing(self):
        """刷新定价数据"""
        self.billing_model.load_model_pricing(page=self.current_page, page_size=self.page_size)

    def refresh_calls(self):
        """刷新API调用记录数据"""
        self.billing_model.load_api_calls(page=self.current_page, page_size=self.page_size)
        self.billing_model.load_statistics()

    def update_users_table(self, users):
        """更新用户表格"""
        # 断开旧的信号连接
        try:
            self.users_table.itemDoubleClicked.disconnect()
        except:
            pass
            
        total = len(users)
        
        # 计算总页数
        self.total_pages = (total + self.page_size - 1) // self.page_size if total > 0 else 1
        
        # 确保当前页在有效范围内
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        
        # 计算当前页的数据范围
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total)
        current_page_users = users[start_idx:end_idx]
        
        # 更新表格数据
        self.users_table.setRowCount(len(current_page_users))
        
        for row, user in enumerate(current_page_users):
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user['id'])))
            self.users_table.setItem(row, 1, QTableWidgetItem(user['name']))
            self.users_table.setItem(row, 2, QTableWidgetItem(user['email'] or ""))
            self.users_table.setItem(row, 3, QTableWidgetItem(f"{user['balance']:.2f}"))
            
            # Token列 - 显示前8位，其余用*代替，双击可查看详情
            token = user.get('token', '')
            masked_token = token[:8] + '*' * (len(token) - 8) if len(token) > 8 else token
            token_item = QTableWidgetItem(masked_token)
            token_item.setToolTip(token)  # 存储完整token在tooltip中
            self.users_table.setItem(row, 4, token_item)
            self.users_table.setItem(row, 5, QTableWidgetItem(user['created_at']))
            
            # 操作按钮
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(5, 5, 5, 5)
            
            recharge_btn = QPushButton("充值")
            recharge_btn.clicked.connect(lambda checked, uid=user['id']: self.recharge_user(uid))
            button_layout.addWidget(recharge_btn)
            
            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, uid=user['id']: self.delete_user(uid))
            button_layout.addWidget(delete_btn)
            
            # Token管理按钮
            token_btn = QPushButton("重置Token")
            token_btn.clicked.connect(lambda checked, uid=user['id']: self.regenerate_user_token(uid))
            button_layout.addWidget(token_btn)
            
            copy_token_btn = QPushButton("复制Token")
            copy_token_btn.clicked.connect(lambda checked, token=token: self.copy_token_to_clipboard(token))
            button_layout.addWidget(copy_token_btn)
            
            view_token_btn = QPushButton("查看Token")
            view_token_btn.clicked.connect(lambda checked, uid=user['id'], name=user['name'], token=token: self.show_token_details(uid, name, token))
            button_layout.addWidget(view_token_btn)
            
            self.users_table.setCellWidget(row, 6, button_widget)
        
        # 重新连接双击事件
        self.users_table.itemDoubleClicked.connect(self.on_user_table_double_click)
        
        # 更新分页控件状态
        self.update_users_pagination()
    
    def update_users_pagination(self):
        """更新用户表格分页控件状态"""
        self.users_page_edit.setText(str(self.current_page))
        self.users_page_total_label.setText(f'/ {self.total_pages}')
        
        # 更新按钮状态
        self.users_first_page_btn.setEnabled(self.current_page > 1)
        self.users_prev_btn.setEnabled(self.current_page > 1)
        self.users_next_btn.setEnabled(self.current_page < self.total_pages)
        self.users_last_page_btn.setEnabled(self.current_page < self.total_pages)
    
    def change_users_page(self, page):
        """切换到指定页码"""
        if 1 <= page <= self.total_pages and page != self.current_page:
            self.current_page = page
            self.billing_model.load_all_users()
    
    def prev_users_page(self):
        """切换到上一页"""
        if self.current_page > 1:
            self.change_users_page(self.current_page - 1)
    
    def next_users_page(self):
        """切换到下一页"""
        if self.current_page < self.total_pages:
            self.change_users_page(self.current_page + 1)
    
    def jump_to_users_page(self):
        """跳转到指定页面"""
        try:
            page = int(self.users_page_edit.text())
            if 1 <= page <= self.total_pages:
                self.change_users_page(page)
            else:
                self.users_page_edit.setText(str(self.current_page))
        except ValueError:
            self.users_page_edit.setText(str(self.current_page))
    
    def change_users_page_size(self, page_size):
        """更改每页显示数量"""
        if page_size != self.page_size:
            self.page_size = page_size
            self.current_page = 1  # 重置为第一页
            self.billing_model.load_all_users()

    def update_pricing_table(self, pricing_list):
        """更新模型定价表格"""
        total = len(pricing_list)
        
        # 计算总页数
        self.total_pages = (total + self.page_size - 1) // self.page_size if total > 0 else 1
        
        # 确保当前页在有效范围内
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        
        # 计算当前页的数据范围
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total)
        current_page_pricing = pricing_list[start_idx:end_idx]
        
        self.pricing_table.setRowCount(len(self.SYSTEM_MODELS))
        
        # 创建价格映射
        price_map = {p['model_name']: p for p in pricing_list}
        
        for row, (model_name, description) in enumerate(self.SYSTEM_MODELS.items()):
            self.pricing_table.setItem(row, 0, QTableWidgetItem(model_name))
            
            if model_name in price_map:
                pricing_info = price_map[model_name]
                self.pricing_table.setItem(row, 1, QTableWidgetItem(f"{pricing_info['price']:.4f}"))
                self.pricing_table.setItem(row, 2, QTableWidgetItem(description))
                self.pricing_table.setItem(row, 3, QTableWidgetItem("已配置"))
                self.pricing_table.setItem(row, 4, QTableWidgetItem(pricing_info.get('updated_at', pricing_info.get('created_at', ''))))
            else:
                self.pricing_table.setItem(row, 1, QTableWidgetItem("未设置"))
                self.pricing_table.setItem(row, 2, QTableWidgetItem(description))
                self.pricing_table.setItem(row, 3, QTableWidgetItem("待配置"))
                self.pricing_table.setItem(row, 4, QTableWidgetItem(""))
                
                # 设置未配置项的样式
                for col in range(5):
                    item = self.pricing_table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 245, 245))  # 浅红色背景
        
        # 更新分页控件状态
        self.update_pricing_pagination()
    
    def update_pricing_pagination(self):
        """更新定价表格分页控件状态"""
        self.pricing_page_edit.setText(str(self.current_page))
        self.pricing_page_total_label.setText(f'/ {self.total_pages}')
        
        # 更新按钮状态
        self.pricing_first_page_btn.setEnabled(self.current_page > 1)
        self.pricing_prev_btn.setEnabled(self.current_page > 1)
        self.pricing_next_btn.setEnabled(self.current_page < self.total_pages)
        self.pricing_last_page_btn.setEnabled(self.current_page < self.total_pages)
    
    def change_pricing_page(self, page):
        """切换到指定页码"""
        if 1 <= page <= self.total_pages and page != self.current_page:
            self.current_page = page
            self.billing_model.load_model_pricing(page=self.current_page, page_size=self.page_size)
    
    def prev_pricing_page(self):
        """切换到上一页"""
        if self.current_page > 1:
            self.change_pricing_page(self.current_page - 1)
    
    def next_pricing_page(self):
        """切换到下一页"""
        if self.current_page < self.total_pages:
            self.change_pricing_page(self.current_page + 1)
    
    def jump_to_pricing_page(self):
        """跳转到指定页面"""
        try:
            page = int(self.pricing_page_edit.text())
            if 1 <= page <= self.total_pages:
                self.change_pricing_page(page)
            else:
                self.pricing_page_edit.setText(str(self.current_page))
        except ValueError:
            self.pricing_page_edit.setText(str(self.current_page))
    
    def change_pricing_page_size(self, page_size):
        """更改每页显示数量"""
        if page_size != self.page_size:
            self.page_size = page_size
            self.current_page = 1  # 重置为第一页
            self.billing_model.load_model_pricing(page=self.current_page, page_size=self.page_size)

    def update_api_calls_table(self, calls_list):
        """更新API调用记录表格"""
        total = len(calls_list)
        
        # 计算总页数
        self.total_pages = (total + self.page_size - 1) // self.page_size if total > 0 else 1
        
        # 确保当前页在有效范围内
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        
        # 计算当前页的数据范围
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total)
        current_page_calls = calls_list[start_idx:end_idx]
        
        # 更新表格数据
        self.calls_table.setRowCount(len(current_page_calls))
        
        for row, call in enumerate(current_page_calls):
            self.calls_table.setItem(row, 0, QTableWidgetItem(str(call['id'])))
            self.calls_table.setItem(row, 1, QTableWidgetItem(call.get('user_name', 'Unknown')))
            self.calls_table.setItem(row, 2, QTableWidgetItem(call['model_name']))
            self.calls_table.setItem(row, 3, QTableWidgetItem(f"{call['cost']:.4f}"))
            self.calls_table.setItem(row, 4, QTableWidgetItem(call['created_at']))
            self.calls_table.setItem(row, 5, QTableWidgetItem(call.get('status', 'success')))
            self.calls_table.setItem(row, 6, QTableWidgetItem(call.get('description', '')))
            
            # 根据状态设置行颜色
            status = call.get('status', 'success')
            if status == 'success':
                for j in range(self.calls_table.columnCount()):
                    item = self.calls_table.item(row, j)
                    if item:
                        item.setBackground(QColor(240, 255, 240))  # 浅绿色
            elif status == 'failed':
                for j in range(self.calls_table.columnCount()):
                    item = self.calls_table.item(row, j)
                    if item:
                        item.setBackground(QColor(255, 240, 240))  # 浅红色
        
        # 更新分页控件状态
        self.update_calls_pagination()
    
    def update_calls_pagination(self):
        """更新API调用记录分页控件状态"""
        self.calls_page_edit.setText(str(self.current_page))
        self.calls_page_total_label.setText(f'/ {self.total_pages}')
        
        # 更新按钮状态
        self.calls_first_page_btn.setEnabled(self.current_page > 1)
        self.calls_prev_btn.setEnabled(self.current_page > 1)
        self.calls_next_btn.setEnabled(self.current_page < self.total_pages)
        self.calls_last_page_btn.setEnabled(self.current_page < self.total_pages)
    
    def change_calls_page(self, page):
        """切换到指定页码"""
        if 1 <= page <= self.total_pages and page != self.current_page:
            self.current_page = page
            self.billing_model.load_api_calls(page=self.current_page, page_size=self.page_size)
    
    def prev_calls_page(self):
        """切换到上一页"""
        if self.current_page > 1:
            self.change_calls_page(self.current_page - 1)
    
    def next_calls_page(self):
        """切换到下一页"""
        if self.current_page < self.total_pages:
            self.change_calls_page(self.current_page + 1)
    
    def jump_to_calls_page(self):
        """跳转到指定页面"""
        try:
            page = int(self.calls_page_edit.text())
            if 1 <= page <= self.total_pages:
                self.change_calls_page(page)
            else:
                self.calls_page_edit.setText(str(self.current_page))
        except ValueError:
            self.calls_page_edit.setText(str(self.current_page))
    
    def change_calls_page_size(self, page_size):
        """更改每页显示数量"""
        if page_size != self.page_size:
            self.page_size = page_size
            self.current_page = 1  # 重置为第一页
            self.billing_model.load_api_calls(page=self.current_page, page_size=self.page_size)

    def update_statistics(self, stats):
        """更新统计数据"""
        self.total_users_value.setText(str(stats.get('total_users', 0)))
        self.total_calls_value.setText(str(stats.get('total_calls', 0)))
        self.total_revenue_value.setText(f"{stats.get('total_revenue', 0):.2f} 元")

    def initialize_system_models(self):
        """初始化系统模型定价（如果不存在）"""
        self.billing_model.initialize_system_models(self.SYSTEM_MODELS)

    def on_model_selected(self, model_name):
        """模型选择变化时的处理"""
        # 自动填充当前模型的价格
        current_row = self.pricing_table.currentRow()
        if current_row >= 0:
            price_item = self.pricing_table.item(current_row, 1)
            if price_item and price_item.text() != "未设置":
                try:
                    price = float(price_item.text())
                    self.model_price_input.setValue(price)
                except ValueError:
                    self.model_price_input.setValue(0.0)

    def on_pricing_selection_changed(self):
        """定价表格选择变化时的处理"""
        current_row = self.pricing_table.currentRow()
        if current_row >= 0:
            # 获取选中行的模型名称和价格
            model_item = self.pricing_table.item(current_row, 0)
            price_item = self.pricing_table.item(current_row, 1)
            
            if model_item and price_item:
                model_name = model_item.text()
                
                # 更新模型选择器
                index = self.model_selector.findText(model_name)
                if index >= 0:
                    self.model_selector.setCurrentIndex(index)
                
                # 更新价格输入框
                if price_item.text() != "未设置":
                    try:
                        price = float(price_item.text())
                        self.model_price_input.setValue(price)
                    except ValueError:
                        self.model_price_input.setValue(0.0)
                else:
                    self.model_price_input.setValue(0.0)

    def update_model_pricing(self):
        """更新模型定价"""
        model_name = self.model_selector.currentText()
        price = self.model_price_input.value()
        description = self.SYSTEM_MODELS.get(model_name, "")
        
        if price <= 0:
            self.show_validation_error("价格必须大于0")
            return
        
        self.billing_model.update_model_pricing(model_name, price, description)

    def reset_default_pricing(self):
        """恢复默认价格"""
        # 默认价格设置
        default_prices = {
            '目标定位': 0.1000,
            '精细分析': 0.2000,
            '快速分类': 0.0500,
            '复杂分类': 0.1500
        }
        
        reply = QMessageBox.question(
            self, "确认重置", "确定要将所有模型价格重置为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for model_name, price in default_prices.items():
                description = self.SYSTEM_MODELS.get(model_name, "")
                self.billing_model.update_model_pricing(model_name, price, description)

    def add_user(self):
        """添加用户"""
        name = self.user_name_input.text().strip()
        email = self.user_email_input.text().strip()
        balance = self.initial_balance_input.value()
        
        if not name:
            self.show_validation_error("请输入用户名")
            return
        
        self.billing_model.create_user(name, email, balance)
        
        # 清空输入框
        self.user_name_input.clear()
        self.user_email_input.clear()
        self.initial_balance_input.setValue(0)

    def recharge_user(self, user_id):
        """用户充值"""
        amount, ok = QInputDialog.getDouble(
            self, "用户充值", "请输入充值金额:", 
            min=0.01, max=99999.99, decimals=2
        )
        
        if ok and amount > 0:
            self.billing_model.recharge_user(user_id, amount, "管理员充值")

    def delete_user(self, user_id):
        """删除用户"""
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这个用户吗？\n此操作无法撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.billing_model.delete_user(user_id)

    def regenerate_user_token(self, user_id):
        """重新生成用户Token"""
        reply = QMessageBox.question(
            self, "确认重新生成", 
            "确定要重新生成用户Token吗？\n旧的Token将失效，请确保告知用户新的Token！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.billing_model.regenerate_user_token(user_id)

    def copy_token_to_clipboard(self, token):
        """复制Token到剪贴板"""
        if token:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(token)
                self.show_success_message(f"Token已复制到剪贴板")
            else:
                self.show_validation_error("无法访问剪贴板")
        else:
            self.show_validation_error("Token为空，无法复制")

    def show_token_details(self, user_id, user_name, token):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
        
        # 如果已经有弹窗，先关闭它
        if self.token_dialog:
            self.token_dialog.close()
            
        self.token_dialog = QDialog(self)
        self.token_dialog.setWindowTitle(f"用户 {user_name} 的Token详情")
        self.token_dialog.setModal(True)
        self.token_dialog.resize(500, 300)
        
        layout = QVBoxLayout(self.token_dialog)
        
        # 用户信息
        user_info = QLabel(f"用户: {user_name} (ID: {user_id})")
        user_info.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(user_info)
        
        # Token显示区域
        token_label = QLabel("Token:")
        layout.addWidget(token_label)
        
        token_text = QTextEdit()
        token_text.setPlainText(token)
        token_text.setMaximumHeight(80)
        token_text.setReadOnly(True)
        layout.addWidget(token_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("复制Token")
        copy_btn.clicked.connect(lambda: self.copy_token_to_clipboard(token))
        button_layout.addWidget(copy_btn)
        
        regenerate_btn = QPushButton("重新生成Token")
        regenerate_btn.clicked.connect(lambda: self.regenerate_and_close(user_id, self.token_dialog))
        button_layout.addWidget(regenerate_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.token_dialog.close)
        button_layout.addWidget(close_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 连接对话框关闭信号
        self.token_dialog.finished.connect(self.on_token_dialog_closed)
        
        self.token_dialog.exec()

    def regenerate_and_close(self, user_id, dialog):
        """重新生成Token并关闭对话框"""
        reply = QMessageBox.question(
            dialog, "确认重新生成", 
            "确定要重新生成Token吗？\n旧的Token将失效！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.billing_model.regenerate_user_token(user_id)
            dialog.close()

    def on_token_dialog_closed(self):
        """处理Token详情对话框关闭事件"""
        self.token_dialog = None

    def on_user_table_double_click(self, item):
        """处理用户表格双击事件"""
        if item.column() == 4:  # Token列
            # 如果已经有弹窗打开，则不再打开新的
            if self.token_dialog and self.token_dialog.isVisible():
                return
                
            row = item.row()
            user_id_item = self.users_table.item(row, 0)
            user_name_item = self.users_table.item(row, 1)
            
            if user_id_item and user_name_item:
                try:
                    user_id = int(user_id_item.text())
                    user_name = user_name_item.text()
                    
                    # 获取当前行的token数据
                    token_item = self.users_table.item(row, 4)
                    if token_item and token_item.toolTip():
                        token = token_item.toolTip()
                        self.show_token_details(user_id, user_name, token)
                    else:
                        self.show_validation_error("无法获取Token信息")
                    
                except ValueError:
                    self.show_validation_error("无法获取用户信息")

    def show_success_message(self, message):
        """显示成功消息"""
        InfoBar.success(
            title='成功',
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def show_error_message(self, message):
        """显示错误消息"""
        InfoBar.error(
            title='错误',
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def show_validation_error(self, message):
        """显示验证错误消息"""
        InfoBar.warning(
            title='验证错误',
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

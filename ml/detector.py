import os
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from numpy import ndarray

from ultralytics import YOLO
from torch import nn
import torch
import cv2
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2
import torch.nn.functional as F
import timm
from torchvision import transforms
from PIL import Image

# 导入资源路径处理函数
try:
    from main import get_resource_path
except ImportError:
    # 如果无法导入，提供一个默认实现
    def get_resource_path(relative_path):
        try:
            # 使用hasattr检查_MEIPASS属性是否存在
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS # type: ignore
                print(f"[DEBUG] 使用PyInstaller打包路径: {base_path}")
            else:
                base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
                print(f"[DEBUG] 使用正常运行路径: {base_path}")
        except Exception as e:
            base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            print(f"[DEBUG] 路径解析异常: {e}, 使用默认路径: {base_path}")
        return os.path.join(base_path, relative_path)


class Detector:
    # 模型类型常量定义
    MODEL_YOLO = '目标定位'
    MODEL_UNET = '精细分析'
    MODEL_FAST = '快速分类'
    MODEL_COMPLEX = '复杂分类'

    def __init__(self):
        """初始化检测器，加载所有模型"""
        print(f"[INFO] 初始化钢铁缺陷检测器...")

        # 设置资源路径
        self.base_path = Path(os.path.dirname(__file__)).parent
        # 使用资源路径函数获取模型目录
        self.model_path = Path(get_resource_path('resources/model'))
        
        # 检查模型目录是否存在
        if not self.model_path.exists():
            print(f"[ERROR] 模型目录不存在: {self.model_path}")
            raise FileNotFoundError(f"模型目录不存在: {self.model_path}")

        # 设置设备
        self.device = self._get_device()
        print(f"[INFO] 使用设备: {self.device}")
        
        # 初始化分类映射
        self._init_class_mappings()
        
        # 初始化模型列表
        self.model_list = [self.MODEL_YOLO, self.MODEL_UNET, self.MODEL_FAST, self.MODEL_COMPLEX]
        self.models = {}
        
        # 加载所有模型
        self._load_models()
        print(f"[INFO] 所有模型加载完成")

    def _get_device(self) -> torch.device:
        """获取设备，优先使用GPU"""
        if torch.cuda.is_available():
            try:
                device = torch.device('cuda')
                # 测试CUDA是否正常工作
                torch.zeros(1).to(device)
                print(f"[INFO] GPU可用: {torch.cuda.get_device_name(0)}")
                return device
            except Exception as e:
                print(f"[WARNING] GPU虽然可用但发生错误: {e}，将使用CPU")
                return torch.device('cpu')
        return torch.device('cpu')
        
    def _init_class_mappings(self):
        """初始化类别映射"""
        # UNet模型的类别名称
        self.unet_class_names = {
            1: '夹杂物',
            2: '补丁',
            3: '划痕',
            4: '其他缺陷',
        }
        
        # YOLO模型类别映射
        self.yolo_class_map = {
            'class-1': '夹杂物',
            'class-2': '补丁',
            'class-3': '划痕',
            'class-4': '其他缺陷',
        }
        
        # 所有缺陷类型ID映射
        self.defect_ids = {
            1: '夹杂物',
            2: '补丁',
            3: '划痕',
            4: '其他缺陷',
            5: '裂纹',
            7: '斑点',
            8: '麻面',
            9: '轧入氧化皮',
        }
        
        # 快速分类模型标签映射
        self.fast_label_mapping = {
            0: 5,  # 裂纹
            1: 8,  # 麻面
            2: 7,  # 斑点
            3: 9,  # 轧入氧化皮
            4: 3,  # 划痕
            5: 1,  # 夹杂物
            6: 0   # 无缺陷
        }

    def _load_models(self):
        """加载所有模型"""
        try:
            # 加载YOLOv11模型
            yolo_path = self.model_path / 'YOLOv11.pt'
            if not yolo_path.exists():
                print(f"[WARNING] YOLO模型文件不存在: {yolo_path}")
            else:
                print(f"[INFO] 正在加载YOLO模型: {yolo_path}")
                self.models[self.MODEL_YOLO] = YOLO(str(yolo_path))
            
            # 加载UNet模型
            unet_path = self.model_path / 'unet.pth'
            if not unet_path.exists():
                print(f"[WARNING] UNet模型文件不存在: {unet_path}")
            else:
                print(f"[INFO] 正在加载UNet模型: {unet_path}")
                self.models[self.MODEL_UNET] = UNet(n_channels=3, n_classes=5)
                # 使用map_location确保即使没有GPU也能加载模型
                self.models[self.MODEL_UNET].load_state_dict(
                    torch.load(str(unet_path), map_location=self.device))
                self.models[self.MODEL_UNET].to(self.device)
                self.models[self.MODEL_UNET].eval()
            
            # 加载MobileNetV4模型(快速分类)
            mobilenet1_path = self.model_path / 'mobilenetv4_1.pth'
            if not mobilenet1_path.exists():
                print(f"[WARNING] MobileNetV4模型文件不存在: {mobilenet1_path}")
            else:
                print(f"[INFO] 正在加载快速分类模型: {mobilenet1_path}")
                try:
                    self.models[self.MODEL_FAST] = timm.create_model('mobilenetv4_conv_large.e600_r384_in1k', pretrained=False)
                    self.models[self.MODEL_FAST].classifier = nn.Linear(self.models[self.MODEL_FAST].classifier.in_features, 7)
                    self.models[self.MODEL_FAST].load_state_dict(
                        torch.load(str(mobilenet1_path), map_location=self.device))
                    self.models[self.MODEL_FAST].to(self.device)
                    self.models[self.MODEL_FAST].eval()
                except Exception as e:
                    print(f"[ERROR] 加载快速分类模型时出错: {e}")
            
            # 加载MobileNetV4模型(复杂分类)
            mobilenet2_path = self.model_path / 'mobilenetv4_2.pth'
            if not mobilenet2_path.exists():
                print(f"[WARNING] MobileNetV4复杂分类模型文件不存在: {mobilenet2_path}")
            else:
                print(f"[INFO] 正在加载复杂分类模型: {mobilenet2_path}")
                try:
                    self.models[self.MODEL_COMPLEX] = timm.create_model('mobilenetv4_conv_large.e600_r384_in1k', pretrained=False)
                    self.models[self.MODEL_COMPLEX].classifier = nn.Linear(self.models[self.MODEL_COMPLEX].classifier.in_features, 4)
                    self.models[self.MODEL_COMPLEX].load_state_dict(
                        torch.load(str(mobilenet2_path), map_location=self.device))
                    self.models[self.MODEL_COMPLEX].to(self.device)
                    self.models[self.MODEL_COMPLEX].eval()
                except Exception as e:
                    print(f"[ERROR] 加载复杂分类模型时出错: {e}")
        
        except Exception as e:
            print(f"[ERROR] 加载模型时发生错误: {e}")
            raise

    # 传入模型名称和图片，返回推理结果
    def detect(self, model_name: str, img: np.ndarray) -> 'InferenceResult':
        """
        使用指定模型对图像进行推理
        
        Args:
            model_name: 模型名称，必须是self.model_list中的一个
            img: 输入图像，必须是BGR格式的numpy数组
            
        Returns:
            InferenceResult: 推理结果对象
            
        Raises:
            ValueError: 如果模型名称不存在或图像格式不正确
        """
        if img is None or not isinstance(img, np.ndarray):
            print(f"[ERROR] 输入图像无效，必须是numpy数组")
            raise ValueError("输入图像无效，必须是numpy数组")
            
        if len(img.shape) != 3 or img.shape[2] != 3:
            print(f"[ERROR] 输入图像必须是3通道彩色图像，当前形状: {img.shape}")
            raise ValueError(f"输入图像必须是3通道彩色图像，当前形状: {img.shape}")
        
        # 检查模型是否存在
        model = self.models.get(model_name)
        if not model:
            print(f"[ERROR] 模型 '{model_name}' 不存在或未加载")
            raise ValueError(f"模型 '{model_name}' 不存在或未加载")
        
        print(f"[INFO] 使用 '{model_name}' 模型开始推理...")
        
        try:
            # 根据不同模型的输入要求，进行处理
            if model_name == self.MODEL_FAST:
                return self._detect_fast_classification(model, img)
            elif model_name == self.MODEL_COMPLEX:
                return self._detect_complex_classification(model, img)
            elif model_name == self.MODEL_YOLO:
                return self._detect_yolo(model, img)
            elif model_name == self.MODEL_UNET:
                return self._detect_unet(model, img)
            else:
                print(f"[ERROR] 未知模型类型: {model_name}")
                raise ValueError(f"未知模型类型: {model_name}")
        except Exception as e:
            print(f"[ERROR] 推理过程中发生错误: {e}")
            raise

    def _detect_fast_classification(self, model, img: np.ndarray) -> 'InferenceResult':
        """快速分类模型的推理方法"""
        print(f"[INFO] 执行快速分类推理...")
        try:
            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Resize((334, 334)),
            ])
            original_img = img
            img_tensor = transform(img).unsqueeze(0).to(self.device)
            
            start_time = time.time()
            with torch.no_grad():
                outputs = model(img_tensor)
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 获取预测类别
            _, predicted = torch.max(outputs, 1)
            predicted_label = int(predicted.item())
            
            # 处理预测结果
            if predicted_label == 6:  # 无缺陷
                defect_count = 0
                defect_ids = {}
            else:
                final_label = self.fast_label_mapping[predicted_label]
                defect_name = self.defect_ids.get(final_label, '未知缺陷')
                defect_ids = {defect_name: 1}
                defect_count = 1
            
            print(f"[INFO] 快速分类完成，处理时间: {processing_time:.4f}秒, 检测到缺陷: {defect_count}个")
            
            return InferenceResult(
                model_name=self.MODEL_FAST,
                defect_count=defect_count,
                defect_ids=defect_ids,
                original_image=original_img,
                annotated_image=None,
                metadata={
                    "processing_time": processing_time,
                    "raw_output": outputs.cpu().squeeze().tolist()
                }
            )
        except Exception as e:
            print(f"[ERROR] 快速分类推理失败: {e}")
            raise

    def _detect_complex_classification(self, model, img: np.ndarray) -> 'InferenceResult':
        """复杂分类模型的推理方法"""
        print(f"[INFO] 执行复杂分类推理...")
        try:
            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Resize((334, 334)),
            ])
            input_tensor = transform(img).unsqueeze(0).to(self.device)
            original_img = img
            
            start_time = time.time()
            with torch.no_grad():
                output = model(input_tensor)
                prob = torch.sigmoid(output)
                predicted = (prob >= 0.43).float().squeeze(0)
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 统计缺陷信息
            defect_indices = torch.nonzero(predicted).cpu().squeeze()
            if defect_indices.ndim == 0 and defect_indices.nelement() > 0:
                defect_indices = [defect_indices.item()]
            elif defect_indices.ndim > 0:
                defect_indices = defect_indices.tolist()
            else:
                defect_indices = []
            
            # 将类别标签从 0-3 转换为 1-4
            defect_ids = {self.defect_ids.get(int(idx) + 1, '未知缺陷'): 1 for idx in defect_indices}
            
            print(f"[INFO] 复杂分类完成，处理时间: {processing_time:.4f}秒, 检测到缺陷: {len(defect_indices)}个")
            
            return InferenceResult(
                model_name=self.MODEL_COMPLEX,
                defect_count=len(defect_indices),
                defect_ids=defect_ids,
                original_image=original_img,
                annotated_image=None,
                metadata={
                    "processing_time": processing_time,
                    "raw_output": prob.cpu().squeeze().tolist()
                }
            )
        except Exception as e:
            print(f"[ERROR] 复杂分类推理失败: {e}")
            raise

    def _detect_yolo(self, model, img: np.ndarray) -> 'InferenceResult':
        """YOLO目标检测模型的推理方法"""
        print(f"[INFO] 执行YOLO目标检测推理...")
        try:
            start_time = time.time()
            results = model.predict(img)
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 结果处理
            if not results or len(results) == 0:
                print(f"[WARNING] YOLO未返回有效结果")
                return InferenceResult(
                    model_name=self.MODEL_YOLO,
                    defect_count=0,
                    defect_ids={},
                    original_image=img,
                    annotated_image=img.copy(),
                    metadata={"processing_time": processing_time}
                )
            
            result = results[0]
            names = result.names
            boxes = result.boxes
            
            if boxes is None or len(boxes) == 0:
                print(f"[INFO] YOLO未检测到任何目标")
                return InferenceResult(
                    model_name=self.MODEL_YOLO,
                    defect_count=0,
                    defect_ids={},
                    original_image=img,
                    annotated_image=img.copy(),
                    metadata={"processing_time": processing_time}
                )
            
            xyxy = boxes.xyxy.cpu().tolist()
            conf = boxes.conf.cpu().tolist()
            cls = boxes.cls.cpu().tolist()
            
            # 获取标注后的图片
            annotated_image = result.plot()
            
            # 处理元数据和缺陷统计
            metadata = []
            defect_ids = {}
            
            for i in range(len(xyxy)):
                x1, y1, x2, y2 = xyxy[i]
                confidence = conf[i]
                class_id = int(cls[i])
                class_name_raw = names[class_id]
                class_name = self.yolo_class_map.get(class_name_raw, class_name_raw)
                
                metadata.append({
                    'box': [x1, y1, x2, y2],
                    'confidence': confidence,
                    'class_id': class_id,
                    'class_name': class_name
                })
                
                defect_ids[class_name] = defect_ids.get(class_name, 0) + 1
            
            defect_count = len(xyxy)
            metadata.append({"processing_time": processing_time})
            
            print(f"[INFO] YOLO检测完成，处理时间: {processing_time:.4f}秒, 检测到缺陷: {defect_count}个")
            
            return InferenceResult(
                model_name=self.MODEL_YOLO,
                defect_count=defect_count,
                defect_ids=defect_ids,
                original_image=img,
                annotated_image=annotated_image,
                metadata=metadata
            )
        except Exception as e:
            print(f"[ERROR] YOLO推理失败: {e}")
            raise

    def _detect_unet(self, model, img: np.ndarray) -> 'InferenceResult':
        """UNet语义分割模型的推理方法"""
        print(f"[INFO] 执行UNet语义分割推理...")
        try:
            # 转换BGR到RGB
            frame_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 数据预处理
            transform = A.Compose([
                A.Resize(height=128, width=800),
                A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
                ToTensorV2(),
            ])
            
            transformed = transform(image=frame_rgb)
            input_tensor = transformed['image'].unsqueeze(0).to(self.device)
            
            # 模型推理
            start_time = time.time()
            with torch.no_grad():
                output = model(input_tensor)
            end_time = time.time()
            processing_time = end_time - start_time
            
            pred_mask = output.argmax(dim=1).squeeze().cpu().numpy()
            
            # 准备标注图像
            annotated_image = frame_rgb.copy()
            colors = [
                (0, 0, 0),       # 背景（黑色）
                (255, 0, 0),     # 疵点（蓝色）
                (0, 255, 0),     # 划痕（绿色）
                (0, 0, 255),     # 白色划痕（红色）
                (255, 255, 255)  # 大面积黑色凸起（白色）
            ]
            
            h, w = pred_mask.shape
            overlay = np.zeros((h, w, 3), dtype=np.uint8)
            
            for cls_id in range(1, 5):
                mask = pred_mask == cls_id
                if np.any(mask):
                    overlay[mask] = colors[cls_id]
            
            # 调整尺寸匹配原图
            original_height, original_width = img.shape[:2]
            overlay = cv2.resize(overlay, (original_width, original_height), interpolation=cv2.INTER_NEAREST)
            annotated_image = cv2.resize(annotated_image, (original_width, original_height))
            
            # 转换回BGR并添加叠加层
            annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
            opacity = 0.5
            cv2.addWeighted(overlay, opacity, annotated_image, 1 - opacity, 0, annotated_image)
            
            # 准备元数据
            metadata = []
            unique_classes = np.unique(pred_mask)
            defect_ids = {}
            total_pixels = pred_mask.size
            
            for cls_id in unique_classes:
                if cls_id == 0:  # 跳过背景
                    continue
                    
                class_mask = pred_mask == cls_id
                class_name = self.unet_class_names.get(cls_id, f'未知_{cls_id}')
                
                # 获取掩码的坐标
                try:
                    y, x = np.where(class_mask)
                    if len(y) == 0 or len(x) == 0:
                        continue
                        
                    y_min, y_max = min(y), max(y)
                    x_min, x_max = min(x), max(x)

                    pixel_count = int(np.sum(class_mask))
                    proportion = pixel_count / total_pixels  
                    
                    metadata.append({
                        'class_id': int(cls_id),
                        'class_name': class_name,
                        'bbox': [x_min, y_min, x_max, y_max],
                        'pixel_count': int(np.sum(class_mask)),
                        'proportion': proportion  # 占比
                    })
                    
                    defect_ids[class_name] = defect_ids.get(class_name, 0) + 1
                except Exception as e:
                    print(f"[WARNING] 处理类别 {cls_id} 时出错: {e}")
            
            defect_count = len(metadata)
            metadata.append({"processing_time": processing_time})
            
            print(f"[INFO] UNet分割完成，处理时间: {processing_time:.4f}秒, 检测到缺陷: {defect_count}个")
            
            return InferenceResult(
                model_name=self.MODEL_UNET,
                defect_count=defect_count,
                defect_ids=defect_ids,
                original_image=img,
                annotated_image=annotated_image,
                metadata=metadata
            )
        except Exception as e:
            print(f"[ERROR] UNet推理失败: {e}")
            raise


class InferenceResult:
    """推理结果类，用于存储模型推理的结果"""

    def __init__(self, 
                 model_name: str, 
                 original_image: np.ndarray, 
                 defect_count: int, 
                 defect_ids: dict, 
                 annotated_image: Optional[np.ndarray] = None, 
                 metadata: Optional[Any] = None):
        """
        初始化推理结果对象
        
        Args:
            model_name: 模型名称
            original_image: 原始图像(BGR格式)
            defect_count: 缺陷总数
            defect_ids: 缺陷ID字典，键为缺陷名称，值为缺陷数量
            annotated_image: 标注后的图像(BGR格式)，可选
            metadata: 元数据，可选，模型特定信息
        """
        self.model_name: str = model_name
        self.original_image: np.ndarray = original_image
        self.defect_count: int = defect_count
        self.defect_ids: Dict[str, int] = defect_ids
        self.annotated_image: Optional[np.ndarray] = annotated_image
        self.metadata = metadata

    def __str__(self) -> str:
        """返回推理结果的字符串表示"""
        return (f"InferenceResult(model={self.model_name}, "
                f"defect_count={self.defect_count}, "
                f"defects={list(self.defect_ids.keys()) if self.defect_ids else 'None'})")


class UNet(nn.Module):
    """UNet模型实现，用于语义分割"""

    def __init__(self, n_channels, n_classes, bilinear=True):
        super(UNet, self).__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear

        self.inc = DoubleConv(n_channels, 64)
        self.down1 = Down(64, 128)
        self.down2 = Down(128, 256)
        self.down3 = Down(256, 512)
        factor = 2 if bilinear else 1
        self.down4 = Down(512, 1024 // factor)
        self.up1 = Up(1024, 512 // factor, bilinear)
        self.up2 = Up(512, 256 // factor, bilinear)
        self.up3 = Up(256, 128 // factor, bilinear)
        self.up4 = Up(128, 64, bilinear)
        self.outc = OutConv(64, n_classes)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)
        return logits


class DoubleConv(nn.Module):
    """(convolution => [BN] => ReLU) * 2"""

    def __init__(self, in_channels, out_channels, mid_channels=None):
        super().__init__()
        if not mid_channels:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)


class Down(nn.Module):
    """Downscaling with maxpool then double conv"""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels)
        )

    def forward(self, x):
        return self.maxpool_conv(x)


class Up(nn.Module):
    """Upscaling then double conv"""

    def __init__(self, in_channels, out_channels, bilinear=True):
        super().__init__()

        # if bilinear, use the normal convolutions to reduce the number of channels
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)
        else:
            self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]

        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2,
                        diffY // 2, diffY - diffY // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class OutConv(nn.Module):
    """输出卷积层"""
    
    def __init__(self, in_channels, out_channels):
        super(OutConv, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x):
        return self.conv(x)


def classify(outputs, threshold=0.5):
    """
    分类函数，应用softmax并根据阈值确定类别
    
    Args:
        outputs: 模型输出的logits
        threshold: 置信度阈值，低于此值被视为"无缺陷"
        
    Returns:
        int: 预测的类别标签
    """
    probabilities = torch.softmax(outputs, dim=1)
    max_prob, predicted = torch.max(probabilities, 1)
    predicted_label = predicted.item()

    if max_prob < threshold:
        return 6  # 无缺陷
    return predicted_label




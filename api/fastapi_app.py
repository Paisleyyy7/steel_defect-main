import json
import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Header
from typing import Optional

from app.models.database.defect_dao import DefectDAO
from app.models.database.inference_dao import InferenceDAO
from app.models.database.user_dao import UserDAO
from app.models.database.billing_dao import BillingDAO
from app.models.event_bus import EventBus
from ml.detector import Detector

app = FastAPI(title="钢材缺陷检测API", description="支持计费和用户认证的钢材缺陷检测服务")

inference_dao = InferenceDAO()
defect_dao = DefectDAO()
user_dao = UserDAO()
billing_dao = BillingDAO()
detector = Detector()

# 允许的图片格式
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png']


@app.get("/")
async def root():
    """
    获取API服务基本信息
    
    **接口说明：** 返回API服务的基本信息，用于确认服务是否正常运行
    
    **请求方式：** GET
    
    **请求URL：** /
    
    **请求参数：** 无
    
    **成功响应示例：**
    ```json
    {
        "message": "钢材缺陷检测API服务"
    }
    ```
    """
    return {"message": "钢材缺陷检测API服务"}


@app.get("/health")
async def health_check():
    """
    健康检查
    
    **接口说明：** 检查API服务的健康状态，用于监控和负载均衡器
    
    **请求方式：** GET
    
    **请求URL：** /health
    
    **请求参数：** 无
    
    **成功响应示例：**
    ```json
    {
        "status": "healthy"
    }
    ```
    """
    return {"status": "healthy"}


# 获取所有推理结果，支持分页
@app.get("/inference_results")
async def get_requests(page: int = 1, page_size: int = 10):
    """
    获取所有推理结果（支持分页）
    
    **接口说明：** 分页获取所有推理结果的列表，包括基本信息和缺陷统计
    
    **请求方式：** GET
    
    **请求URL：** /inference_results
    
    **Query参数：**
    | 参数名 | 类型 | 必填 | 默认值 | 说明 |
    |--------|------|------|--------|------|
    | page | int | 否 | 1 | 页码，从1开始 |
    | page_size | int | 否 | 10 | 每页记录数，建议不超过100 |
    
    **请求示例：**
    ```
    GET /inference_results?page=1&page_size=10
    ```
    
    **成功响应示例：**
    ```json
    {
        "total": 150,
        "results": [
            {
                "id": 1,
                "defect_count": 3,
                "created_at": "2025-01-01T10:30:00",
                "defects": [
                    {"defect_name": "裂纹", "count": 2},
                    {"defect_name": "划痕", "count": 1}
                ]
            },
            {
                "id": 2,
                "defect_count": 0,
                "created_at": "2025-01-01T11:15:00",
                "defects": []
            }
        ]
    }
    ```
    """
    total, results = inference_dao.fetch_inference_results_by_page(page, page_size)
    return {"total": total, "results": results}


# 通过 ID 获取推理结果
@app.get("/inference_results/{inference_id}")
async def get_request_by_id(inference_id: int):
    """
    通过ID获取推理结果详情
    
    **接口说明：** 根据推理结果ID获取详细信息，包括原始图像、标注图像和所有缺陷信息
    
    **请求方式：** GET
    
    **请求URL：** /inference_results/{inference_id}
    
    **Path参数：**
    | 参数名 | 类型 | 必填 | 说明 |
    |--------|------|------|------|
    | inference_id | int | 是 | 推理结果的唯一标识符 |
    
    **请求示例：**
    ```
    GET /inference_results/123
    ```
    
    **成功响应示例：**
    ```json
    {
        "id": 123,
        "defect_count": 5,
        "created_at": "2025-01-01T14:22:00",
        "original_image": "base64编码的原始图像数据",
        "annotated_image": "base64编码的标注图像数据",
        "defects": [
            {
                "defect_name": "裂纹",
                "count": 3,
                "severity": "高"
            },
            {
                "defect_name": "划痕", 
                "count": 2,
                "severity": "中"
            }
        ]
    }
    ```
    
    **错误响应示例：**
    ```json
    {
        "detail": "Inference result not found"
    }
    ```
    """
    return inference_dao.get_inference_result_by_id(inference_id)


# 提交一张或者多张图片文件进行推理，指定模型名称
@app.post("/inference")
async def inference_request(
    model_name: str = Form(...),
    files: list[UploadFile] = File(...),
    authorization: Optional[str] = Header(None)
):
    """
    钢材缺陷检测推理接口
    
    **接口说明：** 上传一张或多张钢材图片，使用指定的AI模型进行缺陷检测，返回检测结果和计费信息
    
    **请求方式：** POST
    
    **请求URL：** /inference
    
    **Content-Type：** multipart/form-data
    
    **Headers参数：**
    | 参数名 | 类型 | 必填 | 说明 |
    |--------|------|------|------|
    | Authorization | string | 是 | 用户认证令牌，支持Bearer token格式 |
    
    **Body参数（form-data）：**
    | 参数名 | 类型 | 必填 | 说明 |
    |--------|------|------|------|
    | model_name | string | 是 | 检测模型名称，支持：YOLOv11、mobilenetv4_1、mobilenetv4_2、unet |
    | files | file[] | 是 | 图片文件列表，支持JPEG和PNG格式 |
    
    **请求示例：**
    ```
    POST /inference
    Content-Type: multipart/form-data
    Authorization: Bearer abc123token456
    
    form-data:
    - model_name: YOLOv11
    - files: [选择图片文件]
    ```
    
    **成功响应示例：**
    ```json
    {
        "message": "推理完成",
        "cost": 2.5,
        "remaining_balance": 97.5,
        "processed_images": 1
    }
    ```
    
    **错误响应示例：**
    
    **缺少认证头（401）：**
    ```json
    {
        "detail": "Missing authorization header"
    }
    ```
    
    **无效令牌（401）：**
    ```json
    {
        "detail": "Invalid token"
    }
    ```
    
    **余额不足（402）：**
    ```json
    {
        "detail": "Insufficient balance. Current: 1.5, Required: 5.0"
    }
    ```
    
    **不支持的文件格式（400）：**
    ```json
    {
        "detail": "不支持的文件类型: image/gif。只支持 JPEG 和 PNG 格式。"
    }
    ```
    
    **未知模型（400）：**
    ```json
    {
        "detail": "Unknown model: invalid_model_name"
    }
    ```
    
    **支持的模型列表：**
    - `YOLOv11`: 高精度目标检测模型
    - `mobilenetv4_1`: 轻量级快速检测模型
    - `mobilenetv4_2`: 移动端优化模型  
    - `unet`: 语义分割模型
    
    **计费说明：**
    - 每张图片按模型定价单独计费
    - 推理成功后自动扣除费用
    - 推理失败时自动退款
    - 余额不足时拒绝请求
    
    **注意事项：**
    - 支持的图片格式：JPEG (.jpg, .jpeg), PNG (.png)
    - 单次请求最大文件数量：建议不超过 10 张
    - 图片大小限制：建议单张不超过 10MB
    - 认证令牌支持 Bearer 格式或直接传递
    """
    # 验证token
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # 支持 Bearer token 格式
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    
    user = user_dao.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 检查模型价格
    price_per_call = billing_dao.get_model_price(model_name)
    if price_per_call is None:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
    
    total_cost = price_per_call * len(files)
    
    # 检查余额
    if user['balance'] < total_cost:
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient balance. Current: {user['balance']}, Required: {total_cost}"
        )
    
    # 验证文件格式
    for file in files:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file.content_type}。只支持 JPEG 和 PNG 格式。"
            )

    images = []
    for file in files:
        # 读取上传的文件内容
        contents = await file.read()
        # 将文件内容转换为 numpy 数组
        nparr = np.frombuffer(contents, np.uint8)
        # 解码图像
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(
                status_code=400,
                detail=f"无法解码图像文件: {file.filename}"
            )
        images.append(image)

    results = []
    inference_result_ids = []
    balance_deducted = False
    
    try:
        # 执行推理
        for image in images:
            results.append(detector.detect(model_name, image))

        # 扣除费用
        if not user_dao.deduct_balance(user['id'], total_cost):
            raise HTTPException(status_code=402, detail="Failed to deduct balance")
        balance_deducted = True

        # 保存推理结果
        for result in results:
            # 1. 保存推理结果基本信息到 inference_results 表
            # 将原始图像和标注图像转换为 bytes
            original_image_bytes = cv2.imencode('.jpg', result.original_image)[1].tobytes()
            annotated_image_bytes = cv2.imencode('.jpg', result.annotated_image)[1].tobytes() if result.annotated_image is not None else None

            inference_result_id = inference_dao.add_inference_result(
                defect_count=result.defect_count,
                original_image=original_image_bytes,
                annotated_image=annotated_image_bytes
            )
            inference_result_ids.append(inference_result_id)
            print(f"  成功保存推理结果基本信息，ID: {inference_result_id}")

            # 2. 保存缺陷计数信息到 defect_counts 表
            for defect_name, count in result.defect_ids.items():
                defect_dao.add_defect_count(
                    inference_result_id=inference_result_id,
                    defect_name=defect_name,
                    count=count
                )
                print(f"    成功保存缺陷计数信息，缺陷名称: {defect_name}, 数量: {count}")
        
        # 记录API调用计费信息
        for i, inference_result_id in enumerate(inference_result_ids):
            billing_dao.record_api_call(
                user_id=user['id'],
                token=token,
                endpoint='/inference',
                model_name=model_name,
                cost=price_per_call,
                status='success'
            )
        
        # 发送数据更新信号
        EventBus.get_instance().inference_data_saved.emit()
        EventBus.get_instance().message_notification.emit('API上传成功', f"成功上传了{len(files)}张图片，花费: {total_cost}元")

    except Exception as e:
        # 如果出错且已扣费，则返还费用
        if balance_deducted:
            user_dao.add_balance(user['id'], total_cost, "推理失败退款")
        raise HTTPException(status_code=500, detail=f"推理过程出错: {str(e)}")

    # 获取更新后的用户余额
    updated_user = user_dao.get_user_by_token(token)
    remaining_balance = updated_user['balance'] if updated_user else 0

    return {
        "message": "推理完成",
        "cost": total_cost,
        "remaining_balance": remaining_balance,
        "processed_images": len(files)
    }


if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000, reload=True)

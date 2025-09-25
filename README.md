# ODCR本地管理工具

Amazon EC2 On-Demand Capacity Reservation (ODCR) 本地自动化管理工具，支持智能拆分购买和实时进度显示。

## 🔗 相关项目
- **AWS托管版本**: [ODCR-AWS-Serverless](https://github.com/lcwang/ODCR-AWS-Serverless) - 基于Step Functions和Lambda的企业级解决方案

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置AWS凭证
```bash
aws configure
```

### 3. 运行工具
```bash
# 创建10台r7i.metal-24xl实例
python odcr_manager.py create --instance-type r7i.metal-24xl --availability-zone us-west-2a --count 10

# 创建20台m5.large实例，超时30分钟
python odcr_manager.py create --instance-type m5.large --availability-zone us-west-2a --count 20 --timeout 30

# 扩容现有ODCR，增加10台实例
python odcr_manager.py expand --odcr-id cr-xxxxxxxxx --count 10

# 扩容现有ODCR，增加20台实例，超时30分钟
python odcr_manager.py expand --odcr-id cr-xxxxxxxxx --count 20 --timeout 30
```

## 核心特性

- ✅ **双模式操作**: 支持创建新ODCR和扩容现有ODCR
- ✅ **智能扩容**: 优先扩容现有ODCR，最小化ODCR数量
- ✅ **拆分购买**: 容量不足时自动降级重试 (10→5→2→1)
- ✅ **实时进度**: 动态显示执行状态和倒计时
- ✅ **状态更新**: 每30秒显示详细进度报告
- ✅ **优雅中断**: 支持Ctrl+C中断执行

## 参数说明

### create 命令
- `--instance-type`: 实例类型 (必需)
- `--availability-zone`: 可用区 (必需)  
- `--count`: 目标实例数量 (必需)
- `--preference`: 容量偏好 (open/targeted, 默认open)
- `--timeout`: 超时时间分钟数 (默认60)
- `--region`: AWS区域 (默认us-west-2)

### expand 命令
- `--odcr-id`: 要扩容的ODCR ID (必需)
- `--count`: 增加的实例数量 (必需)
- `--timeout`: 超时时间分钟数 (默认60)
- `--region`: AWS区域 (默认us-west-2)

## 工作原理

### 创建新ODCR模式
1. **首次购买**: 创建新ODCR
2. **后续购买**: 优先扩容最后一个ODCR
3. **扩容失败**: 尝试创建新ODCR
4. **拆分购买**: 容量不足时自动减半重试
5. **持续重试**: 直到达到目标或超时

### 扩容现有ODCR模式
1. **获取当前容量**: 查询ODCR当前状态
2. **尝试扩容**: 按目标数量增加容量
3. **拆分购买**: 容量不足时自动减半重试
4. **持续重试**: 直到达到目标或超时

详细文档请查看 `使用指南.md`

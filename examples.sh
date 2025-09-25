#!/bin/bash
# ODCR管理工具使用示例

echo "=== ODCR本地管理工具使用示例 ==="

# 1. 基本用法 - 创建少量实例
echo "1. 创建5台t3.micro实例 (通常容量充足)"
python odcr_manager.py create --instance-type t3.micro --availability-zone us-west-2a --count 5 --timeout 5

echo -e "\n" 

# 2. 中等规模 - 测试拆分购买
echo "2. 创建10台m5.large实例 (可能需要拆分购买)"
python odcr_manager.py create --instance-type m5.large --availability-zone us-west-2a --count 10 --timeout 10

echo -e "\n"

# 3. 大规模部署 - 完整拆分购买流程
echo "3. 创建20台c5.xlarge实例 (演示完整拆分购买)"
python odcr_manager.py create --instance-type c5.xlarge --availability-zone us-west-2a --count 20 --timeout 15

echo -e "\n"

# 4. 扩容现有ODCR - 需要提供真实的ODCR ID
echo "4. 扩容现有ODCR (请替换为真实的ODCR ID)"
echo "python odcr_manager.py expand --odcr-id cr-xxxxxxxxx --count 5 --timeout 10"

echo -e "\n"

# 5. 不同区域测试
echo "5. 在不同区域创建实例"
python odcr_manager.py create --instance-type m5.large --availability-zone us-west-2b --count 5 --region us-west-2 --timeout 5

echo -e "\n=== 示例执行完成 ==="

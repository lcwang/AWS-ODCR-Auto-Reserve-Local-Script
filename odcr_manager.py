#!/usr/bin/env python3
"""
ODCR本地管理工具 - 优先扩容现有ODCR，实时进度显示
"""

import boto3
import json
import time
import argparse
import sys
from datetime import datetime, timedelta

class ODCRManager:
    def __init__(self, region: str = 'us-west-2'):
        self.ec2 = boto3.client('ec2', region_name=region)
        self.region = region
    
    def print_status(self, current_purchased: int, target_count: int, created_odcrs: list, elapsed: timedelta):
        """实时打印状态"""
        progress_pct = (current_purchased / target_count) * 100 if target_count > 0 else 0
        print(f"\r📊 进度: {current_purchased}/{target_count} ({progress_pct:.1f}%) | "
              f"ODCR数量: {len(created_odcrs)} | "
              f"运行时间: {str(elapsed).split('.')[0]}", end='', flush=True)
    
    def try_expand_existing_odcr(self, odcr_id: str, additional_count: int) -> bool:
        """尝试扩容现有ODCR"""
        try:
            # 获取当前容量
            response = self.ec2.describe_capacity_reservations(CapacityReservationIds=[odcr_id])
            current_capacity = response['CapacityReservations'][0]['TotalInstanceCount']
            new_capacity = current_capacity + additional_count
            
            # 尝试修改容量
            self.ec2.modify_capacity_reservation(
                CapacityReservationId=odcr_id,
                InstanceCount=new_capacity
            )
            return True
        except Exception as e:
            if 'InsufficientCapacity' in str(e) or 'InsufficientInstanceCapacity' in str(e):
                return False
            else:
                raise e
    
    def create_new_odcr(self, instance_type: str, availability_zone: str, 
                       instance_count: int, capacity_preference: str = 'open') -> str:
        """创建新ODCR"""
        response = self.ec2.create_capacity_reservation(
            InstanceType=instance_type,
            InstancePlatform='Linux/UNIX',
            AvailabilityZone=availability_zone,
            InstanceCount=instance_count,
            EbsOptimized=True,
            Tenancy='default',
            EndDateType='unlimited',
            InstanceMatchCriteria=capacity_preference
        )
        return response['CapacityReservation']['CapacityReservationId']
    
    def create_odcr_with_split_purchase(self, instance_type: str, availability_zone: str, 
                                      target_count: int, capacity_preference: str = 'open',
                                      timeout_minutes: int = 60):
        """创建ODCR，优先扩容现有ODCR，支持拆分购买"""
        print(f"🎯 目标: 创建 {target_count} 台 {instance_type} 实例在 {availability_zone}")
        print(f"⏰ 超时设置: {timeout_minutes} 分钟")
        print("=" * 60)
        
        start_time = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)
        last_status_time = start_time
        
        current_purchased = 0
        current_attempt_size = target_count
        created_odcrs = []
        attempt_count_total = 0
        
        while current_purchased < target_count and datetime.now() - start_time < timeout:
            elapsed = datetime.now() - start_time
            
            # 每30秒显示一次详细状态
            if datetime.now() - last_status_time >= timedelta(seconds=30):
                print(f"\n⏱️  运行状态更新 ({str(elapsed).split('.')[0]}):")
                print(f"   📈 当前进度: {current_purchased}/{target_count} 台")
                print(f"   🔄 总尝试次数: {attempt_count_total}")
                print(f"   📋 ODCR列表: {len(created_odcrs)}")
                for i, odcr in enumerate(created_odcrs, 1):
                    print(f"      {i}. {odcr['odcr_id']} ({odcr['current_capacity']}台)")
                last_status_time = datetime.now()
            
            remaining_count = target_count - current_purchased
            attempt_count = min(current_attempt_size, remaining_count)
            attempt_count_total += 1
            
            # 如果已有ODCR，优先尝试扩容最后一个
            if created_odcrs:
                last_odcr = created_odcrs[-1]
                print(f"\n🔄 第{attempt_count_total}次尝试: 扩容ODCR {last_odcr['odcr_id']} +{attempt_count}台")
                self.print_status(current_purchased, target_count, created_odcrs, elapsed)
                
                try:
                    if self.try_expand_existing_odcr(last_odcr['odcr_id'], attempt_count):
                        # 扩容成功
                        current_purchased += attempt_count
                        last_odcr['current_capacity'] += attempt_count
                        
                        print(f"\n✅ 扩容成功! ODCR {last_odcr['odcr_id']} 现有 {last_odcr['current_capacity']} 台")
                        self.print_status(current_purchased, target_count, created_odcrs, elapsed)
                        
                        # 成功后重置尝试大小
                        if current_purchased < target_count:
                            current_attempt_size = target_count - current_purchased
                            print(f"\n⏳ 等待30秒后继续...")
                            
                            for i in range(30, 0, -1):
                                elapsed = datetime.now() - start_time
                                print(f"\r⏳ 等待中... {i}秒 | ", end='')
                                self.print_status(current_purchased, target_count, created_odcrs, elapsed)
                                time.sleep(1)
                            print()
                        continue
                    else:
                        # 扩容失败，尝试创建新ODCR
                        print(f"\n⚠️  扩容失败，尝试创建新ODCR ({attempt_count}台)")
                except Exception as e:
                    print(f"\n❌ 扩容错误: {str(e)}")
            else:
                print(f"\n🔄 第{attempt_count_total}次尝试: 创建新ODCR ({attempt_count}台)")
                self.print_status(current_purchased, target_count, created_odcrs, elapsed)
            
            # 尝试创建新ODCR
            try:
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                odcr_id = self.create_new_odcr(instance_type, availability_zone, attempt_count, capacity_preference)
                
                current_purchased += attempt_count
                created_odcrs.append({
                    'odcr_id': odcr_id,
                    'initial_capacity': attempt_count,
                    'current_capacity': attempt_count,
                    'created_at': timestamp
                })
                
                print(f"\n✅ 新ODCR创建成功! {odcr_id} ({attempt_count} 台)")
                self.print_status(current_purchased, target_count, created_odcrs, elapsed)
                
                # 成功后重置尝试大小
                if current_purchased < target_count:
                    current_attempt_size = target_count - current_purchased
                    print(f"\n⏳ 等待30秒后继续...")
                    
                    for i in range(30, 0, -1):
                        elapsed = datetime.now() - start_time
                        print(f"\r⏳ 等待中... {i}秒 | ", end='')
                        self.print_status(current_purchased, target_count, created_odcrs, elapsed)
                        time.sleep(1)
                    print()
                
            except Exception as e:
                error_str = str(e)
                if 'InsufficientCapacity' in error_str or 'InsufficientInstanceCapacity' in error_str:
                    # 容量不足，减半重试
                    new_attempt_size = max(1, current_attempt_size // 2)
                    if new_attempt_size == current_attempt_size:
                        print(f"\n⚠️  即使1台也容量不足，等待30秒后重试...")
                        for i in range(30, 0, -1):
                            elapsed = datetime.now() - start_time
                            print(f"\r⚠️  容量不足等待中... {i}秒 | ", end='')
                            self.print_status(current_purchased, target_count, created_odcrs, elapsed)
                            time.sleep(1)
                        print()
                    else:
                        current_attempt_size = new_attempt_size
                        print(f"\n⚠️  容量不足，降级到 {current_attempt_size} 台重试")
                        time.sleep(5)
                else:
                    print(f"\n❌ 永久错误: {error_str}")
                    break
        
        # 最终结果
        elapsed = datetime.now() - start_time
        print(f"\n" + "=" * 60)
        
        result = {
            'success': current_purchased > 0,
            'target_count': target_count,
            'actual_count': current_purchased,
            'created_odcrs': created_odcrs,
            'total_attempts': attempt_count_total,
            'elapsed_time': str(elapsed).split('.')[0],
            'completed': current_purchased >= target_count
        }
        
        if result['completed']:
            print(f"🎉 任务完成! 使用 {len(created_odcrs)} 个ODCR，总计 {current_purchased} 台实例")
        else:
            print(f"⏰ 任务结束! 在 {elapsed} 内创建了 {current_purchased}/{target_count} 台实例")
        
        print(f"📊 总尝试次数: {attempt_count_total}")
        
        return result

def main():
    parser = argparse.ArgumentParser(description='ODCR本地管理工具 - 优先扩容现有ODCR')
    parser.add_argument('--region', default='us-west-2', help='AWS区域')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    create_parser = subparsers.add_parser('create', help='创建新ODCR')
    create_parser.add_argument('--instance-type', required=True, help='实例类型')
    create_parser.add_argument('--availability-zone', required=True, help='可用区')
    create_parser.add_argument('--count', type=int, required=True, help='实例数量')
    create_parser.add_argument('--preference', default='open', choices=['open', 'targeted'], help='容量偏好')
    create_parser.add_argument('--timeout', type=int, default=60, help='超时时间(分钟)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = ODCRManager(region=args.region)
    
    if args.command == 'create':
        try:
            result = manager.create_odcr_with_split_purchase(
                instance_type=args.instance_type,
                availability_zone=args.availability_zone,
                target_count=args.count,
                capacity_preference=args.preference,
                timeout_minutes=args.timeout
            )
            print(f"\n📋 最终结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except KeyboardInterrupt:
            print(f"\n\n⚠️  用户中断执行")
            sys.exit(1)

if __name__ == '__main__':
    main()

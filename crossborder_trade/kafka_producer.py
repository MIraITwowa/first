from kafka import KafkaProducer
import json
from django.conf import settings

# 初始化Kafka生产者
producer = KafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_order_created_message(order_data):
    """发送订单创建消息到Kafka"""
    producer.send(
        topic='order_created',
        value=order_data
    )
    producer.flush()  # 确保消息发送

def send_stock_change_message(stock_data):
    """发送库存变更消息到Kafka"""
    producer.send(
        topic='stock_changed',
        value=stock_data
    )
    producer.flush()
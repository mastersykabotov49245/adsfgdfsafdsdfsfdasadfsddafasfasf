# system_monitor.py
import logging
import psutil
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        
    async def start_monitoring(self):
        """Запускает мониторинг системы"""
        while True:
            try:
                # Мониторинг использования памяти
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)
                
                if memory.percent > 85:
                    logger.warning(f"Высокое использование памяти: {memory.percent}%")
                
                if cpu > 80:
                    logger.warning(f"Высокая загрузка CPU: {cpu}%")
                
                # Ждем 30 секунд перед следующей проверкой
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Ошибка мониторинга: {e}")
                await asyncio.sleep(60)

    def get_system_stats(self):
        """Возвращает статистику системы"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_usage': cpu,
            'memory_usage': memory.percent,
            'disk_usage': disk.percent,
            'uptime': str(datetime.now() - self.start_time)
        }

# Глобальный монитор системы
system_monitor = SystemMonitor()
import logging
import os
from pathlib import Path

def setup_logging():
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    # สร้าง StreamHandler เพื่อพ่น Log ออกหน้าจอ (Console)
    # วิธีนี้จะใช้ได้ทั้ง Local และบน Vercel
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # ตรวจสอบว่าถ้าไม่ได้รันบน Vercel (เช่นรัน Local) ถึงจะอนุญาตให้เขียนไฟล์
    if not os.environ.get("VERCEL"):
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_dir / "app.log")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Cannot setup file logging: {e}")

    return logger

# Initialize the global logger instance
logger = setup_logging()
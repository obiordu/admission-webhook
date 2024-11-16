import logging
import json
from pythonjsonlogger import jsonlogger
import sys
from typing import Optional

def setup_logger(name: str = "webhook", log_level: Optional[str] = None) -> logging.Logger:
    """
    Setup structured JSON logging
    """
    logger = logging.getLogger(name)
    
    # Set log level
    level = getattr(logging, log_level.upper()) if log_level else logging.INFO
    logger.setLevel(level)
    
    # Create JSON formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Create default logger
logger = setup_logger()

class WebhookLoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter for webhook requests
    """
    def process(self, msg, kwargs):
        # Add request context if available
        if hasattr(self.extra, 'request_id'):
            kwargs["extra"] = {
                "request_id": self.extra.request_id,
                **kwargs.get("extra", {})
            }
        return msg, kwargs

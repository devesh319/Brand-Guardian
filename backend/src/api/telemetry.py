import logging
import os
from azure.monitor.opentelemetry import configure_azure_monitor

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("brand-guardian-telemetry")


def set_telemetry():
    # Retrieve COnnection String
    connection_string = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")

    if not connection_string:
        logger.warning("Azure Telemetry is disabled!")
        return

    try:
        configure_azure_monitor(
            connection_string=connection_string, logger_name="brand-guardian-tracer"
        )
        logger.warning("Azure Telemetry iis Configured and Enabled!")
    except Exception as e:
        logger.error(f"Azure Telemetry failed: {str(e)}")

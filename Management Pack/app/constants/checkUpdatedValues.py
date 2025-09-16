#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

NULL_STATUS = "null"
logger = logging.getLogger(__name__)


def checkLastValue(objectName, keyName, currentValue, valueType):
      if valueType == "metric":
            lastValue = objectName.get_last_metric_value(keyName)
            if lastValue != currentValue:
                  logger.info(f"Metric value changed for {keyName}: from '{lastValue}' to '{currentValue}'")
                  return True
            else:
                  logger.info(f"No change in metric value for {keyName}: from '{lastValue}' remains as '{currentValue}'")
                  return False
      if valueType == "property":
            lastValue = objectName.get_last_property_value(keyName)
            if lastValue != currentValue:
                  logger.info(f"Property value changed for {keyName}: from '{lastValue}' to '{currentValue}'")
                  return True
            else:
                  logger.info(f"No change in property value for {keyName}: from '{lastValue}' remains as '{currentValue}'")
                  return False
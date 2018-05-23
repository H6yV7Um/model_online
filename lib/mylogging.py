# -*- coding: utf-8 -*-
#!/usr/bin/python                        
##################################################
# AUTHOR: Yandi LI
# DATE:   2015-03-28
# TASK:  INITIALIZE A LOGGER FOR A CLASS 
##################################################
import logging
import logging.handlers
import sys, os
#from cloghandler import ConcurrentRotatingFileHandler # pip install ConcurrentLogHandler

#logging.basicConfig(level=logging.INFO,
#    format='%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
#    filename='../log/WebpageShow.log',
#    filemode='w')

class LevelFilter(object):
  """
  This is a filter which keep only a specific level
  @http://stackoverflow.com/questions/8162419/python-logging-specific-level-only
  """
  def __init__(self, level):
    self.__level = level

  def filter(self, logRecord):
    return logRecord.levelno <= self.__level


#class ContextFilter(logging.Filter):
#  """
#  This is a filter which injects contextual information into the log.
#  @http://stackoverflow.com/questions/16203908/how-to-input-variables-in-logger-formatter
#  """
#  def filter(self, record):
#    record.context = context
#    return True


class CustomAdapter(logging.LoggerAdapter):
  """
  This example adapter expects the passed in dict-like object to have a
  'context' key, whose value in brackets is prepended to the log message.
  @https://docs.python.org/2/howto/logging-cookbook.html#context-info
  """
  def process(self, msg, kwargs):
    return '[%s]\t%s' % (self.extra['context'], msg), kwargs


def getLogger(logname='root'):
    
  log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'../log')
  if not os.path.isdir(log_path):
        os.mkdir(log_path)
    
  logger = logging.getLogger(logname)
  logger.setLevel(logging.INFO)

  #================================
  # File Handler
  #================================
#  LOG_FILENAME = os.path.abspath('./log/' + logname + '.err')
  LOG_FILENAME = os.path.abspath(log_path+'/' + logname + '.err')
  handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2e7, backupCount=5)
  #handler = ConcurrentRotatingFileHandler(LOG_FILENAME, "a", 200*1024*1024, 5)
  handler.setLevel(logging.WARN)
  formatter = logging.Formatter("%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s")
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  
  #================================
  # Standard Output Handler: INFO ONLY
  #================================
  # handler = logging.StreamHandler(sys.stdout)
#  LOG_FILENAME = os.path.abspath('./log/' + logname + '.info')
  LOG_FILENAME = os.path.abspath(log_path+'/' + logname + '.info')
  handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2e7, backupCount=5)
  #handler = ConcurrentRotatingFileHandler(LOG_FILENAME, "a", 200*1024*1024, 5)
  handler.setLevel(logging.INFO)
  formatter = logging.Formatter("%(asctime)s\t%(name)s\t%(message)s")
  handler.setFormatter(formatter)
  handler.addFilter(LevelFilter(logging.INFO))
  logger.addHandler(handler)
  return logger



from sys import path, exc_info
from os import getcwd
from datetime import tzinfo, datetime
import requests
import json
from logging import getLogger

from config import log_data_to_local_couchdb, log_data_to_local_file

logger = getLogger('mvp.' + __name__)

def need_to_log_locally():
   return log_data_to_local_couchdb or log_data_to_local_file


# Log data to couchdb and/or file or neither.
#

def logData(sensor_name, status, attribute, subject, value, units, comment):

   # Need to factor out the next call.    
   timestamp = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.now())

   if log_data_to_local_file == True:
      logFile(timestamp, sensor_name, status, attribute, value, comment)

   if log_data_to_local_couchdb == True:
      logDB(timestamp, sensor_name, status, attribute, value, comment)


def logFile(timestamp, name, status, attribute, value, comment):
    #TBD - Need to put a file rotation scheme in place for the text file.
    #TBD - I'm not sure this is thread safe.  If the light controller and the logSensor
    #      threads both call it can things get messed up?:

    try:
        f = open(getcwd() + '/data/data.txt', 'a')
        s = name + ", " + status + ", " + attribute + ", " + value + "," + comment
        logger.debug('appending data: {} to file: {}'.format(s, f))
        f.write(s + "\n")
        f.close()
    except:
       logger.error('Error writing to data file: {}'.format(exc_info()[0]))


def logDB(timestamp, name, status, attribute, value, comment):

    s = name + ", " + status + ", " + attribute + ", " + value + "," + comment
    logger.debug('couchd db write: {}'.format(s))

    log_record = {'timestamp' : timestamp,
            'name' : name,
            'status' : status,
            'attribute' : attribute,
            'value' : value,
            'comment' : comment}
    json_data = json.dumps(log_record)
    headers = {'content-type': 'application/json'}
    
    """
    f there is a network problem like a DNS failure, or refused connection the Requests library will
    raise a ConnectionError exception.  With invalid HTTP responses, Requests will also raise an HTTPError 
    exception, but these are rare.  If a request times out, a Timeout exception will be raised.
    If and when a request exceeds the preconfigured number of maximum redirections, then a TooManyRedirects
    exception will be raised.
    """

    r = requests.post('http://localhost:5984/mvp_sensor_data', data = json_data, headers=headers)

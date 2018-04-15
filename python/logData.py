from datetime import tzinfo, datetime
import requests
import json
from send_mqtt_data import send_sensor_data_via_mqtt

#Output to file
#logData("si7021_top", "Success", "temperature", "{:10.1f}".format(temp), '')
def logData(mqtt, name, status, attribute, value, units, date_time, comment):

    # Need to factor out the next call.    
    timestamp = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.utcnow())
    logFile(timestamp, name, status, attribute, value, comment)
    logDB(timestamp, name, status, attribute, value, comment)

    if status == "Success":
       send_sensor_data_via_mqtt(mqtt, attribute, value, units, date_time)
    
def logFile(timestamp, name, status, attribute, value, comment):
    f = open('/home/pi/MVP/data/data.txt', 'a')
    s= timestamp + ", " + name + ", " + status + ", " + attribute + ", " + value + "," + comment + "\n"
    print(s)
    f.write(s)
    f.close()

def logDB(timestamp, name, status, attribute, value, comment):
    log_record = {'timestamp' : timestamp,
            'name' : name,
            'status' : status,
            'attribute' : attribute,
            'value' : value,
            'comment' : comment}
    json_data = json.dumps(log_record)
    print(json.dumps(log_record, indent=4, sort_keys=True))
    headers = {'content-type': 'application/json'}
    r = requests.post('http://localhost:5984/mvp_sensor_data', data = json_data, headers=headers)
    print(r.json())

#Uncomment to test this function
#logData(_si7021, _Success, _temperature, '27', '')    

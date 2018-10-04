# TBD: Need to write the state file out whenever a change is made that makes this necessary (such as someone turning
#      a recipe on or off.  Add this functionality. Currenlty the state file is written out every state_file_write_interval
#      seconds and when the program gracefully exits.

from os import path, getcwd
from sys import exc_info
from threading import Lock
from time import sleep, time
import datetime
import json
import time

from python.logData import logDB
from python.logger import get_sub_logger 

# Provide a lock to control access to the climate controller state
#
state_lock = Lock()

logger = get_sub_logger(__name__)

# State variables:
# 1) recipe
# 2) run_mode: 'on' or 'off'
climate_state = {} 

# Load the recipe file found at rel_path and stick the JSON into climate_state['recipe']
#
def load_recipe_file(rel_path):

    climate_state['recipe'] = None

    recipe_path = getcwd() + rel_path
    logger.debug('opening recipe file: {}'.format(recipe_path))

    if path.isfile(recipe_path):
        logger.debug('found recipe file')

        with open(recipe_path) as f:
            try:
                recipe = json.load(f)
                climate_state['recipe'] = recipe
            except:
                logger.error('cannot parce recipe file.')
        
    else:
        logger.debug('no recipe file found. the climate controller cannot run without a recipe file.')

def load_state_file(rel_path):

    state_file_path = getcwd() + rel_path
    logger.debug('opening climate state file: {}'.format(state_file_path))

    if path.isfile(state_file_path):
        logger.debug('found state file - will load it')
        
        with open(state_file_path) as f:
            try:
                global climate_state
                climate_state = json.load(f)
            except:
                logger.error('cannot load state file.')
        
    else:
        logger.debug('no state file found. The climate controller will be set to off.')

def write_state_file(rel_path, update_interval, force):

    if force or (time.time() >= climate_state['last_state_file_update_time'] + update_interval):

        # Go ahead and log the update time even though the file write is not done. This way
        # you want bang on the file system over and over in the presence of errors.
        climate_state['last_state_file_update_time'] = time.time()
       
        try:
            state_file_path = getcwd() + rel_path
            logger.info('writing climate state file {}'.format(state_file_path))

            with open(state_file_path, 'w') as outfile:
                    json.dump(climate_state, outfile)
        except:
            logger.error('error encountered while writing state file: {}{}'.format(exc_info()[0], exc_info()[1]))


def make_help(prefix):

    def help():

        cmd_pre = "{}.".format(prefix)
        nul_pre = ' ' * len(cmd_pre)

        s =     cmd_pre + 'help()                     - Displays this help page.\n'
        s = s + cmd_pre + "cmd('start', day_index=n)  - Start a recipe on the designated day (0 based). If no day_index is\n"
        s = s + nul_pre + '                             supplied then start on day 0.\n'
        s = s + nul_pre + "                             e.g. {}.cmd('start', day_index=2) to start a recipe at 3rd day.\n".format(prefix)
        s = s + cmd_pre + "cmd('load_recipe'|'lr',\n" 
        s = s + nul_pre + '    recipe_file=path)      - Load a recipe file. If no recipe_file argument is given\n'
        s = s + nul_pre + '                             then load the default recipe file as specified in the configuration file.\n'
        s = s + nul_pre + "                           - e.g. {}.cmd('lr', recipe_path='/climate_recipes/test1.rcp')\n".format(prefix)
        s = s + cmd_pre + "cmd('stop')                - stop the current recipe.\n".format(prefix)
        s = s + cmd_pre + 'state()                    - Show climate controller state.\n'
        
        return s

    return help

def show_recipe():

    if climate_state['recipe'] != None:
        return climate_state['recipe']
    else:
        return None 

def show_date(date, prelude_msg):

    if date != None:
        return prelude_msg + ': {}\n'.format(datetime.datetime.fromtimestamp(date))
    else:
        return prelude_msg + ': None\n'


def show_state():

    try:
        s =     'Mode:  {}\n'.format(climate_state['run_mode'])  

        if climate_state['recipe'] != None:
            s = s + 'Recipe id: {}\n'.format(climate_state['recipe']['id'])
        else:
            s = s + 'Recipe id: None\n'

        s = s + show_date(climate_state['recipe_start_time'], 'Recipe start time')

        s = s + 'Current day index: {}\n'.format(climate_state['cur_day'])
        s = s + 'Current hour: {}\n'.format(climate_state['cur_hour'])
        s = s + 'Current minute: {}\n'.format(climate_state['cur_min'])
        if climate_state['recipe'] != None and climate_state['cur_phase_index'] != None:
            s = s + 'Current phase: {}\n'.format(climate_state['recipe']['phases'][climate_state['cur_phase_index']]['name'])   

        s = s + 'Current phase index: {}\n'.format(climate_state['cur_phase_index'])   

        s = s + 'Grow light on: {}\n'.format(climate_state['grow_light_on'])
        s = s + show_date(climate_state['grow_light_last_on_time'], 'Last grow light on time')
        s = s + show_date(climate_state['grow_light_last_off_time'], 'Last grow light off time')

        s = s + 'Vent fan on: {}\n'.format(climate_state['vent_fan_on'])
        s = s + show_date(climate_state['vent_last_on_time'], 'Last vent fan on time')

        s = s + 'Air heater on: {}\n'.format(climate_state['air_heater_on'])
        s = s + 'Air temperature: {}\n'.format(climate_state['cur_air_temp'])

        s = s + show_date(climate_state['air_heater_last_on_time'], 'Air heater last on time')
        s = s + show_date(climate_state['air_heater_last_off_time'], 'Air heater last off time')

        s = s + 'Last state file write: {}\n'.format(datetime.datetime.fromtimestamp(
                                                     climate_state['last_state_file_update_time']).isoformat())
        return s

    except:
        logger.error('show_state command {}{}'.format(exc_info()[0], exc_info()[1]))
        return "Error - can't show stat"

def make_cmd(config_args):

    def cmd(*args, **kwargs):

        state_lock.acquire()

        try: 
            if len(args) == 1:
                if args[0] == 'start':

                    if 'day_index' in kwargs:
                        climate_state['cur_day'] = kwargs['day_index']
                    else:
                        climate_state['cur_day'] = 0

                    climate_state['run_mode'] = 'on'
                    climate_state['recipe_start_time'] = (datetime.datetime.now()\
                        - datetime.timedelta(days=climate_state['cur_day'])).timestamp()
                    return 'OK'
                elif args[0] == 'stop':
                    climate_state['run_mode'] = 'off'
                    climate_state['recipe_start_time'] = None
                    return 'OK'
                elif args[0] == 'load_recipe' or args[0] == 'lr':
                    if not 'recipe_file' in kwargs:
                        # TBD - Need to 1st check to make sure the file exists and then warn user if it does not exist.
                        load_recipe_file(config_args['default_recipe_file'])
                    else:
                        load_recipe_file(kwargs['recipe_file'])
                    return 'OK'
                else:
                    return "illegal command: {}. please specify 'start' or 'stop'".format(args[0])
            else:
                return "you must supply a cmd (e.g. 'start')"
        except:
            logger.error('cmd execution failed: {}, {}'.format(exc_info()[0], exc_info()[1]))

        finally:
            state_lock.release()

    return cmd


def init_state(args):

    # Initialize the climate controller state - this stuff will get replaced
    # if there is a state file to load
    climate_state['run_mode'] = 'off'
    climate_state['cur_phase_index'] = None
    climate_state['recipe_start_time'] = None
    # make sure the state has a recipe in case there is no state file.
    load_recipe_file(args['default_recipe_file'])

    # See if there is previous state in a state file  and load it if you have it, otherwise
    # create a state file so it's there the next time we reboot.
    load_state_file(args['state_file'])
    climate_state['last_state_file_update_time'] = time.time()

    now = datetime.datetime.now()
    climate_state['cur_min'] = now.minute
    climate_state['cur_hour'] = now.hour
    if climate_state['recipe_start_time'] != None:
        climate_state['cur_day'] = (now - datetime.datetime.fromtimestamp(climate_state['recipe_start_time'])).days
    else:
        climate_state['cur_day'] = None
        
    climate_state['grow_light_on'] = False
    climate_state['grow_light_last_on_time'] = None
    climate_state['grow_light_last_off_time'] = None

    climate_state['vent_fan_on'] = False
    climate_state['vent_last_on_time'] = None

    climate_state['air_heater_on'] =  False
    climate_state['cur_air_temp'] = None
    climate_state['air_heater_last_on_time'] = None
    climate_state['air_heater_last_off_time'] = None

    # climate_state['cur_time'] = 0 
    climate_state['last_log_time'] = 0
    climate_state['log_cycle'] = False


# step_name -> e.g. light_intensity, air_fush
# value names -> tuple list of value names to return
#
def get_current_recipe_step_values(step_name, value_names):

    values = None 

    try:
        
        times = climate_state['recipe']['phases'][climate_state['cur_phase_index']]['step'][step_name]

        if len(times) > 0:
            
            for t in times:

                past_start = False
                lte_end = False
               
                # accept times as either integers, floats (i.e the hour) or strings (e.g. hh:mm)
                if isinstance(t['start_time'], (int, float)):
                    start = [int(t['start_time']), int((t['start_time'] - int(t['start_time'])) * 60)]
                else:
                    start = t['start_time'].split(':')

                if start[0] <= climate_state['cur_hour']: 
                    if len(start) > 1:
                        if start[1] <= climate_state['cur_min']:
                            past_start = True
                        else:
                            past_start = False
                    else:
                        past_start = True 

                if isinstance(t['end_time'], (int, float)):
                    end = [int(t['end_time']), int((t['end_time'] - int(t['end_time'])) * 60)]
                else:
                    end = t['end_time'].split(':')
                
                if len(end) == 1:
                    if end[0] >= climate_state['cur_hour']: 
                        lte_end = True
                    else:
                        lte_end = False
                else:
                    if (end[0] >= climate_state['cur_hour']) or\
                       (end[0] == climate_state['cur_hour'] and end[1] >= climate_state['cur_min']):
                            lte_end = True
                    else:
                        lte_end = False 
                
                #d logger.info('step name: {}, start: {}, end: {}, past_start: {}, lte_end: {}'.format(step_name, start, end, past_start, lte_end))

                if past_start and lte_end:

                    values = {}

                    for vn in value_names:
                        if vn in t:
                            values[vn] = t[vn]
                        else:
                            logger.warning('cannot find value {} in step {}.'.format(vn, step_name))

                    # You've found the step that cooresponds to the current timeso now exit.
                    return values


        else:
            if climate_state['log_cycle']:
                logger.warning('There are no recipe steps for: {}.  Why?'.format(step_name))

    except:
        logger.error('failed looking for step values: {}, {}, {}'.format(step_name, exc_info()[0], exc_info()[1]))

    return values

def check_lights(controller):
    
    value = get_current_recipe_step_values('light_intensity', ('value',))

    light_on = None

    if value != None:
        if value['value']  == 1:
            if not climate_state['grow_light_on']: 
                light_on = True
        else:
            if climate_state['grow_light_on']:
                light_on = False 
    else:
        if climate_state['grow_light_on']:
            light_on = False 

    if light_on != None:
        if light_on:
            climate_state['grow_light_on'] = True
            climate_state['grow_light_last_on_time'] = climate_state['cur_time'] 
            controller['cmd']('on', 'grow_light') 
        else:
            climate_state['grow_light_on'] = False 
            climate_state['grow_light_last_off_time'] = climate_state['cur_time']
            controller['cmd']('off', 'grow_light')


def check_vent_fan(controller):

    values = get_current_recipe_step_values('air_flush', ('interval', 'duration'))
    fan_on = None

    #logger.debug('vent_fan_on: {}, vent_last_on_time: {}, cur_time: {}, duration: {}, interval: {}'.format(climate_state['vent_fan_on'], climate_state['vent_last_on_time'], climate_state['cur_time'], values['duration'], values['interval']))

    if values != None and climate_state['vent_last_on_time'] != None:
        if climate_state['vent_fan_on'] and\
           climate_state['cur_time'] - climate_state['vent_last_on_time'] > 60 * values['duration']:

            fan_on = False
        if not climate_state['vent_fan_on'] and\
               climate_state['cur_time'] - climate_state['vent_last_on_time'] > 60 * values['interval']:
            fan_on = True
    elif values != None and climate_state['vent_last_on_time'] == None:
        # Assume this is a startup state.  There are recipe values for the flush flan but 
        # no history on the flushing so go ahead and start a flush cycle.
        fan_on = True
    else:
        # There are no recipe values for flushing so leave the fan off.
        fan_on = False

    if fan_on != None:
        if fan_on:
            climate_state['vent_fan_on'] = True
            climate_state['vent_last_on_time'] = climate_state['cur_time']
            controller['cmd']('on', 'vent_fan') 
            logger.info('turning vent fan on') 
        else:
            climate_state['vent_fan_on'] = False
            controller['cmd']('off', 'vent_fan') 
            logger.info('turning vent fan off') 


def check_air_temperature(controller):

    values = get_current_recipe_step_values('air_temperature', ('low_limit', 'high_limit'))
    heater_on = None

    if values != None:
        # TBD - Need to set the temperature gap based upon the controllers abilities. The FCV1 temperature sensor
        #       is not that accurate so to avoid the heater going and off we enforce a minimal difference of 2.
        #       The reason the recipe can specify different values is to allow people to set wide ranges so that
        #       they don't need to use their heater a lot if that is their desire.
        if values ['high_limit'] - values['low_limit'] >= 2:

            mid_val_temp = (values ['high_limit'] + values['low_limit'])/2.0 

            if climate_state['cur_air_temp'] != None:
                if climate_state['cur_air_temp'] < values['low_limit'] and not climate_state['air_heater_on']:
                    heater_on = True
                elif climate_state['cur_air_temp'] > (values['low_limit'] + mid_val_temp) and\
                     climate_state['air_heater_on']:
                    heater_on = False
            else:
                logger.warning('No air temperature avaialble. Will turn heater off.')
                heater_on = False 
        else:
            if climate_state['log_cycle']: 
                logger.error('Illegal values for high and low limits. High limit must be ' +\
                             'at least 2 degrees Celsius higher than low limit.')

    else:
        heater_on = False
        logger.info('No air temperature instructions found')

    # Don't run the heater for more than 30 minutes.
    if climate_state['air_heater_on']:
        if climate_state['air_heater_last_on_time'] != None and\
           climate_state['cur_time'] - climate_state['air_heater_last_on_time'] > 30 * 60:

            heater_on = False

    # If the last run was for over 29 minutes then let the heater rest for 5 minutes
    if not climate_state['air_heater_on']:
        if (climate_state['air_heater_last_off_time'] != None and\
            climate_state['air_heater_last_on_time'] != None) and\
           (climate_state['air_heater_last_off_time'] - climate_state['air_heater_last_on_time']  > 29 * 60) and\
           (climate_state['cur_time'] - climate_state['air_heater_last_off_time']) < 5 * 60: 
           
            heater_on = False

    if heater_on != None:
        if heater_on:

            # Don't turn the heater on more than once per minute.
            if climate_state['air_heater_last_on_time'] == None or\
               climate_state['cur_time'] - climate_state['air_heater_last_on_time'] >= 60: 
                   
                logger.info('turning the air heater on')
                climate_state['air_heater_on'] = True
                climate_state['air_heater_last_on_time'] = climate_state['cur_time']
                controller['cmd']('on', 'air_heat')
        else:
            logger.info('turning the air heater off')
            climate_state['air_heater_on'] = False 
            climate_state['air_heater_last_off_time'] = climate_state['cur_time']
            controller['cmd']('off', 'air_heat')


def get_phase_index(cur_day_index, phases):

    try:

        rcp_day_index = 0

        for i in range(0, len(phases)):
            
            rcp_phase_cycles = phases[i]['cycles']

            if cur_day_index >= rcp_day_index and cur_day_index < rcp_day_index + rcp_phase_cycles: 

                return i

            else:
                rcp_day_index = rcp_day_index + rcp_phase_cycles

        logger.error('the current recipe does not apply to today. It may be over.')
        return None

    except:
        logger.error('cannot update phase index: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return None

def update_climate_state(min_log_period, controller):

    now = datetime.datetime.now()
    
    climate_state['cur_min'] = now.minute
    climate_state['cur_hour'] = now.hour
    
    if climate_state['recipe_start_time'] != None:
        climate_state['cur_day'] = (now - datetime.datetime.fromtimestamp(climate_state['recipe_start_time'])).days
    else:
        climate_state['cur_day'] = None

    climate_state['cur_phase_index'] = get_phase_index(climate_state['cur_day'], climate_state['recipe']['phases'])

    climate_state['cur_time'] = time.time()   # Return the time in seconds since the epoch as a floating point number.

    if climate_state['cur_time']  - climate_state['last_log_time'] >= min_log_period:   
        climate_state['last_log_time'] = climate_state['cur_time']
        climate_state['log_cycle'] =  True
    else:
        climate_state['log_cycle'] = False

    at = controller['get']('air_temp')['value']
    try:
        climate_state['cur_air_temp'] = float(at)
    except:
        if climate_state['log_cycle']:
            logger.warning('cannot read air temperature. value returned by source is {}'.format(at))

    # logger.info('cur_time {}, last_log_time: {}, log_cycle: {}'.format(climate_state['cur_time'], 
    #             climate_state['last_log_time'], climate_state['log_cycle']))

def start(app_state, args, barrier):

    logger.setLevel(args['log_level'])
    logger.info('starting climate controller thread')

    # Inject this resources commands into app_state
    app_state[args['name']] = {}
    app_state[args['name']]['help'] = make_help(args['name']) 
    app_state[args['name']]['state'] = show_state
    app_state[args['name']]['recipe'] = show_recipe
    app_state[args['name']]['cmd'] = make_cmd(args)

    init_state(args)

    # Don't proceed until all the other resources are available.
    barrier.wait()    

    while not app_state['stop']:

       state_lock.acquire()

       try:
           if climate_state['run_mode'] == 'on': 

               update_climate_state(args['min_log_period'], app_state['mc'])

               # TODO - need to make 'mc' configurable from config file.
               check_lights(app_state['mc'])

               check_vent_fan(app_state['mc'])
               
               check_air_temperature(app_state['mc'])

           # Every once in a while write the state to the state file to make sure the file 
           # stays up to date.  TBD: A more sophisticated system would write only when
           # changes were made.
           #
           write_state_file(args['state_file'], args['state_file_write_interval'], False)

       finally:
           state_lock.release()

       sleep(1)

    write_state_file(args['state_file'], args['state_file_write_interval'], True)
    logger.info('exiting climate controller thread')

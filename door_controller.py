#!/usr/bin/python3

"""

To Do:




"""

import pifacedigitalio
import threading
import os
import sys
import collections
import select
import time
from time import sleep

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

import log_handler
import get_config
import pollable_queue
import event_handler

CONFIG_FILE_NAME = 'config.conf'

PifaceInput = collections.namedtuple('Input', 'name type description pin rising falling disablepullup')
PifaceOutput = collections.namedtuple('Output', 'name description pin')
InputCommands = collections.namedtuple('InputCommands',
                                       'toggle_door_cmd open_door_cmd close_door_cmd light_cmd control_wire stop_cmd')

EventContainer = collections.namedtuple('Event', 'source type value creation hardware pin')                                       
                                       
DOOR_STATUS_INPUT_NAME = 'Door_Status'
DOOR_RELAY_OUTPUT_NAME = 'Door_Relay'
STATUS_LED_OUTPUT_NAME = 'Status_LED'

OPEN = 0
CLOSED = 1
OFF = 0
ON = 1
PRESSED = 1

INSTRUCTION_TIMEOUT  = 1 #seconds

#Sources
BUTTON = 'Button'
NETWORK = 'Network'
MONITORING = 'Monitoring'
INTERNAL = 'Internal'
ERROR = 'Error'


class InterruptHandler(object):

    """Handles interrupt events"""

    def __init__(self, e_source, e_type, e_value, queue):
        self.event_source = e_source
        self.event_type = e_type
        self.event_value = e_value
        self.event_queue = queue

    def interrupt_function(self, event):
    
        #print(type(event))
        #print(event)
    
        #<class 'pifacecommon.interrupts.InterruptEvent'>
        #interrupt_flag:    0b100000
        #interrupt_capture: 0b1011111
        #pin_num:           5
        #direction:         0
        #chip:              <pifacedigitalio.core.PiFaceDigital object at 0xb5bb5b50>
        #timestamp:         1499169992.78806
    
        ev = EventContainer(source=self.event_source,
                            type=self.event_type,
                            value=self.event_value,
                            creation=event.timestamp,
                            hardware=True,
                            pin=event.pin_num)    
                            
        self.event_queue.put(ev)


class InputOutputHandler(object):

    """Handles Input/Output operations on PiFace"""
    
    
    def input_pin(self, pin): return self.pifacedigital.input_pins[pin].value
    
    def output_pin(self, pin): return self.pifacedigital.output_pins[pin].value
    
    
    def __input_filter(self, event):
    
        if not event.hardware:
            return True
            
        pin_val = self.input_pin(event.pin)
        
        if event.type == 'Door_Status' and event.value == 'Rising_Edge' and pin_val == OPEN:
            return True
        elif pin_val == PRESSED:
            return True
           
        return False
        

    def __toggle_door(self):
        self.operate_door.set()

    def __open_door(self):
        if self.input_pin(self.door_status_pin) == CLOSED:
            self.operate_door.set()

    def __close_door(self):
        if self.input_pin(self.door_status_pin) == OPEN:
            self.operate_door.set()

    def __light(self):
        self.operate_light.set()
        
    def __log_input_pin_state(self, ev):
                
        self.logging_queue.put(self.__create_event_obj(MONITORING,
                                                       ev.type,
                                                       self.input_pin(ev.pin)))
                                                       
    def __log_output_pin_state(self, ev):
                
        self.logging_queue.put(self.__create_event_obj(MONITORING,
                                                       ev.type,
                                                       self.output_pin(ev.pin)))
        

    def __flash_status_led(self):

        """Flash status LEDs"""
    
        while not self.stop_event.isSet():
            
            if self.input_pin(self.door_status_pin) == CLOSED:
                self.pifacedigital.leds[self.led_status0_pin].set_high()
                sleep(3)
                self.pifacedigital.leds[self.led_status0_pin].set_low()
                sleep(0.1)
            else:
                self.pifacedigital.leds[self.led_status0_pin].set_high()
                sleep(0.7)
                self.pifacedigital.leds[self.led_status0_pin].set_low()
                sleep(0.7)


    def __check_relay_state(self, last_state=0):
    
        """Poll relay status to check its not stuck on"""

        current_state = self.output_pin(self.door_relay_pin)
        
        if last_state == 1 and current_state == 1:
            self.logger1.info('Resetting Relay')
            self.pifacedigital.leds[self.door_relay_pin].set_low()
            self.logging_queue.put(self.__create_event_obj(MONITORING, 'Relay', 'StuckOn'))

        if not self.stop_event.isSet():
            self.check_relay_thread = threading.Timer(5, self.__check_relay_state, args=(current_state,))
            self.check_relay_thread.start()


    def __door_activator(self):
    
        """Activate door"""

        while not self.stop_event.isSet():

            self.operate_door.wait(30)

            if self.operate_door.isSet():
            
                if not self.door_locked:
                    self.pifacedigital.leds[self.door_relay_pin].set_high()
                    sleep(0.1)
                    self.pifacedigital.leds[self.door_relay_pin].set_low()
                
                sleep(0.1)
                    
                self.operate_door.clear()


    def __light_activator(self):

        """Turn on light"""
    
        while not self.stop_event.isSet():

            self.operate_light.wait(30)

            if self.operate_light.isSet():
            
                if not self.light_locked:
                    self.pifacedigital.leds[self.door_relay_pin].set_high()
                    sleep(0.1)
                    self.pifacedigital.leds[self.door_relay_pin].set_low()
                    sleep(0.1)
                    self.pifacedigital.leds[self.door_relay_pin].set_high()
                    sleep(0.1)
                    self.pifacedigital.leds[self.door_relay_pin].set_low()
                    
                sleep(10)

                self.operate_light.clear()


    def __update_door_info(self):
        
        status = self.input_pin(self.door_status_pin)
        
        if status == self.last_status:
            return None
        
        if status == OPEN:
            self.last_status = OPEN
            self.last_open_time = time.time()
            self.logging_queue.put(self.__create_event_obj(MONITORING, 'Door_Status', self.door_status_pin))
        else:
            self.last_status = CLOSED
            self.last_closed_time = time.time()
            self.logging_queue.put(self.__create_event_obj(MONITORING, 'Door_Status', self.door_status_pin))
        



    def __process_input(self):

        """Process incoming events on event_queue"""

        while not self.stop_event.isSet():

            readable, writable, exceptional = select.select([self.event_queue], [], [])

            if readable[0] is self.event_queue:

                event = self.event_queue.get()
                
                if (time.time() - event.creation) > INSTRUCTION_TIMEOUT:
                    self.logging_queue.put(self.__create_event_obj(ERROR, 'TimeOut',  str(time.time() - event.creation)))
                    self.logger1.info("Instruction rejected due to timeout: '{}', '{}', '{}'".format(event.source, event.type, event.value))
                    
                elif not self.__input_filter(event):
                    self.logging_queue.put(self.__create_event_obj(ERROR, 'Filtered', '{}, {}, {}'.format(event.source, event.type, event.value)))
                    
                else:
                
                    self.logging_queue.put(event)    
                    
                    if event.type == self.input_commands.toggle_door_cmd:
                        self.__toggle_door()
                        self.__update_door_info()
                    elif event.type == self.input_commands.light_cmd:
                        self.__light()
                    elif event.type == self.input_commands.open_door_cmd:
                        self.__open_door()
                        self.__update_door_info()
                    elif event.type == self.input_commands.close_door_cmd:
                        self.__close_door()
                        self.__update_door_info()
                    elif event.type == self.input_commands.control_wire:
                        self.__log_output_pin_state(event)
                        self.__update_door_info()
                    elif event.type == self.input_commands.stop_cmd:
                        self.__del__()
                        return None
                        
                    
                    #if event.hardware:
                    #    self.__log_input_pin_state(event)                 
        
        
    def __create_event_obj(self, src, type, val=None, pin_num=None):
    
        """Create event object"""
    
        return EventContainer(source=src,
                              type=type,
                              value=val,
                              creation=time.time(),
                              hardware=False,
                              pin=pin_num)


    def __init__(self):

        #Setup logging
        self.logger1 = log_handler.get_log_handler(
            'door_controller_log.txt', 'info', 'door.IOHandler')

            
        self.logger1.info('Starting: InputOutputHandler')

        #Open config file
        self.logger1.debug('Getting config from: %s', CONFIG_FILE_NAME)
        config = get_config.get_config(CONFIG_FILE_NAME, True)

        #Parse inputs and outputs from config file
        self.inputs, self.outputs = parse_config(config)

        #Parse commands from config file in named tuple
        self.input_commands = InputCommands(toggle_door_cmd=config.get('Commands', 'toggle_door_cmd'),
                                            open_door_cmd=config.get('Commands', 'open_door_cmd'),
                                            close_door_cmd=config.get('Commands', 'close_door_cmd'),
                                            light_cmd=config.get('Commands', 'light_cmd'),
                                            control_wire=config.get('Commands', 'control_wire'),
                                            stop_cmd=config.get('Commands', 'stop_cmd'))
                                            
        #Lock status                      
        self.door_locked = False
        self.light_locked = False

        #Initialise PiFace and interrupts
        pifacedigitalio.init()
        self.pifacedigital = pifacedigitalio.PiFaceDigital()
        self.listener = pifacedigitalio.InputEventListener(chip=self.pifacedigital)

        #Output pins
        self.door_relay_pin = None
        self.led_status0_pin = None
        
        #Input pins
        self.door_status_pin = None

        #Queue to capture input events
        self.event_queue = pollable_queue.PollableQueue()
        
        #Queue to log events to
        self.logging_queue = pollable_queue.PollableQueue()
        
        #Instantiate logging module
        self.log_events = event_handler.EventHandler(self.logging_queue, self.input_commands.stop_cmd)
        
        #Log starting event
        self.logging_queue.put(self.__create_event_obj(INTERNAL, 'Starting'))

        #Dict to store interrupt functions about to be generated
        self.intrupt_funcs = {}

        #Generate dynamic functions to process interrupts
        for key in self.inputs:

            self.logger1.info('Processing Input: ' + key)
            piface_in = self.inputs[key]
            
            if piface_in.name == DOOR_STATUS_INPUT_NAME:
                self.logger1.info('Setting door status input to pin: {}'.format(piface_in.pin))
                self.door_status_pin = piface_in.pin
            
            #Disable 10K pullup resistor on piface input pin
            if piface_in.disablepullup:
                self.logger1.info('Disabling pullup on input {}'.format(piface_in.name))
                pifacedigitalio.digital_write_pullup(piface_in.pin, 0)

            #Create interrupt listener and associated function for falling edges
            if piface_in.falling:
                self.logger1.info('Creating Falling Edge Listener on input: {}'.format(piface_in.name))
                #e_obj = self.__create_event_obj(piface_in.type, piface_in.name, 'Falling_Edge')
                self.intrupt_funcs[key + '_falling'] = getattr(InterruptHandler(piface_in.type, piface_in.name, 'Falling_Edge', self.event_queue), 'interrupt_function')
                self.listener.register(piface_in.pin, pifacedigitalio.IODIR_FALLING_EDGE, self.intrupt_funcs[key + '_falling'])

            #Create interrupt listener and associated function for rising edges
            if piface_in.rising:
                self.logger1.info('Creating Rising Edge Listener on input: {}'.format(piface_in.name))
                #e_obj = self.__create_event_obj(piface_in.type, piface_in.name, 'Rising_Edge')
                self.intrupt_funcs[key + '_rising'] = getattr(InterruptHandler(piface_in.type, piface_in.name, 'Rising_Edge', self.event_queue), 'interrupt_function')
                self.listener.register(piface_in.pin, pifacedigitalio.IODIR_RISING_EDGE, self.intrupt_funcs[key + '_rising'])

                
        #Processing outputs
        for key in self.outputs:

            piface_out = self.outputs[key]
            
            #Set relay output pin on piface
            if piface_out.name == DOOR_RELAY_OUTPUT_NAME:
                self.logger1.info('Creating door relay on output: {}'.format(piface_out.pin))
                self.door_relay_pin = piface_out.pin
    
            #Set status LED output pin on piface
            if piface_out.name == STATUS_LED_OUTPUT_NAME:
                self.logger1.info('Creating status LED on output: {}'.format(piface_out.pin))
                self.led_status0_pin = piface_out.pin


        self.logger1.info('Starting worker threads')

        #Create threading events and clear them
        self.stop_event = threading.Event()
        self.operate_door = threading.Event()
        self.operate_light = threading.Event()

        self.stop_event.clear()
        self.operate_door.clear()
        self.operate_light.clear()

        #Start threads to process input events
        self.process_input_thread = threading.Thread(name='process_input_thread',
                                                     target=self.__process_input)

        self.activate_door_thread = threading.Thread(name='act_door_thread',
                                                     target=self.__door_activator)

        self.activate_light_thread = threading.Thread(name='act_light_thread',
                                                      target=self.__light_activator)

        self.flash_led_thread = threading.Thread(name='flt', target=self.__flash_status_led)

        self.process_input_thread.start()
        self.activate_door_thread.start()
        self.activate_light_thread.start()
        self.flash_led_thread.start()

        self.check_relay_thread = None
        self.__check_relay_state()
        
        #Monitoring
        self.last_open_time = None
        self.last_closed_time = None
        self.last_status = None

        #Activate interrupts
        self.listener.activate()

        self.logger1.info('Initialisation of InputOutputHandler Complete')



    def __del__(self):
        self.logger1.info('Shutdown command received')
        self.listener.deactivate()
        self.event_queue.put(self.__create_event_obj(INTERNAL, self.input_commands.stop_cmd))
        self.stop_event.set()
        self.flash_led_thread.join()
        self.check_relay_thread.join()
        self.activate_door_thread.join()
        self.activate_light_thread.join()
        #pifacedigitalio.deinit()
        sys.exit()

    
    """PUBLIC METHODS"""
        
    def activate_door(self, val=''):
        self.event_queue.put(self.__create_event_obj(NETWORK,
                                                     self.input_commands.toggle_door_cmd, val))

    def open_door(self, val=''):
        self.event_queue.put(self.__create_event_obj(NETWORK,
                                                     self.input_commands.open_door_cmd, val))

    def close_door(self, val=''):
        self.event_queue.put(self.__create_event_obj(NETWORK,
                                                     self.input_commands.close_door_cmd, val))        

    def activate_light(self, val=''):
        self.event_queue.put(self.__create_event_obj(NETWORK,
                                                     self.input_commands.light_cmd, val))    

    def get_status(self):
        return  {'STATUS': self.pifacedigital.input_pins[self.door_status_pin].value,
                 'DOOR_LOCKED': self.door_locked,
                 'LIGHT_LOCKED': self.light_locked,
                 'LAST_OPEN': self.last_open_time,
                 'LAST_CLOSED': self.last_closed_time}
                 
        #return {'STATUS': self.pifacedigital.input_pins[self.door_status_pin].value}

    def shutdown(self):
        self.__del__()


def parse_config(parser):

    """
    parse inputs and outputs from config file to
    dictionarys of named tuples
    """

    all_inputs = {}
    all_outputs = {}
    input_container = {}
    output_container = {}

    #Parse config file into dictionaries
    for section_name in parser.sections():

        #Input pins
        if section_name.startswith('Input'):

            this_input = {}

            for name, value in parser.items(section_name):
                this_input[name] = value

            all_inputs[section_name] = this_input

        #Output pins
        if section_name.startswith('Output'):

            this_output = {}

            for name, value in parser.items(section_name):
                this_output[name] = value

            all_outputs[section_name] = this_output


    #Convert inputs into dict of named tuples
    for key in all_inputs:
        inp = all_inputs[key]
        input_container[key] = PifaceInput(name=inp['name'],
                                           type=inp['type'],
                                           description=inp['description'],
                                           pin=int(inp['pin']),
                                           rising=bool(inp['rising']),
                                           falling=bool(inp['falling']),
                                           disablepullup=bool(inp['disablepullup']))

    #Convert outputs into dict of named tuples
    for key in all_outputs:
        inp = all_outputs[key]
        output_container[key] = PifaceOutput(name=inp['name'],
                                             description=inp['description'],
                                             pin=int(inp['pin']))


    return input_container, output_container




#if __name__ == "__main__":
#	pass
    #IH = InputOutputHandler()
    #sleep(2)
    #IH.activate_door()
    #sleep(10)
    #IH.shutdown()

    #try:
    #    while True:
    #        sleep(5)
    #except (KeyboardInterrupt, SystemExit):
    #    IH.shutdown()

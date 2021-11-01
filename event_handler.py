#!/usr/bin/python3

import os
import sys
import threading
import select
import pymysql
import datetime
import collections

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

import get_config
import log_handler

import pollable_queue #testing only
from time import sleep #testing only

CONFIG_FILE_NAME = 'config.conf'

class EventHandler(object):

    def __write_to_logfile(self, source, type, value):
        
        try:
            logfile = open('{}/{}'.format(THIS_DIR, self.event_logfile), 'a')
            logfile.write("'{}','{}','{}','{}'\r\n".format(str(datetime.datetime.now()), source, type, value))
            logfile.close()
        except Exception as e:
            self.logger.exception('Error writing to file: {}, {}'.format(type(e).__name__, e.args))
    

    def __insert_into_mysql(self, source, type, value):

        sql_query = "INSERT INTO logs (source, type, value, time) VALUES ('{}', '{}', '{}', now())".format(source, type, value)
        
        mysql_conn = pymysql.connect(host=self.host, user=self.user, passwd=self.pwd, db=self.db)
        
        try:
            mysql_cursor = mysql_conn.cursor()
            mysql_cursor.execute(sql_query)
            mysql_conn.commit()
            mysql_conn.close()
        except Exception as e:
            self.logger.exception('Error inserting in MySQL: {}, {}'.format(type(e).__name__, e.args))
            mysql_conn.rollback()
    
    
    def __parse(self, event):
            
        source = event.source
        type = event.type            
        value = event.value
        
        if value == None:
            value = ''
    
        if type == 'Door_Status' and value == 'Rising_Edge':
            value = 'Opened'
        elif type == 'Door_Status' and value == 'Falling_Edge':
            value = 'Closed'
    
        return source, type, value

    def __process_events(self):
    
        while not self.stop_event.isSet():
        
            readable, writable, exceptional = select.select([self.event_queue], [], [])

            if readable[0] is self.event_queue:
            
                evnt = self.event_queue.get()
                
                esource, etype, evalue = self.__parse(evnt)
                
                #write to file
                self.__write_to_logfile(esource, etype, evalue)
                
                #insert into SQL
                self.__insert_into_mysql(esource, etype, evalue)
                
                if evnt.type == self.shutdown_cmd:
                    self.logger.info('Stopping: EventHandler')
                    #self.__del__()
                    return None
        
        

    def __init__(self, event_q, shutdown_command='Stop'):
    
        self.logger = log_handler.get_log_handler('server_log.txt', 'info', 'door.EventHandler')
        
        self.logger.info('Starting: EventHandler')
        
        #Open config file
        config = get_config.get_config(CONFIG_FILE_NAME)
        
        self.event_logfile=config.get('Logging', 'event_logfile')
        
        self.event_queue = event_q
        self.shutdown_cmd = shutdown_command
        
        self.host=config.get('Logging', 'sql_server')
        self.user=config.get('Logging', 'sql_user')
        self.pwd=config.get('Logging', 'sql_pwd')
        self.db=config.get('Logging', 'sql_db')
        
        #self.mysql_conn = pymysql.connect(host=host, user=user, passwd=pwd, db=db)
        #self.mysql_cursor = self.mysql_conn.cursor()
        
        self.stop_event = threading.Event()

        #Start thread to process input events
        self.process_events_thread = threading.Thread(name='process_events',
                                                     target=self.__process_events)
                                                     
        self.process_events_thread.start()
        

    def __del__(self):
        pass
        #self.logger.info('Stopping: EventHandler')
        #self.stop_event.set()
        #self.process_events_thread.join()
        

        
if __name__ == "__main__":

    cue = pollable_queue.PollableQueue()
    
    EventContainer = collections.namedtuple('Event', 'source type value')     

    evnt_con = EventContainer(source='Test_Source', type='Test_Type', value='Test_Value')
    
    logger = EventHandler(cue)
    
    sleep(1)
    
    cue.put(evnt_con)
    
    sleep(1)
    
    cue.put(EventContainer(source='Test_Source', type='Stop', value='Test_Value'))
    
    sleep(3)
    
    #cue = None
    #logger = None
    
    
        
        
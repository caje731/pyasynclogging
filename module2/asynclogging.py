#!../bin/python
""" Asynchronous Logging For Python.

    This is a partial wrapper over python's logging module.
    It provides asynchronous logging methods, so that business API endpoints
    that are under heavy load can stop worrying about time spent in logging.
"""

from threading import Thread
import json, sys, logging, logging.handlers, Queue, urllib, urllib2
import socket, traceback

# The FIFO Queue instance which stores log requests for later processing
logging_queue = Queue.Queue()

# The number of worker threads that work on queued logging requests
# CAUTION: Creating more than 1 consumer thread will cause messages to be
# logged out of sequence.
NUM_CONSUMER_THREADS = 1

# Slack webhook integration URLs
SLACK_WEBHOOK_URL = 'https://hooks.slack.com'+\
                    '/services/T04BV4TC5/B09UXRE5V/VFu6htlQPwKRPyECFyL3GUWK'

class SlackHTTPHandler(logging.handlers.HTTPHandler):
    """ An HTTPHandler logging class that sends messages to a Slack channel.

        Ideal for scenarios where a real-time notification is needed.
        E.g. when an exception occurs.
    """

    def mapLogRecord(self, record):
        """ Manipulate the record that will be logged. """
        record.__dict__['payload'] = json.dumps({
            "text": '\n'.join([
                # Know the server which generated this log
                'Host: '+ socket.getfqdn(),

                # Know the module which generated this log
                'Logger: '+ record.__dict__['name'],

                # The actual msg of the log entry
                record.__dict__['msg']
            ])
        })
        return record.__dict__

    def emit(self, record):
        """ Log the record in the Slack channel.

            I needed to override this method, as the URL to the Slack channel
            integration is a Secure one (HTTPS). The base class' behaviour 
            didn't seem to log to Slack when specifying host+path in the 
            class constructor.
            TODO : check how to specify protocol for HTTPHandler
        """
        urllib2.urlopen(
            SLACK_WEBHOOK_URL,
            urllib.urlencode({'payload' : self.mapLogRecord(record)['payload']})
        )
        
# Handler definitions for the queue logger
HANDLER_CHOICES = {
    # all logs to stdout
    'stdout' : logging.StreamHandler(stream=sys.stdout),

    # all logs to stderr
    'stderr' : logging.StreamHandler(stream=sys.stderr),

    # all logs to a named file, backed up on a rotating basis
    'logfile' : logging.handlers.RotatingFileHandler(
        '/var/log/server.log',
        mode='a',           # always append, don't overwrite
        maxBytes=1024*5,    # don't grow to more than 5MB
        backupCount=10,     # sustain upto 10 previous log files
        encoding='utf-8',   # think global, not local!
        delay=True          # open the file only after first emit() is made
    ),

    # all logs to nowhere
    'suppress' : logging.NullHandler(),

    # all logs to our Slack channel for crashes
    'slack' : SlackHTTPHandler(
        'hooks.slack.com',
        '/services/T04BV4TC5/B09UXRE5V/VFu6htlQPwKRPyECFyL3GUWK',
        method='POST'
    ),
}

# Set severity levels for handlers
HANDLER_CHOICES['stdout'].setLevel(logging.DEBUG)
HANDLER_CHOICES['stderr'].setLevel(logging.ERROR)
HANDLER_CHOICES['logfile'].setLevel(logging.DEBUG)
HANDLER_CHOICES['suppress'].setLevel(logging.NOTSET)
HANDLER_CHOICES['slack'].setLevel(logging.ERROR)

# Attach formatters to the handlers
time_name_lvl_formatter = logging.Formatter(
    '[%(asctime)s] [%(name)s] [%(levelname)s] %(msg)s'
)
HANDLER_CHOICES['stdout'].setFormatter(time_name_lvl_formatter)
HANDLER_CHOICES['stderr'].setFormatter(time_name_lvl_formatter)
HANDLER_CHOICES['logfile'].setFormatter(time_name_lvl_formatter)

class QueueLogger(object):
    """ Facilitates the creation of an asynchronous log request.

	    This exposes a few functions similar to the core python logging module, 
	    but instead of immediately executing the log request, they pile all
	    requests onto a queue and return immediately.

	    The requests piled in the queue are processed later by worker threads.
	"""

    def __init__(self):
        # Modules can access and customise the following attributes.
        # For e.g. you can change the severity level of this logger
        self.logger = None

    def create_logger(self, name='default', handlers_list=['suppress']):
        """ Set and use a logger with the specified name and handlers. 

            The convention for name is the same as what you would use with
            a regular logging.Logger object. Check the python docs. The 
            recommended convention specifies using the __name__ built-in:
                QueueLogger().create_logger(__name__)
            If name isn't given, the literal 'default' will be used.

            handlers_list must be a list of one or more choices defined in this 
            module's HANDLER_CHOICES dictionary. If handlers_list isn't given,
            the 'suppress' handler will be attached. 

            For sake of maintenance, define all future handlers in this module.
            Append them to HANDLER_CHOICES, and set appropriate severity levels
            and formatting, if applicable.
        """
		
        self.logger = logging.getLogger(name)

        # Don't neglect any logs at the logger level.
        # Let the handlers take care of it.
        self.logger.setLevel(logging.DEBUG)

        # Attach specified handlers
        for handler in handlers_list:
            try:
                self.logger.addHandler(HANDLER_CHOICES[handler])
            except KeyError:
                raise Exception(
                    'Logging handler "{0}" not found!\n'.format(handler)+\
                    'Please use handlers from '+str(HANDLER_CHOICES.keys())\
                )
        
    def critical(self, msg, *args, **kwargs):
        """ Log a message with a CRITICAL severity """
        logging_queue.put([self.logger, logging.CRITICAL, msg, args, kwargs])


    def error(self, msg, *args, **kwargs):
        """ Log a message with an ERROR severity. 

            This method DOES NOT append stack trace information 
            when used for exception handling.
            Use the exception() method instead.
        """
        logging_queue.put([self.logger, logging.ERROR, msg, args, kwargs])


    def warning(self, msg, *args, **kwargs):
        """ Log a message with a WARNING severity """
        logging_queue.put([self.logger, logging.WARNING, msg, args, kwargs])


    def info(self, msg, *args, **kwargs):
        """ Log a message with an INFO severity """
        logging_queue.put([self.logger, logging.INFO, msg, args, kwargs])


    def debug(self, msg, *args, **kwargs):
        """ Log a message with a DEBUG severity """
        logging_queue.put([self.logger, logging.DEBUG, msg, args, kwargs])

    def exception(self, msg, *args, **kwargs):
        """ Log a message with an ERROR severity.
            Also causes exception information to be appended, if any.
        """
        msg = '\n'.join([
            msg, 
            traceback.format_exc()
        ])
        logging_queue.put([self.logger, logging.ERROR, msg, args, kwargs])

def log_item():
    """ Access items from queue, and log them. """
    while True:
        # Block until something is available in queue, and remove it from queue
        logger, severity, msg, args, kwargs = logging_queue.get(True)
        logger.log(severity, msg, *args, **kwargs)


# Start logging anything that's put on the queue
for i in range(NUM_CONSUMER_THREADS):
    t = Thread(target=log_item)
    t.daemon = False
    t.start()

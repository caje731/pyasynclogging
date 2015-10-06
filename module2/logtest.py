#!../bin/python


import time
import StringIO


def testlog():
    ql = _.QueueLogger()
    ql.create_logger(__name__+'.testlog', ['stdout'])
    for i in range(20):
        ql.info(i)

def testlog2():
    ql = _.QueueLogger()
    ql.create_logger(__name__+'.testlog2', ['stdout'])
    for i in range(20):
        ql.info(i)

def teststack():
    import sys
    saved_sysout = sys.stdout
    saved_syserr = sys.stderr
    sys.stdout = StringIO.StringIO()
    sys.stderr = StringIO.StringIO()
    
    import asynclogging as _
    
    ql = _.QueueLogger()
    ql.create_logger(__name__+'.teststack', ['stdout', 'stderr'])
    try:
        raise Exception('Some exception')
    except Exception, exc:
        ql.exception('Trace should be printed below:')
        time.sleep(2)
        a = sys.stderr.getvalue()
        b = sys.stdout.getvalue()
        sys.stdout = saved_sysout
        sys.stderr = saved_syserr
        print 'now printing stderr:', a
        print 'now printing stdout:', b
        #logging.error('Trace printing now: ', exc_info=True)

    _.stop_workers()

if __name__ == '__main__':
    teststack()

#!../bin/python


import asynclogging as _




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

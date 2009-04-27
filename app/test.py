class loginrequired:

    def __init__(self, func):
        self.calls=0
        self.func = func
    def __call__(self, *pargs, **kargs):
        self.calls += 1
	firstarg = pargs[0] if (len(pargs) > 0) else ()
        print "Call to %s with parg %s and karg %s" % (self.func.__name__, pargs, kargs)
        self.func(pargs, kargs)
        
@loginrequired
def testfunc(*pargs, **kargs):
    print "Hi there parg-%s karg-%s" % (pargs,kargs)
    
testfunc('Hello')
testfunc()
testfunc('Hi', 'There', status="Hello")
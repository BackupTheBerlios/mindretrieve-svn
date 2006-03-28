"""A thread pool class
"""

import Queue
import sys
import threading
import traceback

class Runnable:
    """ An abitrary task to be executed. """

    def __init__(self, target=None, args=(), kwargs={}):
        """ Based on threading.Thread.__init__ """
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs

    def run(self):
        """ Based on threading.Thread.run """
        if self.__target:
            self.__target(*self.__args, **self.__kwargs)



class PooledExecutor:
    """ A thread pool class """

    terminateTask = object()    # sentinel object

    def __init__(self, numberOfThreads, daemon_threads=False):
        self.queue = Queue.Queue()

        # setup numberOfThreads
        self.threads = []
        for i in xrange(numberOfThreads):
            th = threading.Thread(target=self._runLoop, name='worker-%d' % i)
            th.id = i
            self.threads.append(th)

        for t in self.threads:
            if daemon_threads:
                t.setDaemon(True)
            t.start()


    def execute(self, command):
        self.queue.put(command)


    def terminate(self):
        """ Signal threads to terminate. Safe to call multiple times. """

        # original trick to start with new empty queue does not work
        # worker threads are waiting on old queue
        #self.queue = Queue.Queue()

        # try to flush the queue
        try:
            while True: self.queue.get_nowait()
        except Queue.Empty:
            pass

        # note it is still possible for new task to get in at this point

        # fill it with len(self.threads) terminateTask objects
        # and wait for the worker threads to end themselves
        for t in self.threads:
            self.queue.put(self.terminateTask)


    def _runLoop(self):
        while True:
            task = self.queue.get()
            if task is self.terminateTask: break
            try:
                task.run()
            except Exception, e:
                # we must protect the worker thread from terminating due
                # to execution error
                traceback.print_exc()


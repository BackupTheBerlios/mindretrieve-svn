"""A thread pool class
"""

import Queue
import threading
import time
import unittest

import threadutil



class Test_PooledExecutor(unittest.TestCase):

    def setUp(self):
        # create daemon threads to reduce chance of hangup in case of
        # test error
        self.pool = threadutil.PooledExecutor(5, True)


    def tearDown(self):

        # try the best to terminate other threads in case of error
        self.pool.terminate()


    def test_PooledExecutor(self):
        """ test PooledExecutor """

        print '\n@test_PooledExecutor'

        self.lock = threading.Lock()
        self.count = 0
        self.exitTicket = Queue.Queue()

        # fill the pool
        for i in xrange(10):
            task = threadutil.Runnable(target=self.work)
            self.pool.execute(task)
        time.sleep(0.5)

        # initially 5 done, 5 queued
        self.lock.acquire()
        self.assertEqual(self.count, 5)
        self.assertEqual(self.pool.queue.qsize(), 5)
        self.lock.release()

        print 55

        # 3 tasks exited, 8 done, 2 queued
        self.exitTicket.put(1)
        self.exitTicket.put(1)
        self.exitTicket.put(1)
        time.sleep(0.5)

        self.lock.acquire()
        self.assertEqual(self.count, 8)
        self.assertEqual(self.pool.queue.qsize(), 2)
        self.lock.release()

        print 82

        # 4 more tasks exited, 10 done, 0 queued
        self.exitTicket.put(1)
        self.exitTicket.put(1)
        self.exitTicket.put(1)
        self.exitTicket.put(1)
        time.sleep(0.5)

        self.lock.acquire()
        self.assertEqual(self.count, 10)
        self.assertEqual(self.pool.queue.qsize(), 0)
        self.lock.release()

        print 100

        # thread still active and waiting
        for th in self.pool.threads:
            self.assert_(th.isAlive(), '%s not alive' % th.getName())

        # terminate the pool, 3 threads still not exited
        self.pool.terminate()
        time.sleep(0.5)

        nAlive = 0
        for th in self.pool.threads:
            if th.isAlive(): nAlive += 1
        self.assertEqual(3, nAlive)

        print 'nAlive', nAlive

        # all threads exited
        self.exitTicket.put(1)
        self.exitTicket.put(1)
        self.exitTicket.put(1)
        time.sleep(0.5)

        for th in self.pool.threads:
            self.assert_(not th.isAlive(), '%s should not alive' % th.getName())


    def work(self):
        """ increment count and wait for exit """

        self.lock.acquire()
        self.count += 1
        self.lock.release()

        # work should finish in no more than 3 seconds
        self.exitTicket.get(True,3)


    def test_exception(self):
        """ Test task throws exception """

        task = threadutil.Runnable(target=self.badWork)
        self.pool.execute(task)
        time.sleep(0.5)

        # thread are still alive and well
        for th in self.pool.threads:
            self.assert_(th.isAlive(), '%s not alive' % th.getName())

        # 5 more bad tasks
        self.pool.execute(task)
        self.pool.execute(task)
        self.pool.execute(task)
        self.pool.execute(task)
        self.pool.execute(task)
        time.sleep(0.5)

        # thread are still alive and well
        for th in self.pool.threads:
            self.assert_(th.isAlive(), '%s not alive' % th.getName())


    def badWork(self):
        raise Exception, 'bad'


if __name__ == '__main__':
    unittest.main()
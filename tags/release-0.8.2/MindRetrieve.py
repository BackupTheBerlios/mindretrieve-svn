#
# A sample service to be 'compiled' into an exe-file with py2exe.
#
# See also
#    setup.py - the distutils' setup script
#    setup.cfg - the distutils' config file for this
#    README.txt - detailed usage notes
#
# A minimal service, doing nothing else than
#    - write 'start' and 'stop' entries into the NT event log
#    - when started, waits to be stopped again.
#
import os, os.path, sys
import win32api
import win32con
import win32serviceutil
import win32service
import win32event
import win32evtlogutil

import sitecustomize                # it seems sitecustomize need to be explicitly imported for a NT service
import run
#from minds import proxy

class MyService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MindRetrieve"
    _svc_display_name_ = "MindRetrieve Engine"
    _svc_deps_ = ["EventLog"]
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        run.main(['','--inproc_stop'])

        win32event.SetEvent(self.hWaitStop)


    def SvcDoRun(self):
        import servicemanager
        ### # Write a 'started' event to the event log...
        ### win32evtlogutil.ReportEvent(self._svc_name_,
        ###                             servicemanager.PYS_SERVICE_STARTED,
        ###                             0, # category
        ###                             servicemanager.EVENTLOG_INFORMATION_TYPE,
        ###                             (self._svc_name_, ''))

        baseDir = self.getBaseDir()
        # below log event under 'Python Service'. How to change the source to MindRetrieve?
        servicemanager.LogInfoMsg('Starting MindRetrieve at [%s]' % baseDir)
        os.chdir(baseDir)

        run.main(['','--start'])

        # wait for beeing stopped...
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)


        # and write a 'stopped' event to the event log.
        win32evtlogutil.ReportEvent(self._svc_name_,
                                    servicemanager.PYS_SERVICE_STOPPED,
                                    0, # category
                                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                                    (self._svc_name_, ''))


    def getBaseDir():
        """ Derive base directory from registry key
            HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\%s(ImagePath)
        """
        # throws pywintypes.error if key not found
        key = "SYSTEM\CurrentControlSet\Services\%s" % MyService._svc_name_
        regkey = win32api.RegOpenKeyEx(win32con.HKEY_LOCAL_MACHINE, key)
        path, typ = win32api.RegQueryValueEx(regkey, 'ImagePath')
        path = path.strip('"')
        path = os.path.split(path)[0]
        return path

    getBaseDir = staticmethod(getBaseDir)


def test():
    """ Sanity test """
    print 'baseDir: [%s]' % MyService.getBaseDir()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['--test', '-test']:
        test()
        sys.exit(-1)
    # Note that this code will not be run in the 'frozen' exe-file!!!
    win32serviceutil.HandleCommandLine(MyService)

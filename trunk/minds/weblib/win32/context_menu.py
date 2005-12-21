# -*- coding: utf-8 -*-

# A sample context menu handler.
# Adds a 'Hello from Python' menu entry to .py files.  When clicked, a
# simple message box is displayed.
#
# To demostrate:
# * Execute this script to register the context menu.
# * Open Windows Explorer, and browse to a directory with a .py file.
# * Right-Click on a .py file - locate and click on 'Hello from Python' on
#   the context menu.

import urllib
import pythoncom
from win32com.shell import shell, shellcon
import win32gui
import win32con

IContextMenu_Methods = ["QueryContextMenu", "InvokeCommand", "GetCommandString"]
IShellExtInit_Methods = ["Initialize"]

#HKCR Key	Affected object types
#* 	All files
#AllFileSystemObjects 	All regular files and file folders
#Folder 	All folders, virtual and filesystem
#Directory 	File folders
#Drive 	Root folders of all system drives
#Network 	Entire network
#NetShare 	All network shares

TYPES = [
    '*',
    'Directory',
    ]
SUBKEY = 'MindRetrieve'

class ShellExtension:
    _reg_progid_ = "MindRetrieve.ShellExtension.ContextMenu"
    _reg_desc_ = "MindRetrieve Shell Extension (context menu)"
    _reg_clsid_ = "{d4193e50-70fa-11da-9808-00123f0d59a8}"

    _com_interfaces_ = [shell.IID_IShellExtInit, shell.IID_IContextMenu]
    _public_methods_ = IContextMenu_Methods + IShellExtInit_Methods

    def Initialize(self, folder, dataobj, hkey):
        print "Init", folder, dataobj, hkey
        self.dataobj = dataobj

    def QueryContextMenu(self, hMenu, indexMenu, idCmdFirst, idCmdLast, uFlags):
        print "QCM", hMenu, indexMenu, idCmdFirst, idCmdLast, uFlags
        # Query the items clicked on
        files = self.getFiles()
        msg =  len(files) > 1 and '&Tag %s files' % len(files) or '&Tag with MindRetrieve'

        idCmd = idCmdFirst
        items = []
        if (uFlags & 0x000F) == shellcon.CMF_NORMAL: # Check == here, since CMF_NORMAL=0
            print "CMF_NORMAL..."
            items.append(msg)
        elif uFlags & shellcon.CMF_VERBSONLY:
            print "CMF_VERBSONLY..."
            items.append(msg + " - shortcut")
        elif uFlags & shellcon.CMF_EXPLORE:
            print "CMF_EXPLORE..."
            items.append(msg + " - normal file, right-click in Explorer")
        elif uFlags & CMF_DEFAULTONLY:
            print "CMF_DEFAULTONLY...\r\n"
        else:
            print "** unknown flags", uFlags
        win32gui.InsertMenu(hMenu, indexMenu,
                            win32con.MF_SEPARATOR|win32con.MF_BYPOSITION,
                            0, None)
        indexMenu += 1
        for item in items:
            win32gui.InsertMenu(hMenu, indexMenu,
                                win32con.MF_STRING|win32con.MF_BYPOSITION,
                                idCmd, item)
            indexMenu += 1
            idCmd += 1

        win32gui.InsertMenu(hMenu, indexMenu,
                            win32con.MF_SEPARATOR|win32con.MF_BYPOSITION,
                            0, None)
        indexMenu += 1
        return idCmd-idCmdFirst # Must return number of menu items we added.


    def InvokeCommand(self, ci):
        mask, hwnd, verb, params, dir, nShow, hotkey, hicon = ci

        files = self.getFiles()
        if not files:
            return

        fname = files[0]
        file_url = urllib.pathname2url(fname)

# 2005-12-20 Test urllib.pathname2url()
#
#>>> urllib.pathname2url(r'c:\tung\wäi')
#'///C|/tung/w%84i'
#>>> urllib.pathname2url(r'\tung\wäi')
#'/tung/w%84i'
#>>> urllib.pathname2url(r'tung\wäi')
#'tung/w%84i'

        # prefer ':' as the drive separator rather than '|'
        if file_url.startswith('///') and file_url[4:5] == '|':
            file_url = file_url.replace('|',':',1)

        if file_url.startswith('//'):
            file_url = 'file:' + file_url
        elif file_url.startswith('/'):
            file_url = 'file://' + file_url
        else:
            # fname is a relative filename? Should not happen!
            file_url = 'file:///' + file_url

        shell.ShellExecuteEx(fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                             lpFile='http://localhost:8052/weblib/_?url=' + file_url,
                             nShow=win32con.SW_NORMAL,
                            )

    def GetCommandString(self, cmd, typ):
        return "&Tag with MindRetrieve"


    def getFiles(self):
        format_etc = win32con.CF_HDROP, None, 1, -1, pythoncom.TYMED_HGLOBAL
        sm = self.dataobj.GetData(format_etc)
        num_files = shell.DragQueryFile(sm.data_handle, -1)
        files = [shell.DragQueryFile(sm.data_handle, i) for i in range(num_files)]
        return files


def DllRegisterServer():
    import _winreg
    for typ in TYPES:
        # e.g. HKEY_CLASSES_ROOT\*\shellex\ContextMenuHandlers\MindRetrieve
        key = _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, "%s\\shellex" % typ)
        subkey = _winreg.CreateKey(key, "ContextMenuHandlers")
        subkey2 = _winreg.CreateKey(subkey, SUBKEY)
        _winreg.SetValueEx(subkey2, None, 0, _winreg.REG_SZ, ShellExtension._reg_clsid_)
    print ShellExtension._reg_desc_, "registration complete."


def DllUnregisterServer():
    import _winreg
    for typ in TYPES:
        try:
            # e.g. HKEY_CLASSES_ROOT\*\shellex\ContextMenuHandlers\MindRetrieve
            key = _winreg.DeleteKey(_winreg.HKEY_CLASSES_ROOT, "%s\\shellex\\ContextMenuHandlers\\%s" % (typ, SUBKEY))
        except WindowsError, details:
            import errno
            if details.errno != errno.ENOENT:
                raise
    print ShellExtension._reg_desc_, "unregistration complete."


if __name__=='__main__':
    from win32com.server import register
    register.UseCommandLine(ShellExtension,
                   finalize_register = DllRegisterServer,
                   finalize_unregister = DllUnregisterServer)

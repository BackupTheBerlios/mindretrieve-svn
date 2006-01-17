"""
A TestRunner for use with the Python unit testing framework. It
generates a HTML report to show the result at a glance.

The simplest way to use this is to invoke its main method. E.g.

    import unittest
    import HTMLTestRunner

    ... define your tests ...

    if __name__ == '__main__':
        HTMLTestRunner.main()

You can also instantiates a HTMLTestRunner object for finer
control.
"""
__author__ = "Wai Yip Tung"
__version__ = "0.5"

# TODO: allow link to custom CSS
# TODO: color stderr

import datetime
import string
import StringIO
import sys
import time
import unittest
from xml.sax import saxutils

TestResult = unittest.TestResult

class OutputRedirector(object):
    """ Wrapper to redirect stdout or stderr """
    def __init__(self, fp):
        self.fp = fp

    def write(self, s):
        self.fp.write(s)

    def writelines(self, lines):
        self.fp.writelines(lines)

    def flush(self):
        self.fp.flush()

# The redirectors below is used to capture output during testing. Output
# sent to sys.stdout and sys.stderr are automatically captured. However
# in some cases sys.stdout is already cached before HTMLTestRunner is
# invoked (e.g. calling logging.basicConfig). In order to capture those
# output, use the redirectors for the cached stream.
#
# e.g.
#   >>> logging.basicConfig(stream=HTMLTestRunner.stdout_redirector)
#   >>>
stdout_redirector = OutputRedirector(sys.stdout)
stderr_redirector = OutputRedirector(sys.stderr)


# ----------------------------------------------------------------------
# Template

STATUS = {
0: 'pass',
1: 'fail',
2: 'error',
}


CSS = """
<style>
body        { font-family: verdana, arial, helvetica, sans-serif; font-size: 80%; }
table       { font-size: 100%; }
pre         { }
h1          { }
.heading    {
    margin-top: 0ex;
    margin-bottom: 1ex;
}
#show_detail_line {
    margin-top: 3ex;
    margin-bottom: 1ex;
}
#result_table {
    width: 80%;
    border-collapse: collapse;
    border: medium solid #777;
}
#result_table td {
    border: thin solid #777;
    padding: 2px;
}
#header_row {
    font-weight: bold;
    color: white;
    background-color: #777;
}
#total_row  { font-weight: bold; }
.passClass  { background-color: #6c6; }
.failClass  { background-color: #c60; }
.errorClass { background-color: #c00; }
.passCase   { color: #6c6; }
.failCase   { color: #c60; font-weight: bold; }
.errorCase  { color: #c00; font-weight: bold; }
.hiddenRow  { display: none; }
.testcase   { margin-left: 2em; }
#btm_filler { margin-top: 50%; }
</style>
"""
CSS_LINK = '<link rel="stylesheet" href="$url" type="text/css">\n'


HTML_TMPL = string.Template(r"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
    <title>$title</title>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    $css
</head>
<body>
<script>
output_list = Array();

/* level - 0:Summary; 1:Failed; 2:All */
function showCase(level) {
    trs = document.getElementsByTagName("tr");
    for (var i = 0; i < trs.length; i++) {
        tr = trs[i];
        id = tr.id;
        if (id.substr(0,2) == 'ft') {
            if (level < 1) {
                tr.className = 'hiddenRow';
            }
            else {
                tr.className = '';
            }
        }
        if (id.substr(0,2) == 'pt') {
            if (level > 1) {
                tr.className = '';
            }
            else {
                tr.className = 'hiddenRow';
            }
        }
    }
}

function showClassDetail(cid, count) {
    var id_list = Array(count);
    var toHide = 1;
    for (var i = 0; i < count; i++) {
        tid0 = 't' + cid.substr(1) + '.' + (i+1);
        tid = 'f' + tid0;
        tr = document.getElementById(tid);
        if (!tr) {
            tid = 'p' + tid0;
            tr = document.getElementById(tid);
        }
        id_list[i] = tid;
        if (tr.className) {
            toHide = 0;
        }
    }
    for (var i = 0; i < count; i++) {
        tid = id_list[i];
        if (toHide) {
            document.getElementById(tid).className = 'hiddenRow';
        }
        else {
            document.getElementById(tid).className = '';
        }
    }
}

function showOutput(id, name) {
    w = window.open("", //url
                    name,
                    "resizable,status,width=800,height=450");
    d = w.document;
    d.write("<pre>");
    d.write(output_list[id]);
    d.write("\n");
    d.write("<a href='javascript:window.close()'>close</a>\n");
    d.write("</pre>\n");
    d.close();
}

</script>

<h1>$description</h1>
<p class='heading'><strong>Time:</strong> $time</p>
<p class='heading'><strong>Status:</strong> $status</p>
<p id='show_detail_line'>Show
<a href='javascript:showCase(0)'>Summary</a>
<a href='javascript:showCase(1)'>Failed</a>
<a href='javascript:showCase(2)'>All</a>
</p>
<table id='result_table'>
<colgroup>
<col align='left' />
<col align='right' />
<col align='right' />
<col align='right' />
<col align='right' />
<col align='right' />
</colgroup>
<tr id='header_row'>
    <td>Class/Test case</td>
    <td>Count</td>
    <td>Pass</td>
    <td>Fail</td>
    <td>Error</td>
    <td>View</td>
</tr>
$tests
<tr id='total_row'>
    <td>Total</td>
    <td>$count</td>
    <td>$Pass</td>
    <td>$fail</td>
    <td>$error</td>
    <td>&nbsp;</td>
</tr>
</table>
<div id='btm_filler' />
</body>
</html>
""")

CLASS_TMPL = string.Template(r"""
<tr class='$style'>
    <td>$name</td>
    <td>$count</td>
    <td>$Pass</td>
    <td>$fail</td>
    <td>$error</td>
    <td><a href="javascript:showClassDetail('$cid',$count)">Detail</a></td>
</tr>
""")

TEST_TMPL = string.Template(r"""
<tr id='$tid' class='$Class'>
    <td class='$style'><div class='testcase'>$name<div></td>
    <td colspan='5' align='center'><a href="javascript:showOutput('$tid', '$name')">$status</a></td>
</tr>
""")

TEST_TMPL_NO_OUTPUT = string.Template(r"""
<tr id='$tid' class='$Class'>
    <td class='$style'><div class='testcase'>$name<div></td>
    <td colspan='5' align='center'>$status</td>
</tr>
""")

TEST_OUTPUT_TMPL = string.Template(r"""
<script>output_list['$id'] = '$output';</script>
""")


# ----------------------------------------------------------------------

class _TestResult(TestResult):
    # note: _TestResult is a pure representation of results.
    # It lacks the output and reporting ability compares to unittest._TextTestResult.

    def __init__(self):
        TestResult.__init__(self)
        self.result = []
        self.stdout0 = None
        self.stderr0 = None


    def startTest(self, test):
        TestResult.startTest(self, test)
        self.outputBuffer = StringIO.StringIO()
        stdout_redirector.fp = self.outputBuffer
        stderr_redirector.fp = self.outputBuffer
        self.stdout0 = sys.stdout
        self.stderr0 = sys.stderr
        sys.stdout = stdout_redirector
        sys.stderr = stderr_redirector


    def complete_output(self):
        """
        Disconnect output redirection and return buffer.
        Safe to call multiple times.
        """
        if self.stdout0:
            sys.stdout = self.stdout0
            sys.stderr = self.stderr0
            self.stdout0 = None
            self.stderr0 = None
        return self.outputBuffer.getvalue()


    def stopTest(self, test):
        # Usually one of addSuccess, addError or addFailure would have been called.
        # But there are some path in unittest that would bypass this.
        # We must disconnect stdout in stopTest(), which is guaranteed to be called.
        self.complete_output()


    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        output = self.complete_output()
        self.result.append((0, test, output, ''))
        sys.stderr.write('.')
        sys.stderr.write(str(test))
        sys.stderr.write('\n')

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        output = self.complete_output()
        self.result.append((2, test, output, self._exc_info_to_string(err, test)))
        sys.stderr.write('E')
        sys.stderr.write(str(test))
        sys.stderr.write('\n')

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        output = self.complete_output()
        self.result.append((1, test, output, self._exc_info_to_string(err, test)))
        sys.stderr.write('F')
        sys.stderr.write(str(test))
        sys.stderr.write('\n')


class HTMLTestRunner:
    """
    """
    def __init__(self, stream=sys.stdout, descriptions=1, verbosity=1, description='A Test'):
        # unittest itself has no good mechanism for user to define a
        # description neither in TestCase nor TestSuite. Allow user to
        # pass in the description as a parameter.

        # note: this is different from unittest.TextTestRunner's
        # 'descrpitions' parameter, which is an integer flag.

        self.stream = stream
        self.startTime = datetime.datetime.now()
        self.description = description
        self.verbosity = verbosity

    def run(self, test):
        "Run the given test case or test suite."
        result = _TestResult()
        test(result)
        self.stopTime = datetime.datetime.now()
        self.generateReport(test, result)
        print >>sys.stderr, '\nTime Elapsed: %s' % (self.stopTime-self.startTime)
        return result

    def sortResult(self, result_list):
        # unittest does not seems to run in any particular order.
        # Here at least we want to group them together by class.
        rmap = {}
        classes = []
        for n,t,o,e in result_list:
            cls = t.__class__
            if not rmap.has_key(cls):
                rmap[cls] = []
                classes.append(cls)
            rmap[cls].append((n,t,o,e))
        r = [(cls, rmap[cls]) for cls in classes]
        return r

    def generateReport(self, test, result):
        rows = []
        npAll = nfAll = neAll = 0
        sortedResult = self.sortResult(result.result)
        for cid, (cls, cls_results) in enumerate(sortedResult):
            # update counts
            np = nf = ne = 0
            for n,t,o,e in cls_results:
                if n == 0: np += 1
                elif n == 1: nf += 1
                else: ne += 1
            npAll += np
            nfAll += nf
            neAll += ne

            row = CLASS_TMPL.safe_substitute(
                style = ne > 0 and 'errorClass' or nf > 0 and 'failClass' or 'passClass',
                name = "%s.%s" % (cls.__module__, cls.__name__),
                count = np+nf+ne,
                Pass = np,
                fail = nf,
                error = ne,
                cid = 'c%s' % (cid+1),
            )
            rows.append(row)

            for tid, (n,t,o,e) in enumerate(cls_results):
                # e.g. 'pt1.1', 'ft1.1', etc
                has_output = bool(o or e)
                tid = (n == 0 and 'p' or 'f') + 't%s.%s' % (cid+1,tid+1)
                name = t.id().split('.')[-1]
                tmpl = has_output and TEST_TMPL or TEST_TMPL_NO_OUTPUT
                row = tmpl.safe_substitute(
                    tid = tid,
                    Class = (n == 0 and 'hiddenRow' or ''),
                    style = n == 2 and 'errorCase' or (n == 1 and 'failCase' or ''),
                    name = name,
                    status = STATUS[n],
                )
                rows.append(row)
                if has_output:
                    if isinstance(o,str):
                        uo = o.decode('latin-1')
                    else:
                        u0 = 0
                    if isinstance(e,str):
                        ue = e.decode('latin-1')
                    else:
                        ue = e
                    row = TEST_OUTPUT_TMPL.safe_substitute(
                        id = tid,
                        output = saxutils.escape(uo+ue) \
                            .replace("'", '&apos;') \
                            .replace('"', '&quot;') \
                            .replace('\\','\\\\') \
                            .replace('\r','\\r') \
                            .replace('\n','\\n'),
                    )
                    rows.append(row)

        report = HTML_TMPL.safe_substitute(
            title = self.description,
            css = CSS,
            description = self.description,
            time = str(self.startTime)[:19],
            status = result.wasSuccessful() and 'Passed' or 'Failed',
            tests = ''.join(rows),
            count = str(npAll+nfAll+neAll),
            Pass = str(npAll),
            fail = str(nfAll),
            error = str(neAll),
        )
        self.stream.write(report.encode('utf8'))


##############################################################################
# Facilities for running tests from the command line
##############################################################################

class TestProgram(unittest.TestProgram):
    """
    A variation of the unittest.TestProgram. Please refer to the base
    class for command line parameters.
    """
    # TODO: unittest.TestProgram.createTests() is useful. On the other
    #   hand unittest.TestProgram's commandline parameters may not be
    #   sufficient for HTMLTestRunner. (want title, CSS, etc.)

    def runTests(self):
        """ Pick HTMLTestRunner as the default test runner. """
        if self.testRunner is None:
            self.testRunner = HTMLTestRunner(verbosity=self.verbosity)
        unittest.TestProgram.runTests(self)

main = TestProgram


##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    main(module=None)

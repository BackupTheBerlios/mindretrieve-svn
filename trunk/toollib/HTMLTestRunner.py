import datetime
import time
import string
import sys
import unittest

TestResult = unittest.TestResult


class _TextTestResult(TestResult):

    def __init__(self, stream, descriptions, verbosity):
        TestResult.__init__(self)
        self.stream = stream
        self.descriptions = descriptions
        self.result = []
        
    def getDescription(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):
        TestResult.startTest(self, test)
#        if self.showAll:
#            self.stream.write(self.getDescription(test))
#            self.stream.write(" ... ")

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        self.result.append((0, test, ''))

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        self.result.append((2, test, self._exc_info_to_string(err, test)))

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        self.result.append((1, test, self._exc_info_to_string(err, test)))


class HTMLTestRunner:
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    def __init__(self, stream=sys.stderr, descriptions=1, verbosity=1):
        self.stream = stream
        self.descriptions = descriptions
        self.verbosity = verbosity

    def _makeResult(self):
        return _TextTestResult(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        "Run the given test case or test suite."

        result = self._makeResult()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        self.generateReport(startTime, stopTime, result)
        return result
        
    def sortResult(self, result_list):
        rmap = {}
        classes = []
        for n,t,e in result_list:
            cls = t.__class__
            if not rmap.has_key(cls):
                rmap[cls] = []
                classes.append(cls)
            rmap[cls].append((n,t,e))           
        r = [(cls, rmap[cls]) for cls in classes]
        return r
        
    def generateReport(self, startTime, stopTime, result):

        rows = []
        npAll = nfAll = neAll = 0
        sortedResult = self.sortResult(result.result)
        for cid, (cls, cls_results) in enumerate(sortedResult):
            # update counts
            np = nf = ne = 0            
            for n,t,e in cls_results:
                if n == 0: np += 1
                elif n == 1: nf += 1
                else: ne += 1
            npAll += np                
            nfAll += nf                
            neAll += ne
            style = ne > 0 and 'error' or nf > 0 and 'fail' or 'pass'

            row = CLASS_TMPL.safe_substitute(dict(
                style = style,
                name = "%s.%s" % (cls.__module__, cls.__name__),
                count = np+nf+ne,
                Pass = np,
                fail = nf,
                error = ne,
                cid = 'c%s' % (cid+1),
            ))
            rows.append(row)
            
            for tid, (n,t,e) in enumerate(cls_results):
                # e.g. 'pt1.1', 'ft1.1', etc
                tid = (n == 0 and 'p' or 'f') + 't%s.%s' % (cid+1,tid+1)
                style = n == 2 and 'error' or (n == 1 and 'fail' or 'pass')
                name = t.id().split('.')[-1]
                row = TEST_TMPL.safe_substitute(dict(
                    tid = tid,
                    Class = (n == 0 and 'hiddenRow' or ''),
                    style = style,
                    name = name,
                    status = STATUS[n],
                ))
                rows.append(row)
                row = TEST_OUTPUT_TMPL.safe_substitute(dict(
                    id = tid+'.out',
                    output = 'xyz',
                ))
                rows.append(row)
                    
        startTime = datetime.datetime.fromtimestamp(startTime)
        print HTML_TMPL.safe_substitute(dict(
            title = name,
            css = CSS,
            description = name,
            time = startTime.isoformat()[:19],
            status = result.wasSuccessful() and 'Success' or 'Fail',
            tests = ''.join(rows),
            count = str(npAll+nfAll+neAll),
            Pass = str(npAll),
            fail = str(nfAll),
            error = str(neAll),            
        ))

STATUS = {
0: 'pass',
1: 'fail',
2: 'error',
}

# Template structure
#
# HTML
#     CSS  
#     MODULES...
#         TESTS...    


CSS = """
<style>
body        { font-family: verdana, arial, helvetica, sans-serif; font-size: 80%; }
table       { font-size: 100% }
th          { font-weight: bold; }
.col1       { text-align: left; }    
.col2       { text-align: center; }    
.col3       { text-align: center; }    
.col4       { text-align: right; }    
.col5       { text-align: right; }    
.pass       { background-color: #6c6; }
.fail       { background-color: #c60; }
.error      { background-color: #c00; }
.hiddenRow  { display: none; }
</style>
"""
CSS_LINK = '<link rel="stylesheet" href="$url" type="text/css">\n'


HTML_TMPL = string.Template("""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
    <title>$title</title>
    $css
</head>
<body>
<script>
/* level - 0:Summary; 1:Failed; 2:All */
function showCase(level) {
    trs = document.getElementsByTagName("tr");
    for (var i = 0; i < trs.length; i++) {
        tr = trs[i];
        id = tr.id;
        output = id.slice(-3) == 'out';
        if (id.substr(0,2) == 'ft') {
            if (level < 1) {
                tr.className = 'hiddenRow';
            }
            else {
                if (!output) tr.className = '';
            }
        }
        if (id.substr(0,2) == 'pt') {
            if (level > 1) {
                if (!output) tr.className = '';
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
            document.getElementById(tid + '.out').className = 'hiddenRow';
        }
        else {
            document.getElementById(tid).className = '';
        }
    }
}

function showDetail(tid) {
    tid1 = tid + '.out';
    oe = document.getElementById(tid1);
    if (oe.className)
        oe.className = '';
    else
        oe.className = 'hiddenRow';
}
</script>

<p>$description</p>
<p>Time: $time</p>
<p>Status: $status</p>
Show 
<a href='javascript:showCase(0)'>Summary</a> 
<a href='javascript:showCase(1)'>Failed</a> 
<a href='javascript:showCase(2)'>All</a>
<table border='1' cellspacing='0' cellpadding='2'>
<colgroup>
<col class='col1' align='left' />
<col class='col2' align='right' />
<col class='col3' align='right' />
<col class='col4' align='right' />
<col class='col5' align='right' />
<col class='col6' align='right' />
</colgroup>
<tr>
    <th>Class/Test case</th>
    <th>Count</th>
    <th>Pass</th>
    <th>Fail</th>
    <th>Error</th>
    <th>View</th>
</tr>
$tests
<tr>
    <th>Total</th>
    <th>$count</th>
    <th>$Pass</th>
    <th>$fail</th>
    <th>$error</th>
    <th>&nbsp;</th>
</tr>
</table>
</body>
</html>
""")

CLASS_TMPL = string.Template("""
<tr>
    <td class='$style'>$name</td>
    <td>$count</td>
    <td>$Pass</td>
    <td>$fail</td>
    <td>$error</td>
    <td><a href="javascript:showClassDetail('$cid',$count)">Detail</a></td>
</tr>
""")

TEST_TMPL = string.Template("""
<tr id='$tid' class='$Class'>
    <td style='margin-left:2em;'><div class='$style'>$name<div></td>
    <td>&nbsp</td>
    <td colspan='3' align='center'>$status</td>
    <td><a href="javascript:showDetail('$tid')">Detail</a></td>
</tr>
""")

TEST_OUTPUT_TMPL = string.Template("""
<tr id='$id' class='hiddenRow'>
    <td colspan='6'>
    <pre>$output</pre>
    </td>
</tr>
""")


##############################################################################
# Facilities for running tests from the command line
##############################################################################

class TestProgram(unittest.TestProgram):
    """ 
    A variation of the unittest.TestProgram. Please refer to the base 
    class for command line parameters.
    """
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

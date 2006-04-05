import logging
import os
import sys
from xml.sax import saxutils

from minds.config import cfg
from minds.cgibin.util import request
from minds.cgibin.util import response
from minds import upgrade_checker

log = logging.getLogger('cgi.upgrde')


def main(rfile, wfile, env):
    req = request.Request(rfile, env)
    path = env.get('PATH_INFO', '')
    errors = []

    # initialize current state
    state = upgrade_checker._getSystemState()
    form = {
        'feed_url': state.feed_url,
        'fetch_frequency': str(state.fetch_frequency),
        'current_version': state.current_version,
        'upgrade_info': state.upgrade_info,
    }

    log.debug('%s %s' % (path, str(state.upgrade_info)))

    if path == '/dismiss':
        upgrade_checker.set_config(dismiss=True)
        url = req.param('url','')
        if url:
            response.redirect(wfile, url)
        else:
            response.redirect(wfile, '/updateParent')
        return

    elif path == '/check':
        # 2006-04-02 23:50:26 DEBUG>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        #state.current_version = '0.1' # assume it is an older version
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        upgrade_checker.pollUpgradeInfo(force_check=True)
        form['upgrade_info'] = state.upgrade_info

        # hack, do not redirect to /setting
        # we want the /check in the URL so that we can tell user no new version
        #response.redirect(wfile, '/upgrade/setting')

    elif req.method == 'POST':
        _freq_str = req.param('fetch_frequency',str(upgrade_checker.DEFAULT_FETCH_FREQUENCY))
        if not _freq_str:
            _freq_str = '0'
        try:
            frequency = int(_freq_str)
            if frequency < 0:
                raise ValueError()
        except ValueError:
            form['fetch_frequency'] = _freq_str
            errors = ['Please enter a positive integer for check frequency.']
        else:
            upgrade_checker.set_config(frequency=int(_freq_str))
            form['fetch_frequency'] = str(state.fetch_frequency)

    renderer = UpgradeRenderer(wfile)
    renderer.setLayoutParam('MindRetrieve - Upgrade Notification Setting')
    renderer.output(errors, form, path)


#------------------------------------------------------------------------

class UpgradeRenderer(response.WeblibLayoutRenderer):

    TEMPLATE_FILE = 'upgradeSetting.html'
    """ Date: 2006-04-02 21:07:22
    con:feed_url
    con:frequency
    con:upgrade_notification
            con:link
                    con:title
                    con:summary
    """
    def render(self, node, errors, form, path):
        if errors:
            escaped_errors = map(saxutils.escape, errors)
            node.error.message.raw = '<br />'.join(escaped_errors)
        else:
            node.error.omit()
        feed_url = form.get('feed_url','')
        node.feed_url.atts['href'] = feed_url
        node.feed_url.content = feed_url or 'n/a'
        node.fetch_frequency.atts['value'] = form.get('fetch_frequency','')
        upgrade_info = form.get('upgrade_info',None)
        if not upgrade_info:
            if path == '/check':
                node.upgrade_notification.content = 'Version %s is up-to-date' % (form.get('current_version',''))
            else:
                node.upgrade_notification.omit()
        else:
            node.upgrade_notification.link.atts['href']     = upgrade_info.url
            node.upgrade_notification.link.title.content    = upgrade_info.title
            node.upgrade_notification.link.summary.content  = upgrade_info.summary


if __name__ == "__main__":
    main(sys.stdin, sys.stdout, os.environ)

"""
Check the MindRetrieve upgrade feed at certain interval.
Determine if a new version is available.
"""
import datetime
import logging
import re
import sys

#from toollib import feedparser
from minds.config import cfg
from minds.util import dateutil

log = logging.getLogger('upgrade')

NOTIFICATION_URL = "http://www.mindretrieve.net/release/upgrade.xml"
DEFAULT_FETCH_FREQUENCY = 10

# match ther version number, e.g.
#   Version 0.8.2
#   Version 0.8.2.03
#   Version 0.8.2-XP
#   0.18.2 version
version_re = re.compile("\d+\.\d+\.\d+[^\s]*")

today_func = datetime.date.today

class State(object):
    """ Represent the upgrade state persisted. """
    def __init__(self):
        self.fetch_date = today_func()                  # date of previous fetch
        self.next_fetch = today_func()                  # date of next scheduled fetch
        self.fetch_frequency = DEFAULT_FETCH_FREQUENCY  # no. of days
        self.last_entry_date = ''                       # date str from the entry in the feed (UTC)
        self.current_version = ''
        self.upgrade_info = None                        # UpgradeInfo or None

    def load(self):
        # note: this is designed to work even if all upgrade.* fields are not specified
        self.current_version = cfg.get('_system.version')
        self.fetch_date      = cfg.get('upgrade.fetch_date','')
        self.fetch_frequency = cfg.getint('upgrade.fetch_frequency',10)
        self.last_entry_date = cfg.get('upgrade.last_entry_date','')
        try:
            self.fetch_date = dateutil.parse_iso8601_date(self.fetch_date).date()
        except ValueError:
            self.fetch_date = today_func()
            self.next_fetch = today_func()
        else:
            self.next_fetch = self.fetch_date + datetime.timedelta(self.fetch_frequency)

    def save(self):
        # TODO
        pass

    def __repr__(self):
        return '(%s) fetch %s(%s) last fetch %s' % (
            self.upgrade_info,
            self.fetch_date,
            self.fetch_frequency,
            self.last_entry_date)


class UpgradeInfo(object):

    def __init__(self, version, title, summary, url):
        self.version = version
        self.title   = title
        self.summary = summary
        self.url = url

    def __repr__(self):
        return '%s %s %s %s' % (self.version, self.title, self.summary, self.url)


# global system state
system_state = None

def _getSystemState():
    """ Lazy initialization of system state """
    global system_state
    if not system_state:
        system_state = State()
        system_state.load()
    return system_state


def _fetch(feed_url):
    """
    Fetch from feed
    @return status, updated_date_str, UpgradeInfo
    """
    d = parsefeed(feed_url)
#    d = feedparser.parse(feed_url)

    status = d.get('status','n/a')      # note not defined when feed from string
    entries = d.get('entries',[])
    if not entries:
        return status, None, None

    entry = entries[0]
    title = entry.get('title','')
    updated = entry.get('updated','')
    summary = entry.get('summary','')
    url = entry.get('link','')
    m = version_re.search(title)
    if m:
        version = m.group(0)
    else:
        version = ''

    return status, updated, UpgradeInfo(version, title, summary, url)


def _checkUpgrade(state, today, feed_url):
    """
    1. Fetch from feed.
    2. Update fetch_date, next_fetch.
    3. Set upgrade_info and if a new version is available.
    """
    status, new_date, new_update_info = _fetch(feed_url)
    state.fetch_date = today
    if new_update_info:
        state.next_fetch = state.fetch_date + datetime.timedelta(state.fetch_frequency)
    else:
        # the fetch is failed, try again next day
        state.next_fetch = state.fetch_date + datetime.timedelta(1)

    log.info('Upgrade feed status: %s next %s [%s]' % (status, state.next_fetch, NOTIFICATION_URL))
    state.save()

    if not new_update_info:
        return  # fetch failed

    if state.last_entry_date and state.last_entry_date >= new_date:
        log.debug('Feed ignored. Old date: %s' % new_date)
        return  # entry already seen

    state.last_entry_date = new_date

    if state.current_version >= new_update_info.version:
        log.debug('Feed ignored. Old Version: %s' % new_update_info.version)
        return  # no newer version (e.g. after a fresh install of latest)

    state.upgrade_info = new_update_info


def pollUpgradeInfo(state=None, today_func=today_func, feed_url=NOTIFICATION_URL):
    """
    TODO
    """
    state = state or _getSystemState()

    today = today_func()
    if today >= state.next_fetch:
        _checkUpgrade(state, today, feed_url)

    return state.upgrade_info


def set_config(state=None, frequency=None, dismiss=False):
    state = state or _getSystemState()
    if frequency is not None:
        state.fetch_frequency = frequency
        state.save()
    if dismiss:
        state.upgrade_info = None

# ------------------------------------------------------------------------
# 2006-04-02 While we are evaluating the Universal Feed Parser
# (http://feedparser.org/) we find that it update sgmllib with various
# fix. Since we depends on sgmllib and we have also made our own fix, it
# is deemed too risky to introduce the Universal Feed Parser at this
# point. Instead we will simulate its function here.

import urlparse
import urllib2
import xml.dom
from xml.dom.minidom import parse, parseString


def _getAttribute(entryElem ,tag, attr):
    elems = entryElem.getElementsByTagName(tag)
    if not elems:
        return ''
    elem = elems[0]
    return elem.getAttribute(attr)


def _getElemText(entryElem ,tag):
    elems = entryElem.getElementsByTagName(tag)
    if not elems:
        return ''
    elem = elems[0]
    return ''.join(t.data for t in elem.childNodes if t.nodeType==xml.dom.Node.TEXT_NODE)


def parsefeed(url_or_data):
    """ A minial replacement of feedparser.parse() """

    if not url_or_data:
        return  { 'entries': [] }

    # assume url_or_data is text data
    data = url_or_data
    status = None

    # use this 2 tests to seet it is indeed an URL
    if '\n' not in url_or_data:
        scheme, netloc = urlparse.urlsplit(url_or_data)[:1]
        if scheme and netloc:
            resp = urllib2.urlopen(url_or_data)
            status = resp.info()['status']
            data = resp.read(1000000)

    entries = []
    dom = parseString(data)
    for entryElem in dom.getElementsByTagName('entry'):
        entry = {}
        entry['title'] = _getElemText(entryElem ,'title')
        entry['updated'] = _getElemText(entryElem ,'updated')
        entry['summary'] = _getElemText(entryElem ,'summary')
        entry['link'] = _getAttribute(entryElem ,'link', 'href')
        entries.append(entry)

    if status:
        return { 'status': status, 'entries': entries }
    else:
        return { 'entries': entries }


# ------------------------------------------------------------------------

def main(argv):
    logging.getLogger().setLevel(logging.DEBUG)
    print pollUpgradeInfo()


if __name__ =='__main__':
    main(sys.argv)
""" Utility for building web page that shows a long list in multiple pages.

It performs the necessary arithmetics.
Indexes are 0 based as used in sequence slicing.
"""

class PageMeter:

  def __init__(self, start, total, page_size, page_window_size=10):

    if total < 0: raise ValueError, "total should must be non-negative integer"
    if page_size <= 0: raise ValueError, "page_size must be positive integer"
    if page_window_size <= 0: raise ValueError, "page_window_size must be positive integer"

    # we really need some abbreviation for "self" here
    s = self


    # input parameters
    s.start = start
    s.total = total
    s.page_size = page_size
    s.page_window_size = page_window_size


    # start (adjusted), end and page
    s.start = max(0, s.start)           # begin stopper
    s.start = min(s.start, s.total-1)   # end stopper
    if s.total == 0: s.start = 0        # special case when total == 0

    s.page  = s.start / s.page_size
    s.start = s.page * page_size        # align start as multiple of page_size

    s.end = s.start + page_size
    s.end = min(s.end, total)           # end stopper


    # total_page
    if s.total > 0:
        s.total_page = (s.total - 1) / s.page_size + 1
    else:
        s.total_page = 1   # special case when total==0


    # previous and next page
    s.prev = None
    if s.page > 0:
        s.prev = (s.page-1) * s.page_size

    s.next = (s.page+1) * s.page_size
    if s.next >= s.total:
        s.next = None


    # setup page window
    s.page_window_start = s.page - s.page_window_size
    s.page_window_start = max(0, s.page_window_start)           # begin stopper

    s.page_window_end = s.page + s.page_window_size + 1
    s.page_window_end = min(s.total_page, s.page_window_end)    # end stopper



  def __str__(self):

    """ This is the documentation and test helper for PageMeter! """

    return "Item %d-%d/%d | prev %s page %d/%d next %s | Page <%s-%s> | page size %d" % (
        self.start,
        self.end,
        self.total,
        self.prev,
        self.page,
        self.total_page,
        self.next,
        self.page_window_start,
        self.page_window_end,
        self.page_size,
    )

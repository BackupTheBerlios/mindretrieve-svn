"""
"""

def render(node, numIndexed, numQueued, date):
    node.numIndexed.content = str(numIndexed)
    node.numQueued.content = str(numQueued)
    node.time_stamp.content = date

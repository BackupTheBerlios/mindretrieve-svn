"""HTMLTemplate - A fast, powerful, easy-to-use HTML templating system.

See Manual.txt for documentation.
"""

# HTMLTemplate - A fast, powerful, easy-to-use HTML templating system.
#
# Copyright (C) 2004 HAS <hamish.sanderson@virgin.net>
#
# This library is free software; you can redistribute it and/or modify it under 
# the terms of the GNU Lesser General Public License as published by the Free 
# Software Foundation; either version 2.1 of the License, or (at your option) 
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more 
# details.
#
# You should have received a copy of the GNU Lesser General Public License 
# along with this library; if not, write to the Free Software Foundation, Inc., 
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA


__all__ = ['ParseError', 'Node', 'Template']

from HTMLParser import HTMLParser
from keyword import kwlist
import re


#################################################
# SUPPORT
#################################################

def renderAtts(atts):
    result = ''
    for name, value in atts:
        if value is None:
            result += ' ' + name
        elif '"' in value:
            result += " %s='%s'" % (name, value)
        else:
            result += ' %s="%s"' % (name, value)
    return result


def defaultEncoder(txt):
    return txt.replace('&', '&amp;').replace(
            '<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def defaultDecoder(txt):
    return txt.replace('&quot;', '"').replace(
            '&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')


#################################################
# TEMPLATE PARSER
#################################################

class ParseError(Exception):
    """A template parsing error."""
    pass


class ElementCollector:

    def __init__(self, *args):
        self.nodeType, self.nodeName, self.tagName, self.atts, \
                self.isEmpty, self.omitTags, self.shouldDelete = args
        self.content = ['']
        self.elementNames = {}
        self.__depth = 1
    
    def incDepth(self):
        self.__depth += 1
        
    def decDepth(self):
        self.__depth -= 1
        
    def isComplete(self):
        return self.__depth < 1
        
    def addText(self, txt):
        self.content[-1] += txt
        
    def addElement(self, node, nodeType, nodeName):
        self.content.extend([node, ''])
        self.elementNames[nodeName] = nodeType


class Parser(HTMLParser):

    __specialAttValuePattern = re.compile('(-)?(con|rep|sep|del):(.*)')
    __validNodeNamePattern = re.compile('[a-zA-Z][_a-zA-Z0-9]*')
    __invalidNodeNames = kwlist + [
            'content', 'raw', 'atts', 'omittags', 'omit', 'repeat', 'render']
    
    def __init__(self, attribute, encoder, decoder):
        HTMLParser.__init__(self)
        self.__specialAttributeName = attribute
        self.__encoder = encoder
        self.__decoder = decoder
        self.__outputStack = [
                ElementCollector('tem', '', None, None, False, False, False)]
    
    def __isSpecialTag(self, atts, specialAttName):
        for name, value in atts:
            if name == specialAttName:
                value = self.__specialAttValuePattern.match(value)
                if value:
                    atts = dict(atts)
                    del atts[specialAttName]
                    omitTags, nodeType, nodeName = value.groups()
                    return True, nodeType, nodeName, omitTags, atts
        return False, '', '', False, renderAtts(atts)
    
    def __startTag(self, tagName, atts, isEmpty):
        node = self.__outputStack[-1]
        if node.shouldDelete:
            isSpecial = 0
        else:
            isSpecial, nodeType, nodeName, omitTags, atts = \
                    self.__isSpecialTag(atts, self. __specialAttributeName)
        if isSpecial:
            if nodeType != 'del' and (
                    not self.__validNodeNamePattern.match(nodeName) 
                    or nodeName in self.__invalidNodeNames):
                raise ParseError, "Invalid node name: %r" % nodeName
            shouldDelete = nodeType == 'del'
            if node.elementNames.has_key(nodeName):
                if node.elementNames[nodeName] == nodeType:
                    shouldDelete = True
                elif nodeType != 'sep':
                    raise ParseError, ("Invalid node name: %s:%s " 
                            "(node %s:%s already found).") % (nodeType,  
                            nodeName, node.elementNames[nodeName], nodeName)
            self.__outputStack.append(ElementCollector(nodeType, nodeName, 
                    tagName, atts, isEmpty, omitTags, shouldDelete))
        else:
            if node.tagName == tagName:
                node.incDepth()
            if not node.shouldDelete:
                if isEmpty:
                    endOfOpenTag = ' />'
                else:
                    endOfOpenTag = '>'
                node.addText('<' + tagName + atts + endOfOpenTag)
    
    def __hasCompletedElement(self, element, parent):
        if element.isEmpty:
            content = []
        else:
            content = element.content
        if element.nodeType in ['con', 'rep']:
            node = makeNode(
                    element.nodeType, element.nodeName, element.tagName, 
                    element.atts, content, self.__encoder, self.__decoder)
            if element.omitTags:
                node.omittags()
            parent.addElement(node, element.nodeType, element.nodeName)
        else: # element.nodeType == 'sep'
            # Add this separator to its repeater
            for node in parent.content[1::2]:
                if node._nodeName == element.nodeName:
                    if node._nodeType != 'rep':
                        raise ParseError, ("Can't process separator node "
                                "'sep:%s': repeater node 'rep:%s' wasn't "
                                "found. Found node '%s:%s' instead.") % (
                                element.nodeName, element.nodeName, 
                                element.nodeType, element.nodeName)
                    if element.omitTags:
                        if content:
                            node._sep = content[0]
                        else:
                            node._sep = ''
                    else:
                        if content:
                            node._sep = '<%s%s>%s</%s>' % (element.tagName, 
                                    renderAtts(element.atts), 
                                    content[0], element.tagName)
                        else:
                            node._sep = '<%s%s />' % (element.tagName, 
                                    renderAtts(element.atts))
                    return
            raise ParseError, ("Can't process separator node 'sep:%s' in node " 
                    "'%s:%s': repeater node 'rep:%s' wasn't found.") % (
                    element.nodeName, parent.nodeType, parent.nodeName, 
                    element.nodeName)
    
    def __endTag(self, tagName, isEmpty):
        node = self.__outputStack[-1]
        if node.tagName == tagName:
            node.decDepth()
        if node.isComplete():
            self.__outputStack.pop()
            if not node.shouldDelete:
                parent = self.__outputStack[-1]
                self.__hasCompletedElement(node, parent)
        elif not isEmpty:
            node.addText('</%s>' % tagName)

    def __addText(self, txt):
        self.__outputStack[-1].addText(txt)
    
    # event handlers

    def handle_startendtag(self, tagName, atts):
        self.__startTag(tagName, atts, True)
        self.__endTag(tagName, True)

    def handle_starttag(self, tagName, atts):
        self.__startTag(tagName, atts, False)

    def handle_endtag(self, tagName):
        self.__endTag(tagName, False)

    def handle_charref(self, txt):
        self.__addText('&#%s;' % txt)

    def handle_entityref(self, txt):
        self.__addText('&%s;' % txt)

    def handle_data(self, txt):
        self.__addText(txt)

    def handle_comment(self, txt):
        self.__addText('<!--%s-->' % txt)

    def handle_decl(self, txt):
        self.__addText('<!%s>' % txt)

    def handle_pi(self, txt):
        self.__addText('<?%s?>' % txt)
    
    def result(self):
        element = self.__outputStack.pop()
        if element.nodeType != 'tem':
            raise ParseError, ("Can't complete template: node '%s:%s' wasn't "
                    "correctly closed.") % (element.nodeType, element.nodeName)
        if len(element.content) == 1:
            raise ParseError, "No special %r attributes were found." % (
                    self. __specialAttributeName)
        return element.content


#################################################
# OBJECT MODEL CLASSES
#################################################

class CloneNode(object):
    """Makes cloned nodes."""
    def __init__(self, node):
        self.__dict__ = node.__dict__.copy()
        self.__class__ = node.__class__

class Node:
    """Abstract base class for template nodes; used for type checking when 
       user replaces an existing template node with a new one.
    """
    pass

class Container(Node):
    """A Container node has a one-to-one relationship with the node that 
       contains it.
    """
    
    _nodeType = 'con'
    
    def __init__(self, nodeName, tagName, atts):
        self._nodeName = nodeName
        self._atts = dict(atts) # On cloning, shallow copy this dict.
        if isinstance(self, NullContent):
            self.__startTag = '<%s%%s />' % tagName
            self.__endTag = ''
        else:
            self.__startTag = '<%s%%s>' % tagName
            self.__endTag = '</%s>' % tagName
        self.__omitTags = False
        self._omit = False
    
    def _clone(self):
        clone = CloneNode(self)
        clone._atts = self._atts.copy()
        return clone
    
    def _renderNode(self, collector):
        if self.__omitTags:
            self._renderContent(collector)
        else:
            collector.append(self.__startTag % renderAtts(self._atts.items()))
            self._renderContent(collector)
            collector.append(self.__endTag)

    def _render(self, collector):
        if not self._omit:
            self._renderNode(collector)
    
    def __attsGet(self):
        return Attributes(self._atts)
    
    def __attsSet(self, val):
        self._atts = {}
        atts = Attributes(self._atts)
        for name, value in val.items():
            atts[name] = value
    
    atts = property(__attsGet, __attsSet, 
            doc="Get this element's tag attributes.")
    
    def omittags(self):
        """Don't render this element's tag(s)."""
        self.__omitTags = True
    
    def omit(self):
        """Don't render this element."""
        self._omit = True


class Repeater(Container):
    """A Repeater node has a one-to-many relationship with the node that
       contains it.
    """
    
    _nodeType = 'rep'
    
    def __init__(self, nodeName, tagName, atts):
        self._sep = '\n'
        self.__renderedContent = [] # On cloning, shallow-copy this list.
        Container.__init__(self, nodeName, tagName, atts)
        
    _fastClone = Container._clone
    
    def _clone(self):
        clone = Container._clone(self)
        clone.__renderedContent = self.__renderedContent[:]
        return clone
    
    def _render(self, collector):
        if not self._omit:
            collector.extend(self.__renderedContent[1:])
    
    def repeat(self, fn, list, *args):
        """Render an instance of this node for each item in list."""
        self.__renderedContent = collector = [] # replaces any previous content
        for item in list:
            clone = self._fastClone()
            fn(clone, item, *args)
            if not clone._omit:
                collector.append(clone._sep)
                clone._renderNode(collector)

##

class Attributes:
    """Public facade for modifying a node's tag attributes."""
    
    __attNamePattern = re.compile('^[a-zA-Z_][-.:a-zA-Z_0-9]*$')
    
    def __init__(self, atts):
        self.__atts = atts
    
    def __getitem__(self, name):
        return self.__atts[name]
        
    def __setitem__(self, name, val):
        try:
            if not self.__attNamePattern.match(name): # Note: this 
            # will throw a TypeError if 'name' is not string/unicode.
                raise KeyError, "bad name."
            if val != None:
                if not isinstance(val, basestring):
                    raise TypeError, "bad value: %r" % val
                if '"' in val and "'" in val:
                    raise ValueError, "value %r contains " \
                            "both single and double quotes." % val
            self.__atts[name] = val
        except Exception, e:
            msg = str(e)
            if not isinstance(name, basestring):
                msg = "bad name."
            raise e.__class__, "Can't set tag attribute %r: %s" % (name, msg)
        
    def __delitem__(self, name):
        del self.__atts[name]
    
    def __repr__(self):
        return '<Attributes [%s]>' % renderAtts(self.__atts.items())[1:]


#######

class Content(object):
    def _printStructure(self, indent):
        print indent + self._nodeType + ':' + self._nodeName

##

class NullContent(Content):
    """Represents an empty HTML element's non-existent content."""
    
    def _renderContent(self, collector):
        pass


class PlainContent(Content):
    """Represents a non-empty HTML element's content where it contains plain 
       text/markup only.
    """
    
    def __init__(self, content, encoder, decoder):
        self.raw = content # Get/Set this element's content as raw markup;
        # use with care.
        self.__encode = encoder
        self.__decode = decoder
        
    def _renderContent(self, collector):
        collector.append(self.raw)
    
    def __contentGet(self): return self.__decode(self.raw)
    def __contentSet(self, txt): self.raw = self.__encode(txt)
    content = property(__contentGet, __contentSet, 
            doc="Get/Set this element's content as escaped text.")


class RichContent(Content):
    """Represents a non-empty HTML element's content where it contains other 
       Container/Repeater nodes.
    """
    
    __validIdentifierPattern = re.compile('^[a-zA-Z_][a-zA-Z_0-9]*$')
    
    # KLUDGE: The following line keeps Python 2.3 sweet while it instantiates 
    # instances of this class; without it, the process crashes hard as 
    # __init__ conflicts with __setattr__.
    __nodesDict = {}
    
    def __init__(self, content):
        self.__nodesList = content # On cloning, deep copy this list.
        self.__nodesDict = dict(
                [(node._nodeName, node) for node in content[1::2]]) # (On clon-
        # ing: replace with a new dict built from cloned self.__nodesList.)
    
    def _initRichClone(self, clone):
        clone.__nodesDict = {}
        L = clone.__nodesList = self.__nodesList[:]
        for i in range(1, len(L), 2):
            clone.__nodesDict[L[i]._nodeName] = L[i] = L[i]._clone()
        return clone
    
    def _renderContent(self, collector):
        L = self.__nodesList
        collector.append(L[0])
        for i in range(1, len(L), 2):
            L[i]._render(collector)
            collector.append(L[i + 1])
    
    def _printStructure(self, indent):
        Content._printStructure(self, indent)
        [node._printStructure(indent + '\t') 
                for node in self.__nodesList[1::2]]
    
    def __getattr__(self, name):
        if self.__nodesDict.has_key(name):
            return self.__nodesDict[name]
        else:
            raise AttributeError , "%s instance has no attribute %r." % (
                    self.__class__.__name__, name)
    
    def __setattr__(self, name, value):
        if self.__nodesDict.has_key(name):
            if not isinstance(value, Node):
                # Note: This type check is to catch careless user mistakes like
                # 'node.foo = "text"' instead of  'node.foo.content = "text"'
                raise TypeError, ("Can't replace node '%s:%s': value isn't a "
                        "Node object.") % (self.__nodesDict[name]._nodeType,
                         self.__nodesDict[name]._nodeName)
            value = value._clone() 
            value._nodeName = name
            idx = self.__nodesList.index(self.__nodesDict[name])
            self.__nodesDict[name] = self.__nodesList[idx] = value
        else:
            self.__dict__[name] = value


#######
# Note: Container and Repeater objects are instantiated via the makeNode()
# constructor function. This returns the appropriate class for the content 
# supplied ('abstract factory').
# (The documentation glosses over these differences for simplicity.)

class EmptyContainer(NullContent, Container):
    def __init__(self, nodeName, tagName, atts, content, encoder, decoder):
        Container.__init__(self, nodeName, tagName, atts)


class PlainContainer(PlainContent, Container):
    def __init__(self, nodeName, tagName, atts, content, encoder, decoder):
        PlainContent.__init__(self, content[0], encoder, decoder)
        Container.__init__(self, nodeName, tagName, atts)


class RichContainer(RichContent, Container):
    def __init__(self, nodeName, tagName, atts, content, encoder, decoder):
        RichContent.__init__(self, content)
        Container.__init__(self, nodeName, tagName, atts)
        
    def _clone(self):
        return self._initRichClone(Container._clone(self))

##

class EmptyRepeater(NullContent, Repeater):
    def __init__(self, nodeName, tagName, atts, content, encoder, decoder):
        Repeater.__init__(self, nodeName, tagName, atts)


class PlainRepeater(PlainContent, Repeater):
    def __init__(self, nodeName, tagName, atts, content, encoder, decoder):
        PlainContent.__init__(self, content[0], encoder, decoder)
        Repeater.__init__(self, nodeName, tagName, atts)


class RichRepeater(RichContent, Repeater):
    def __init__(self, nodeName, tagName, atts, content, encoder, decoder):
        RichContent.__init__(self, content)
        Repeater.__init__(self, nodeName, tagName, atts)
        
    def _clone(self):
        return self._initRichClone(Repeater._clone(self))
        
    def _fastClone(self):
        return self._initRichClone(Repeater._fastClone(self))

##

__nodeClasses = {
        'con': {'empty': EmptyContainer, 
                'plain': PlainContainer, 
                'rich': RichContainer},
        'rep': {'empty': EmptyRepeater, 
                'plain': PlainRepeater, 
                'rich': RichRepeater}}

def makeNode(nodeType, nodeName, tagName, atts, content, encoder, decoder):
    return __nodeClasses[nodeType][{0: 'empty', 1: 'plain'}.get(len(content), 
            'rich')](nodeName, tagName, atts, content, encoder, decoder)


#################################################
# MAIN
#################################################

class Template(RichContent):
    """An HTML template object model."""
    
    _nodeType = 'tem'
    _nodeName = ''
    
    def __init__(self, callback, html, attribute='node', 
            codecs=(defaultEncoder, defaultDecoder)):
        """
            callback : function -- the function that controls how this
                    template is rendered
            html : string or unicode -- the template HTML
            [attribute : string or unicode] -- name of the tag attribute used
                    to hold compiler directives
            [codecs : tuple] -- a tuple containing two functions used by the 
                    content property to encode/decode HTML entities
        """
        self.__callback = callback
        parser = Parser(attribute, codecs[0], codecs[1])
        parser.feed(html)
        parser.close()
        RichContent.__init__(self, parser.result())
    
    def render(self, *args):
        """Render this template; *args will be passed directly to the template.
        """
        clone = self._initRichClone(CloneNode(self))
        self.__callback(clone, *args)
        collector = []
        clone._renderContent(collector)
        try: # quick-n-dirty error reporting; not a real substitute for type-
            # checking for bad value assignments at point of origin, but cheap
            return ''.join(collector)
        except TypeError:
            raise TypeError, ("Can't render template: some node's content was "
                    "set to a non-text value.")

    def structure(self):
        """Print the object model's structure for diagnostic use."""
        print '-' * 80
        self._printStructure('')
        print '-' * 80


# Author: Eric Kow
# License: BSD3

"""
The Glozz_ file format in `educe.annotation` form

You're likely most interested in
`slurp_corpus` and `read_annotation_file`

There is a parallel tree of Glozz annotation objects
that are based on the stock objects in
`educe.annotation` but with glozz-specific metadata,
and a to_xml() function

.. _Glozz: http://www.glozz.org/
"""

import xml.etree.ElementTree as ET
import sys

from educe.annotation import *

class GlozzDocument(Document):
    def __init__(self, hashcode, unit, rels, text, schemas):
        Document.__init__(self, unit, rels, text)
        self.hashcode = hashcode
        self.schemas  = schemas # Element

    def to_xml(self):
        elm = ET.Element('annotations')
        if self.hashcode is not None:
            elm.append(ET.Element('metadata', corpusHashcode=self.hashcode))
        elm.extend([x.to_xml() for x in self.units])
        elm.extend([x.to_xml() for x in self.relations])
        elm.extend(self.schemas)
        return elm

    def set_origin(self, origin):
        Document.set_origin(self, origin)
        for x in self.schemas:
            x.origin = origin

def ordered_keys(preferred, d):
    """
    Keys from a dictionary starting with 'preferred' ones
    in the order of preference
    """
    return [ k for k in preferred if k in d ] +\
           [ k for k in d if k not in preferred ]

def glozz_annotation_to_xml(self, tag='annotation'):
    meta_elm = ET.Element('metadata')

    # FIXME: while these preferences are harmless
    # (the elements listed here are completely optional and
    # we except the document to mean the same regardless of
    # the order of these elements), they're a bit silly!
    #
    # We have them here to help
    # debugging (via visual diff), but we should either remove
    # them later or think of a way to model task-specific
    # things (here, STAC)
    #
    # Right now, there's not a very clear distinction between
    # STAC specific stuff and glozz generalities
    preferred_md_order = [ 'author'
                         , 'creation-date'
                         , 'lastModifier'
                         , 'lastModificationDate'
                         ]
    preferred_fs_order = [ 'Status'
                         , 'Quantity'
                         , 'Correctness'
                         , 'Kind'
                         , 'Comments'
                         , 'Developments'
                         , 'Emitter'
                         , 'Identifier'
                         , 'Timestamp'
                         , 'Resources'
                         , 'Trades'
                         , 'Dice_rolling'
                         , 'Gets'
                         , 'Has_resources'
                         , 'Amount_of_resources'
                         , 'Addressee'
                         , 'Surface_act'
                         ]
    for k in ordered_keys(preferred_md_order, self.metadata):
        e = ET.Element(k)
        e.text = self.metadata[k]
        meta_elm.append(e)

    char_elm = ET.Element('characterisation')
    char_tag_elm = ET.Element('type')
    char_tag_elm.text = self.type
    char_tag_fs  = ET.Element('featureSet')
    for k in ordered_keys(preferred_fs_order, self.features):
        e = ET.Element('feature',name=k)
        e.text = self.features[k]
        char_tag_fs.append(e)
    char_elm.extend([char_tag_elm, char_tag_fs])

    elm = ET.Element(tag, id=self.local_id())
    elm.extend([meta_elm, char_elm, self.span.to_xml()])
    return elm

class GlozzUnit(Unit):
    def __init__(self, *args, **kwargs):
        Unit.__init__(self, *args, **kwargs)

    def to_xml(self):
        elm = glozz_annotation_to_xml(self, 'unit')
        return elm

class GlozzRelation(Relation):
    def __init__(self, *args, **kwargs):
        Relation.__init__(self, *args, **kwargs)

    def to_xml(self):
        elm = glozz_annotation_to_xml(self, 'relation')
        return elm

class GlozzSpan(Span):
    def __init__(*args, **kwargs):
        Span.__init__(*args, **kwargs)

    def to_xml(self):
        def set_pos(elm,x):
            elm.append(ET.Element('singlePosition', index=str(x)))
        elm = ET.Element('positioning')
        start_elm = ET.Element('start')
        end_elm   = ET.Element('end')
        set_pos(start_elm, self.char_start)
        set_pos(end_elm,   self.char_end)
        elm.extend([start_elm, end_elm])
        return elm

class GlozzRelSpan(RelSpan):
    def __init__(*args, **kwargs):
        RelSpan.__init__(*args, **kwargs)

    def to_xml(self):
        def set_pos(elm,x):
            elm.append(ET.Element('term', id=str(x)))
        elm = ET.Element('positioning')
        set_pos(elm,self.t1)
        set_pos(elm,self.t2)
        return elm

class GlozzSchema(Annotation):
    """
    A set of annotations

    Parameters:

        * members: the of annotations contained in this schema
    """
    def __init__(self, rel_id, members, type, features, metadata=None):
        Annotation.__init__(self, rel_id, members, type, features, metadata)


# ---------------------------------------------------------------------
# xml processing
# -----------------------------------------------------------

# TODO: learn how exceptions work in Python; can I embed
# arbitrary strings in them?
#
# TODO: probably replace starting/ending integers with
# exception of some sort
class GlozzException(Exception):
    def __init__(self, *args, **kw):
        Exception.__init__(self, *args, **kw)

def on_single_element(root, default, f, name):
    """Return
       * the default if no elements
       * f(the node) if one element
       * an exception if more than one
    """
    nodes=root.findall(name)
    if len(nodes) == 0:
        if default is None:
            raise GlozzException("Expected but did not find any nodes with name %s" % name)
        else:
            return default
    elif len(nodes) > 1:
        raise GlozzException("Found more than one node with name %s" % name)
    else:
        return f(nodes[0])

# ---------------------------------------------------------------------
# glozz files
# ---------------------------------------------------------------------

def read_node(node, context=None):
    def get_one(name, default, ctx=None):
        f = lambda n : read_node(n, ctx)
        return on_single_element(node, default, f, name)

    def get_all(name):
        return map(read_node, node.findall(name))

    if node.tag == 'annotations':
        hashcode = get_one('metadata', '', 'annotations')
        if hashcode is '':
            hashcode = None
        units    = get_all('unit')
        rels     = get_all('relation')
        schemas  = get_all('schema')
        return (hashcode, units, rels, schemas)

    elif node.tag == 'characterisation':
        fs        = get_one('featureSet', [])
        unit_type = get_one('type'      , None)
        return (unit_type, fs)

    elif node.tag == 'feature':
        attr=node.attrib['name']
        val =node.text
        return (attr, val)

    ## TODO throw exception if we see more than one instance of a key
    elif node.tag == 'featureSet':
        return dict(get_all('feature'))

    elif node.tag == 'metadata' and context == 'annotations':
        return node.attrib['corpusHashcode']

    elif node.tag == 'metadata':
        return dict([(t.tag,t.text) for t in node ])

    elif node.tag == 'positioning' and context == 'unit':
        start = get_one('start', -2)
        end   = get_one('end',   -2)
        return GlozzSpan(start,end)

    elif node.tag == 'positioning' and context == 'relation':
        terms = get_all('term')
        if len(terms) != 2:
            raise GlozzException("Was expecting exactly 2 terms, but got %d" % len(terms))
        else:
            return GlozzRelSpan(terms[0], terms[1])

    elif node.tag == 'positioning' and context == 'schema':
        return frozenset(get_all('embedded-unit'))

    elif node.tag == 'relation':
        rel_id          = node.attrib['id']
        (unit_type, fs) = get_one('characterisation', None)
        span            = get_one('positioning',      None, 'relation')
        metadata        = get_one('metadata',         {})
        return GlozzRelation(rel_id, span, unit_type, fs, metadata=metadata)

    if node.tag == 'schema':
        anno_id         = node.attrib['id']
        (anno_type, fs) = get_one('characterisation', None)
        members         = get_one('positioning',      None, 'schema')
        metadata        = get_one('metadata',         {})
        return GlozzSchema(anno_id, members, anno_type, fs, metadata=metadata)

    elif node.tag == 'singlePosition':
        return int(node.attrib['index'])

    elif node.tag == 'start' or node.tag == 'end':
        return get_one('singlePosition', -3)

    elif node.tag in [ 'term', 'embedded-unit' ]:
        return node.attrib['id']

    elif node.tag == 'type':
        return node.text.strip()

    elif node.tag == 'unit':
        unit_id         = node.attrib['id']
        (unit_type, fs) = get_one('characterisation', None)
        span            = get_one('positioning',      None, 'unit')
        metadata        = get_one('metadata',         {})
        return GlozzUnit(unit_id, span, unit_type, fs, metadata=metadata)


def read_annotation_file(anno_filename, text_filename=None):
    """
    Read a single glozz annotation file and its corresponding text
    (if any).
    """
    tree = ET.parse(anno_filename)
    (hashcode, units, rels, schemas) = read_node(tree.getroot())
    text = None
    if text_filename is not None:
        with open(text_filename) as tf:
            text = tf.read()
    return GlozzDocument(hashcode, units, rels, text, schemas)


def write_annotation_file(anno_filename, doc):
    """
    Write a GlozzDocument to XML in the given path
    """

    # tweaked from the indent function in
    # http://effbot.org/zone/element-lib.htm
    def reformat(elem):
        """
        insert a break after each element tag
        """
        i = "\n"
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                reformat(elem)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if not elem.tail or not elem.tail.strip():
                elem.tail = i

    elem = doc.to_xml()
    reformat(elem) # ugh, imperative
    ET.ElementTree(elem).write(anno_filename, encoding='utf-8', xml_declaration=True)

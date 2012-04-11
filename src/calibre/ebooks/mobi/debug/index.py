#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2012, Kovid Goyal <kovid@kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

from collections import OrderedDict, namedtuple

from calibre.ebooks.mobi.reader.headers import NULL_INDEX
from calibre.ebooks.mobi.reader.index import (CNCX, parse_indx_header,
        parse_tagx_section, parse_index_record, INDEX_HEADER_FIELDS)

File = namedtuple('File',
    'file_number name divtbl_count start_position length')

Elem = namedtuple('Elem',
    'insert_pos toc_text file_number sequence_number start_pos '
    'length')

def read_index(sections, idx, codec):
    table, cncx = OrderedDict(), CNCX([], codec)

    data = sections[idx].raw

    indx_header = parse_indx_header(data)
    indx_count = indx_header['count']

    if indx_header['ncncx'] > 0:
        off = idx + indx_count + 1
        cncx_records = [x.raw for x in sections[off:off+indx_header['ncncx']]]
        cncx = CNCX(cncx_records, codec)

    tag_section_start = indx_header['tagx']
    control_byte_count, tags = parse_tagx_section(data[tag_section_start:])

    for i in xrange(idx + 1, idx + 1 + indx_count):
        # Index record
        data = sections[i].raw
        parse_index_record(table, data, control_byte_count, tags, codec,
                indx_header['ordt_map'], strict=True)
    return table, cncx, indx_header

class Index(object):

    def __init__(self, idx, records, codec):
        self.table = self.cncx = self.header = self.records = None
        if idx != NULL_INDEX:
            self.table, self.cncx, self.header = read_index(records, idx, codec)

    def render(self):
        ans = ['*'*10 + ' Index Header ' + '*'*10]
        a = ans.append
        if self.header is not None:
            for field in INDEX_HEADER_FIELDS:
                a('%-12s: %r'%(field, self.header[field]))
        ans.extend(['', ''])

        if self.cncx:
            a('*'*10 + ' CNCX ' + '*'*10)
            for offset, val in self.cncx.iteritems():
                a('%10s: %s'%(offset, val))
            ans.extend(['', ''])

        if self.table is not None:
            a('*'*10 + ' %d Index Entries '%len(self.table) + '*'*10)
            for k, v in self.table.iteritems():
                a('%s: %r'%(k, v))

        if self.records:
            ans.extend(['', '', '*'*10 + ' Parsed Entries ' + '*'*10])
            for f in self.records:
                a(repr(f))

        return ans + ['']

    def __str__(self):
        return '\n'.join(self.render())

class SKELIndex(Index):

    def __init__(self, skelidx, records, codec):
        super(SKELIndex, self).__init__(skelidx, records, codec)
        self.records = []

        if self.table is not None:
            for i, text in enumerate(self.table.iterkeys()):
                tag_map = self.table[text]
                if set(tag_map.iterkeys()) != {1, 6}:
                    raise ValueError('SKEL Index has unknown tags: %s'%
                            (set(tag_map.iterkeys())-{1,6}))
                self.records.append(File(
                    i, # file_number
                    text, # name
                    tag_map[1][0], # divtbl_count
                    tag_map[6][0], # start_pos
                    tag_map[6][1]) # length
                )

class SECTIndex(Index):

    def __init__(self, sectidx, records, codec):
        super(SECTIndex, self).__init__(sectidx, records, codec)
        self.records = []

        if self.table is not None:
             for i, text in enumerate(self.table.iterkeys()):
                tag_map = self.table[text]
                if set(tag_map.iterkeys()) != {2, 3, 4, 6}:
                    raise ValueError('SECT Index has unknown tags: %s'%
                            (set(tag_map.iterkeys())-{2, 3, 4, 6}))

                toc_text = self.cncx[tag_map[2][0]]
                self.records.append(Elem(
                    int(text), # insert_pos
                    toc_text, # toc_text
                    tag_map[3][0], # file_number
                    tag_map[4][0], # sequence_number
                    tag_map[6][0], # start_pos
                    tag_map[6][1]  # length
                    )
                )


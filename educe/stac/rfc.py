'''
Right frontier constraint and its variants
'''

import collections
import itertools as itr

from .annotation import (is_subordinating)


# pylint: disable=too-few-public-methods, no-self-use

class BasicRfc(object):
    '''
    The vanilla right frontier constraint ::

        1. X is textually last among its siblings => RF(X)

        2. Y
           | (sub)
           v
           X

           RF(Y) => RF(X)

        3. X: +----+
              | Y  |
              +----+

           RF(Y) => RF(X)
    '''
    def __init__(self, graph):
        self._graph = graph

    def _build_right_frontier(self, points, last):
        """
        Given a dictionary mapping each node to its closest
        right frontier node, generate a path up that frontier.
        """
        current = last
        while current in points:
            next_point = points[current]
            yield current
            current = next_point

    def _is_on_right_frontier(self, points, last, node):
        """
        Return True if node is on the right frontier as
        represented by the pair points/last.

        This uses `build_frontier`
        """
        return any(fnode == node for fnode in
                   self._build_right_frontier(points, last))

    def _is_incoming_to(self, node, lnk):
        'true if a given link has the given node as target'
        graph = self._graph
        nodes = graph.links(lnk)
        return (graph.is_relation(lnk) and
                len(nodes) == 2 and nodes[1] == node)

    def frontier(self):
        """
        Return nodes on the right frontier, a dictionary
        mapping each node to the nearest node (in the sequence)
        that either

        * points to it with a subordinating relation
        * includes it as a CDU member
        """
        graph = self._graph
        nodes = graph.first_widest_dus()

        def position(name):
            'return a relative position for a node'
            if name in nodes:
                return nodes.index(name)
            else:
                return -1

        points = {}
        for node1 in nodes:
            candidates = []
            for lnk in graph.links(node1):
                if (self._is_incoming_to(node1, lnk) and
                        is_subordinating(graph.annotation(lnk))):
                    node2 = graph.links(lnk)[0]
                    candidates.append((node2, position(node2)))
                elif graph.is_cdu(lnk):
                    node2 = graph.mirror(lnk)
                    candidates.append((node2, position(node2)))

            if candidates:
                best = max(candidates, key=lambda x: x[1])
                points[node1] = best[0]
            else:
                points[node1] = None

        return points

    def violations(self):
        '''
        Return a dictionary of node names which are the targets of right
        frontier violation, along with the offending relation instance edge
        names.

        You'll need a stac graph object to interpret these names with.

        :rtype: dict(string, [string])
        '''
        graph = self._graph
        nodes = graph.first_widest_dus()
        res = collections.defaultdict(list)
        if len(nodes) < 2:
            return res

        points = self.frontier()
        nexts = itr.islice(nodes, 1, None)
        for last, node1 in itr.izip(nodes, nexts):
            for lnk in graph.links(node1):
                if not self._is_incoming_to(node1, lnk):
                    continue
                node2 = graph.links(lnk)[0]
                if not self._is_on_right_frontier(points, last, node2):
                    res[node2].append(lnk)
        return res

# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from collections import deque
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import networkx as nx

from .builder import BranchInfo, SymbolTable


def isolate_incoming_edge(edge: Tuple[str, str], symbols: SymbolTable):
    "Copy block B to isolate the incoming edge A->B for block B"
    blockA, blockB = edge
    blockB_copy = symbols.new_tmp_block_name()

    # 1) Redirect A's branch target from B -> B_copy
    br_info_A = symbols.block_branchs[blockA]
    br_tgts_A_new = [blockB_copy if block == blockB else block for block in br_info_A.branch_targets]
    symbols.block_branchs[blockA] = BranchInfo(br_info_A.branch_condition, br_tgts_A_new)

    # 2) Duplicate B's statements and branch info to B_copy
    symbols.block_statements[blockB_copy] = symbols.block_statements[blockB].copy()
    br_info_B = symbols.block_branchs[blockB]
    symbols.block_branchs[blockB_copy] = BranchInfo(br_info_B.branch_condition, br_info_B.branch_targets)

    # 3) Rewire CFG: remove A->B, add A->B_copy, and B_copy -> successors(B)
    symbols.cfg.remove_edge(blockA, blockB)
    symbols.cfg.add_edge(blockA, blockB_copy)
    for u in symbols.cfg.successors(blockB):
        symbols.cfg.add_edge(blockB_copy, u)


def find_if_pattern(G: nx.DiGraph) -> Optional[Tuple[str, List[List[str]]]]:
    """Find an 'if' statement candidate."""
    edges_deg1 = [(u, v) for u, v in G.edges if G.out_degree(u) == 1]

    H = nx.DiGraph()
    H.add_nodes_from(G.nodes)
    H.add_edges_from(edges_deg1)

    # Partition nodes by out-degree
    deg0_H: set = {u for u in H.nodes if H.out_degree(u) == 0}
    deg1_H: set = {u for u in H.nodes if H.out_degree(u) == 1}

    # chains[u] = path from block u to out-degree-0 block, using only out-degree-1 nodes
    chains: Dict[str, List[str]] = {u: None for u in G.nodes}

    # BFS on the reverse graph, restricted to predecessors with out-degree == 1.
    q: deque[Tuple[str, List[str]]] = deque([(u, [u]) for u in deg0_H])

    while q:
        block, path = q.popleft()
        chains[block] = path
        for pred_block in G.predecessors(block):
            if pred_block in deg1_H:
               assert chains[pred_block] is None
               q.append((pred_block, [pred_block] + path))

    # Scan out-degree-2 nodes for an 'if' statement candidate
    deg2_G: set = {u for u in G.nodes if G.out_degree(u) == 2}
    for block in deg2_G:
        u, v = list(G.successors(block))
        path_u = chains[u]
        path_v = chains[v]
        if path_u[-1] == path_v[-1]:
            while path_u and path_v and path_u[-1] == path_v[-1]:
                path_u.pop(-1)
                path_v.pop(-1)
            return block, [path_u, path_v]

    return None


def isolate_if_pattern(symbols: SymbolTable) -> bool:
    is_updated = False
    result = find_if_pattern(symbols.cfg)
    if result is None:
        return is_updated
    
    # For each path, walk edges and split any node that has in-degree > 1.
    if_block, paths = result
    for path in paths:
        for edge in zip([if_block]+path[:-1], path):
            if symbols.cfg.in_degree(edge[1]) > 1:
                is_updated = True
                isolate_incoming_edge(edge, symbols)
                
    return is_updated
    

def find_while_pattern(G: nx.DiGraph) -> Optional[Tuple[str, List[List[str]]]]:
    """Find an 'while' statement candidate."""
    edges_deg1 = [(u, v) for u, v in G.edges if G.out_degree(u) == 1]

    H = nx.DiGraph()
    H.add_nodes_from(G.nodes)
    H.add_edges_from(edges_deg1)

    # Partition nodes by out-degree
    deg0_H: set = {u for u in H.nodes if H.out_degree(u) == 0}
    deg1_H: set = {u for u in H.nodes if H.out_degree(u) == 1}

    # chains[u] = path from block u to out-degree-0 block, using only out-degree-1 nodes
    chains: Dict[str, List[str]] = {u: None for u in G.nodes}

    # BFS on the reverse graph, restricted to predecessors with out-degree == 1.
    q: deque[Tuple[str, List[str]]] = deque([(u, [u]) for u in deg0_H])

    while q:
        block, path = q.popleft()
        chains[block] = path
        for pred_block in G.predecessors(block):
            if pred_block in deg1_H:
               assert chains[pred_block] is None
               q.append((pred_block, [pred_block] + path))

    # Scan out-degree-2 nodes for an 'while' statement candidate
    deg2_G: set = {u for u in G.nodes if G.out_degree(u) == 2}
    for block in deg2_G:
        for succ in G.successors(block):
            path = chains[succ]
            if block in path:
                return block, path[:path.index(block)]
    
    return None
        

def isolate_while_pattern(symbols: SymbolTable) -> bool:
    is_updated = False
    result = find_while_pattern(symbols.cfg)
    if result is None:
        return is_updated
    
    # For each path, walk edges and split any node that has in-degree > 1.
    while_block, path = result
    for edge in zip([while_block]+path[:-1], path):
        if symbols.cfg.in_degree(edge[1]) > 1:
            is_updated = True
            isolate_incoming_edge(edge, symbols)
                
    return is_updated
    
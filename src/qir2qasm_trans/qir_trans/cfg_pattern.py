from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

import networkx as nx
from networkx.algorithms import isomorphism

from .builder import SymbolTable


class CFGPattern:
    def __init__(self):
        self.patterns: List[nx.DiGraph] = []
        self.degrees: List[OrderedDict[str, Tuple[Optional[int], Optional[int]]]] = []

    def matching(self, cfg: nx.DiGraph) -> Tuple[Optional[int], Optional[Dict[str, str]]]:
        for idx, pattern, degree in enumerate(zip(self.patterns, self.degrees)):
            for match in isomorphism.DiGraphMatcher(cfg, pattern).subgraph_isomorphisms_iter():
                for g_node, p_node in match.items():
                    in_degree, out_degree = degree[p_node]
                    if (in_degree is not None) and (in_degree != cfg.in_degree(g_node)):
                        break
                    if (out_degree is not None) and (out_degree != cfg.out_degree(g_node)):
                        break
                else:
                    return idx, {p_node: g_node for g_node, p_node in match.items()}
        return None, None

    def building(self, symbols: SymbolTable, idx: int, mapping: Dict[str, str]):
        pass


class SeqPattern(CFGPattern):
    def __init__(self):
        super().__init__()
        pattern = nx.DiGraph()
        pattern.add_edges_from([("A", "B")])
        self.patterns.append(pattern)
        degree = {"A": (None, 1), "B": (1, None)}
        self.degrees.append(degree)

    def building(self, symbols: SymbolTable, idx: int, mapping: Dict[str, str]):
        symbols.block_branchs[mapping["A"]] = symbols.block_branchs.pop([mapping["B"]])
        symbols.block_statements[mapping["A"]].extend(symbols.block_statements.pop([mapping["B"]]))


class CopyPattern(CFGPattern):
    def __init__(self):
        super().__init__()
        pattern = nx.DiGraph()
        pattern.add_edges_from([("A", "B")])
        self.patterns.append(pattern)
        degree = {"A": (None, 1), "B": (None, None)}
        self.degrees.append(degree)

    def building(self, symbols: SymbolTable, idx: int, mapping: Dict[str, str]):
        symbols.block_branchs[mapping["A"]] = symbols.block_branchs[mapping["B"]]
        symbols.block_statements[mapping["A"]].extend(symbols.block_statements[mapping["B"]])


class IfPattern(CFGPattern):
    def __init__(self):
        super().__init__()
        pattern1 = nx.DiGraph()
        pattern1.add_edges_from([("A", "B"), ("A", "C"), ("C", "D"), ("D", "")])

        self.pattern.add_edges_from([("A", "B")])
        self.degrees["A"] = (None, 1)
        self.degrees["B"] = (None, None)

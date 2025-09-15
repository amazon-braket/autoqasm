from typing import Dict, Optional, Tuple

import networkx as nx
from networkx.algorithms import isomorphism
from openqasm3 import ast

from .builder import BranchInfo, SymbolTable


class CFGPattern:
    def __init__(self):
        self.pattern: nx.DiGraph = nx.DiGraph()
        self.degrees: Dict[str, Tuple[Optional[int], Optional[int]]] = {}

    def matching(self, cfg: nx.DiGraph) -> Optional[Dict[str, str]]:
        for match in isomorphism.DiGraphMatcher(cfg, self.pattern).subgraph_isomorphisms_iter():
            for g_node, p_node in match.items():
                in_degree, out_degree = self.degrees[p_node]
                if (in_degree is not None) and (in_degree != cfg.in_degree(g_node)):
                    break
                if (out_degree is not None) and (out_degree != cfg.out_degree(g_node)):
                    break
            else:
                return {p_node: g_node for g_node, p_node in match.items()}
        return None

    def building(self, symbols: SymbolTable) -> bool:
        return False


class SeqPattern(CFGPattern):
    def __init__(self):
        super().__init__()
        self.pattern.add_edges_from([("A", "B")])
        self.degrees["A"] = (None, 1)
        self.degrees["B"] = (1, None)

    def building(self, symbols: SymbolTable):
        is_updated = False
        blocks = self.matching(symbols.cfg)

        while blocks:
            is_updated = True
            symbols.block_statements[blocks["A"]].extend(symbols.block_statements.pop(blocks["B"]))
            symbols.block_branchs[blocks["A"]] = symbols.block_branchs.pop(blocks["B"])
            symbols.cfg = nx.contracted_nodes(symbols.cfg, blocks["A"], blocks["B"], self_loops=False)

            blocks = self.matching(symbols.cfg)
        
        return is_updated


class IfPattern1(CFGPattern):
    def __init__(self):
        super().__init__()
        self.pattern.add_edges_from([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])
        self.degrees["A"] = (None, 2)
        self.degrees["B"] = (1, 1)
        self.degrees["C"] = (1, 1)
        self.degrees["D"] = (None, None)

    def building(self, symbols: SymbolTable):
        is_updated = False
        blocks = self.matching(symbols.cfg)
        while blocks:
            is_updated = True
            br_info_A = symbols.block_branchs[blocks["A"]]
            br_cond_A = br_info_A.branch_condition
            br_tgts_A = br_info_A.branch_targets

            if br_tgts_A[0] == blocks["B"]:
                # A -> B is the branch of True 
                if_block = symbols.block_statements[blocks["B"]]
                else_block = symbols.block_statements[blocks["C"]]
            else:
                # A -> B is the branch of False
                if_block = symbols.block_statements[blocks["C"]]
                else_block = symbols.block_statements[blocks["B"]]
            
            if_statement = ast.BranchingStatement(condition=br_cond_A, if_block=if_block, else_block=else_block)
            symbols.block_statements[blocks["A"]].append(if_statement)
            symbols.block_branchs[blocks["A"]] = BranchInfo(None, [blocks["D"]])
            symbols.cfg = nx.contracted_nodes(symbols.cfg, blocks["A"], blocks["B"], self_loops=False)
            symbols.cfg = nx.contracted_nodes(symbols.cfg, blocks["A"], blocks["C"], self_loops=False)

            blocks = self.matching(symbols.cfg)

        return is_updated


class IfPattern2(CFGPattern):
    def __init__(self):
        super().__init__()
        self.pattern.add_edges_from([("A", "B"), ("A", "D"), ("B", "D")])
        self.degrees["A"] = (None, 2)
        self.degrees["B"] = (1, 1)
        self.degrees["D"] = (None, None)

    def building(self, symbols: SymbolTable):
        is_updated = False
        blocks = self.matching(symbols.cfg)
        while blocks:
            is_updated = True
            br_info_A = symbols.block_branchs[blocks["A"]]
            br_cond_A = br_info_A.branch_condition
            br_tgts_A = br_info_A.branch_targets

            if br_tgts_A[0] == blocks["B"]:
                # A -> B is the branch of True 
                if_block = symbols.block_statements[blocks["B"]]
                else_block = []
            else:
                # A -> B is the branch of False
                if_block = []
                else_block = symbols.block_statements[blocks["B"]]
            
            if_statement = ast.BranchingStatement(condition=br_cond_A, if_block=if_block, else_block=else_block)
            symbols.block_statements[blocks["A"]].append(if_statement)
            symbols.block_branchs[blocks["A"]] = BranchInfo(None, [blocks["D"]])
            symbols.cfg = nx.contracted_nodes(symbols.cfg, blocks["A"], blocks["B"], self_loops=False)

            blocks = self.matching(symbols.cfg)

        return is_updated
    

class IfPattern(CFGPattern):
    def building(self, symbols: SymbolTable):
        is_updated = IfPattern1().building(symbols) or IfPattern2().building(symbols)
        while IfPattern1().building(symbols) or IfPattern2().building(symbols):
            pass
        return is_updated
    

class WhilePattern1(CFGPattern):
    def __init__(self):
        super().__init__()
        self.pattern.add_edges_from([("A", "B"), ("B", "A")])
        self.degrees["A"] = (None, 2)    # A is the exit block of the while loop.
        self.degrees["B"] = (1, 1)

    def building(self, symbols: SymbolTable):
        is_updated = False
        blocks = self.matching(symbols.cfg)
        while blocks:
            is_updated = True
            br_info_A = symbols.block_branchs[blocks["A"]]
            br_cond_A = br_info_A.branch_condition
            br_tgts_A = br_info_A.branch_targets

            assert br_cond_A is not None
            if br_tgts_A[0] == blocks["B"]:
                # A -> B is the branch of True 
                while_condition = br_cond_A
                out_bt_tgt = br_tgts_A[1]
            else:
                # A -> B is the branch of False
                while_condition = ast.UnaryExpression(op=ast.UnaryOperator['!'], expression=br_cond_A)
                out_bt_tgt = br_tgts_A[0]
                
            while_body = symbols.block_statements[blocks["B"]] + symbols.block_statements[blocks["A"]]
            while_statement = ast.WhileLoop(while_condition=while_condition, block=while_body)
            symbols.block_statements[blocks["A"]].append(while_statement)
            symbols.block_branchs[blocks["A"]] = BranchInfo(None, [out_bt_tgt])

            symbols.block_statements.pop(blocks["B"])
            symbols.block_branchs.pop(blocks["B"])

            symbols.cfg.remove_edge(blocks["A"], blocks["B"])
            symbols.cfg.remove_node(blocks["B"])
            
            blocks = self.matching(symbols.cfg)

        return is_updated
    

class WhilePattern2(CFGPattern):
    def __init__(self):
        super().__init__()
        self.pattern.add_edges_from([("A", "A")])
        self.degrees["A"] = (None, 2)   

    def building(self, symbols: SymbolTable):
        is_updated = False
        blocks = self.matching(symbols.cfg)
        while blocks:
            is_updated = True
            br_info_A = symbols.block_branchs[blocks["A"]]
            br_cond_A = br_info_A.branch_condition
            br_tgts_A = br_info_A.branch_targets

            assert br_cond_A is not None
            if br_tgts_A[0] == blocks["A"]:
                # A -> A is the branch of True 
                while_condition = br_cond_A
                out_bt_tgt = br_tgts_A[1]
            else:
                # A -> A is the branch of False
                while_condition = ast.UnaryExpression(op=ast.UnaryOperator['!'], expression=br_cond_A)
                out_bt_tgt = br_tgts_A[0]
                
            while_body = symbols.block_statements[blocks["A"]].copy()
            while_statement = ast.WhileLoop(while_condition=while_condition, block=while_body)
            symbols.block_statements[blocks["A"]].append(while_statement)
            symbols.block_branchs[blocks["A"]] = BranchInfo(None, [out_bt_tgt])

            symbols.cfg.remove_edge(blocks["A"], blocks["A"])

            blocks = self.matching(symbols.cfg)

        return is_updated
    

class WhilePattern(CFGPattern):
    def building(self, symbols: SymbolTable):
        is_updated = WhilePattern1().building(symbols) or WhilePattern2().building(symbols)
        while WhilePattern1().building(symbols) or WhilePattern2().building(symbols):
            pass
        return is_updated
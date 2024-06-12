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

"""Converters for aritmetic operator nodes"""

import ast

import gast
from malt.core import ag_ctx, converter
from malt.pyct import templates

ARITHMETIC_OPERATORS = {
    gast.FloorDiv: "ag__.floor_div",
}


class ArithmeticTransformer(converter.Base):
    """Transformer for arithmetic nodes."""

    def visit_BinOp(self, node: ast.stmt) -> ast.stmt:
        """Transforms a BinOp node.
        Args :
            node(ast.stmt) : AST node to transform
        Returns :
            ast.stmt : Transformed node
        """
        node = self.generic_visit(node)
        op_type = type(node.op)
        if op_type not in ARITHMETIC_OPERATORS:
            return node

        template = f"{ARITHMETIC_OPERATORS[op_type]}(lhs_,rhs_)"

        new_node = templates.replace(
            template,
            lhs_=node.left,
            rhs_=node.right,
            original=node,
        )[0].value

        return new_node


def transform(node: ast.stmt, ctx: ag_ctx.ControlStatusCtx) -> ast.stmt:
    """Transform arithmetic nodes.
    Args:
        node(ast.stmt) : AST node to transform
        ctx (ag_ctx.ControlStatusCtx) : Transformer context.
    Returns :
        ast.stmt : Transformed node.
    """

    return ArithmeticTransformer(ctx).visit(node)

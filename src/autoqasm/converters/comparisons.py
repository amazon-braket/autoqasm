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

"""Converters for comparison nodes."""

import ast

from malt.core import ag_ctx, converter
from malt.pyct import templates

COMPARISON_OPERATORS = {
    ast.Lt: "ag__.lt_",
    ast.LtE: "ag__.lteq_",
    ast.Gt: "ag__.gt_",
    ast.GtE: "ag__.gteq_",
}


class ComparisonTransformer(converter.Base):
    """Transformer for comparison nodes."""

    def visit_Compare(self, node: ast.stmt) -> ast.stmt:
        """Transforms a comparison node.

        Args:
            node (ast.stmt): AST node to transform.

        Returns:
            ast.stmt: Transformed node.
        """
        node = self.generic_visit(node)

        if any(type(op) not in COMPARISON_OPERATORS for op in node.ops):
            return node

        operands = [node.left, *node.comparators]
        result = None
        for op, lhs, rhs in zip(node.ops, operands, operands[1:]):
            template = f"{COMPARISON_OPERATORS[type(op)]}(lhs_, rhs_)"
            pair_expr = templates.replace(template, lhs_=lhs, rhs_=rhs, original=node)[0].value
            if result is None:
                result = pair_expr
            else:
                result = templates.replace(
                    "ag__.and_(lambda: lhs_, lambda: rhs_)",
                    lhs_=result,
                    rhs_=pair_expr,
                    original=node,
                )[0].value

        return result


def transform(node: ast.stmt, ctx: ag_ctx.ControlStatusCtx) -> ast.stmt:
    """Transform comparison nodes.

    Args:
        node (ast.stmt): AST node to transform.
        ctx (ag_ctx.ControlStatusCtx): Transformer context.

    Returns:
        ast.stmt: Transformed node.
    """

    return ComparisonTransformer(ctx).visit(node)

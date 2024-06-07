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


"""Converters for integer casting nodes."""

import ast

import gast
from malt.core import ag_ctx, converter
from malt.pyct import templates


class TypecastTransformer(converter.Base):
    def visit_Call(self, node: ast.stmt) -> ast.stmt:
        """Converts type casting operations to their AutoQASM counterpart.

        Args:
            node (ast.stmt): AST node to transform.

        Returns:
            ast.stmt: Transformed node.
        """
        typecasts_supported = ["int", "float"]

        template = """
                ag__.typecast(type_, argument_)
                """
        node = self.generic_visit(node)
        if (
            len(node.args) > 1
            and hasattr(node.args[1], "func")
            and hasattr(node.args[1].func, "id")
            and node.args[1].func.id in typecasts_supported
        ):
            new_node = templates.replace(
                template,
                type_=node.args[1].func.id,
                argument_=node.args[1].args,
                original=node,
            )
            new_node = new_node[0].value
        else:
            new_node = node
        return new_node


def transform(node: ast.stmt, ctx: ag_ctx.ControlStatusCtx) -> ast.stmt:
    """Transform int cast nodes.

    Args:
        node (ast.stmt): AST node to transform.
        ctx (ag_ctx.ControlStatusCtx): Transformer context.

    Returns:
        ast.stmt: Transformed node.
    """

    return TypecastTransformer(ctx).visit(node)

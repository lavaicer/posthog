from typing import Literal, cast, Optional

from posthog.hogql import ast
from posthog.hogql.context import HogQLContext
from posthog.hogql.database.database import create_hogql_database
from posthog.hogql.errors import HogQLException, NotImplementedException, SyntaxException
from posthog.hogql.parser import parse_expr
from posthog.hogql.printer import prepare_ast_for_printing, print_prepared_ast


# This is called only from "non-hogql-based" insights to translate HogQL expressions into ClickHouse SQL
# All the constant string values will be collected into context.values
def translate_hogql(
    query: str,
    context: HogQLContext,
    dialect: Literal["hogql", "clickhouse"] = "clickhouse",
    events_table_alias: Optional[str] = None,
) -> str:
    """Translate a HogQL expression into a Clickhouse expression. Raises if any placeholders found."""
    if query == "":
        raise HogQLException("Empty query")

    try:
        # Create a fake query that selects from "events" to have fields to select from.
        if context.database is None:
            if context.team_id is None:
                raise ValueError("Cannot translate HogQL for a filter with no team specified")
            context.database = create_hogql_database(context.team_id)
        node = parse_expr(query, no_placeholders=True)
        select_query = ast.SelectQuery(select=[node], select_from=ast.JoinExpr(table=ast.Field(chain=["events"])))
        if events_table_alias is not None:
            # mypy thinks select_query could be None here, but it can't
            select_query.select_from.alias = events_table_alias  # type: ignore
        prepared_select_query: ast.SelectQuery = cast(
            ast.SelectQuery,
            prepare_ast_for_printing(select_query, context=context, dialect=dialect, stack=[select_query]),
        )
        return print_prepared_ast(
            prepared_select_query.select[0], context=context, dialect=dialect, stack=[prepared_select_query]
        )
    except (NotImplementedException, SyntaxException):
        raise

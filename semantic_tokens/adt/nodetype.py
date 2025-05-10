from enum import IntEnum


class NodeType(IntEnum):
    LOCAL_VARIABLE_DECLARATION = 1
    METHOD_DECLARATION = 2
    IF_CONDITION = 3
    ELSE_BODY = 4
    ASSERT_CONDITION = 5
    ASSERT_BODY = 6
    SWITCH_CONDITION = 7
    SWITCH_BODY = 8
    CASE_LABEL = 9
    CASE_BODY = 10
    WHILE_CONDITION = 11
    WHILE_BODY = 12
    DO_BODY = 13
    DO_CONDITION = 14
    FOR_CONDITION = 15
    FOR_BODY = 16
    RETURN = 17
    THROW = 18
    SYNCHRONIZED_CONDITION = 19
    SYNCHRONIZED_BODY = 20
    TRY_BODY = 21
    CATCH_BODY = 22
    FINALLY_BODY = 23
    EXPRESSION_ASSIGN = 24
    EXPRESSION_TERNARY = 25
    EXPRESSION_BINARY = 26
    EXPRESSION_LAMBDA = 27
    INVOCATION_METHOD = 28  # Ordinary method call
    INVOCATION_CONSTRUCTOR = 29  # Constructor call
    CREATOR_CLASS = 30  # Class construct
    CREATOR_ARRAY = 31  # Array construction
    LOOP_BODY = 32
    LOOP_CONDITION = 33
    ARRAY_SELECTOR = 34  # Get values from array
    EXPRESSION_BINARY_LOGIC = 35  # Logical and relational expressions: such as >, <, ==, !=
    EXPRESSION_BINARY_OPERATION = 36  # Arithmetic, shift, and bit logic expressions: such as *, /, >>, &
    EXPRESSION_BINARY_CONDITION = 37  # Status expression: such as &&, ||
    NODE_TYPE_END = 38

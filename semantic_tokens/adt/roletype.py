from enum import IntEnum


class RoleType(IntEnum):
    BASIC_TYPE = 1
    REFERENCE_TYPE = 2
    VARIABLE = 3
    FIELD = 4
    METHOD = 5
    QUALIFIER = 6
    EXPRESSION_RELATION = 7
    ROLE_TYPE_END = 8

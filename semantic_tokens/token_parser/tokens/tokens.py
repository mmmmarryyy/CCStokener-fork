from semantic_tokens.adt.roletype import RoleType
from semantic_tokens.token_parser.tokens.token import Token
from semantic_tokens.token_parser.utils import init_n_gram


class Variable(Token):
    def __init__(self, v_type, name, n_gram=None, window_size=0):
        super().__init__(name, RoleType.VARIABLE, n_gram)
        self.type = v_type
        self.related_variables = []

        if n_gram is None:
            n_gram = init_n_gram()
        self.n_gram = n_gram

        self.window_index = 0
        self.window_size = window_size
        self.related_variables_window = [[] for i in range(0, window_size)]

    def add_related_variable(self, related_variable):
        self.related_variables_window[self.window_index] = related_variable
        self.window_index = (self.window_index + 1) % self.window_size

    def get_related_variables(self):
        related_variables = []
        for value in self.related_variables_window:
            related_variables.extend(value)
        return list(set(related_variables))


class Relation(Token):
    def __init__(self, name, n_gram=None):
        super().__init__(name, RoleType.EXPRESSION_RELATION, n_gram)


class FieldAccess(Token):
    def __init__(self, name):
        super().__init__(name, RoleType.FIELD, None)


class VariableType(Token):
    def __init__(self, name, role):
        super().__init__(name, role, None)


class Method(Token):
    def __init__(self, name, n_gram=None):
        super().__init__(name, RoleType.METHOD, n_gram)


class Qualifier(Token):
    def __init__(self, name):
        super().__init__(name, RoleType.QUALIFIER, None)


class Keyword(Token):
    def __init__(self, name):
        super().__init__(name, None, None)

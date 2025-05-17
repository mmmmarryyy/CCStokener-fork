from semantic_tokens.adt.roletype import RoleType
from semantic_tokens.token_parser.utils import init_n_gram


class Token(object):
    n_gram = None
    role: RoleType = None
    name = None
    count = 0

    def __init__(self, name, role, n_gram):
        self.n_gram = n_gram
        self.name = name
        self.role = role

    def update_path(self, n_gram):
        if self.n_gram is None:
            self.n_gram = init_n_gram()

        self.count += 1
        self.n_gram = self.n_gram + n_gram

    def set_path(self, n_gram):
        self.count += 1
        self.n_gram = n_gram

    def output(self):
        if self.n_gram is None:
            return []
        return self.n_gram.astype(int).tolist()

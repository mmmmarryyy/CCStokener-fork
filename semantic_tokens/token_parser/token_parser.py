from logger import log
from semantic_tokens.adt.nodetype import NodeType
from semantic_tokens.adt.roletype import RoleType
from semantic_tokens.javalang import tree
from semantic_tokens.token_parser.tokens.tokens import Variable, VariableType, Method, Keyword, Relation, FieldAccess
from semantic_tokens.token_parser.utils import (
    unpack_modifier,
    unpack_member,
    unpack_type,
    rearrange_path,
    transform_node,
    parse_inner_modifiers
)
from semantic_tokens.utils import merge_dictionaries, transform_to_array, parse_operation_node_type


class TokenParser(object):
    def __init__(self):
        self.clear()
        self.file_path = None
        self.output_file_path = None
        self.window_size = 3
        self.debug = 1
        self.method_depth = 0

    def clear(self):
        self.token_map = {}
        self.current_path = []

        self.global_variable_map = {}
        self.global_field_map = {}
        self.global_type_map = {}
        self.global_method_map = {}

        self.global_keyword_map = {}

        self.method_start = -1
        self.method_end = -1

        self.valid_token_number = 0
        self.total_token_number = 0

        self.union_variable_list = []
        self.union_method_list = []
        self.union_expression_relation_list = []

    def dump(self):
        if (self.method_end - self.method_start + 1) < 6:
            return ""

        dump_str = '<block filePath:{}, startline:{}, endline:{}, validTokenNum:{}, totalTokenNum: {}>\n' \
            .format(self.file_path, self.method_start, self.method_end, self.valid_token_number,
                    self.total_token_number)

        # 输出variable
        dump_str += '<variable>\n'
        for key, value in self.global_variable_map.items():
            dump_str += ('{},{}: {}\n'.format(key, value.count, value.output()))
        dump_str += '</variable>\n'

        dump_str += ('<field>\n')
        for key, value in self.global_field_map.items():
            # dump_str += ('{}: {}\n'.format(key, value.output()))
            dump_str += ('{},{}: {}\n'.format(key, value.count, value.output()))
        dump_str += ('</field>\n')

        dump_str += ('<method>\n')
        for key, value in self.global_method_map.items():
            # dump_str += ('{}: {}\n'.format(key, value.output()))
            dump_str += ('{},{}: {}\n'.format(key, value.count, value.output()))
        dump_str += ('</method>\n')

        dump_str += '<keyword>\n'
        for key, value in self.global_keyword_map.items():
            dump_str += ('{},{}: {}\n'.format(key, value.count, value.output()))
        dump_str += '</keyword>\n'

        dump_str += ('<type>\n')
        for key, value in self.global_type_map.items():
            if value.role == RoleType.BASIC_TYPE:
                continue
            dump_str += ('{},{}: {}\n'.format(key, value.count, value.output()))
            # dump_str += ('{}: {}\n'.format(key, value.output()))
        dump_str += ('</type>\n')

        dump_str += ('<basic type>\n')
        for key, value in self.global_type_map.items():
            if value.role != RoleType.BASIC_TYPE:
                continue
            dump_str += ('{},{}: {}\n'.format(key, value.count, value.output()))
            # dump_str += ('{}: {}\n'.format(key, value.output()))
        dump_str += ('</basic type>\n')

        dump_str += '<variable group>\n'
        for obj in self.union_variable_list:
            dump_str += '{},1: {}\n'.format(obj.name, obj.output())
        dump_str += '</variable group>\n'

        dump_str += '<method group>\n'
        for obj in self.union_method_list:
            dump_str += '{},1: {}\n'.format(obj.name, obj.output())
        dump_str += '</method group>\n'

        dump_str += '<relation>\n'
        for obj in self.union_expression_relation_list:
            dump_str += '{},1: {}\n'.format(obj.name, obj.output())
        dump_str += '</relation>\n'

        dump_str += '</block>\n'

        return dump_str

    def add_global_variable(self, name, v_type=None):
        if name is None or name == '':
            return

        self.valid_token_number += 1
        self.total_token_number += 1

        if name not in self.global_variable_map.keys():
            self.global_variable_map[name] = Variable(v_type=v_type, name=name, window_size=self.window_size)

        if v_type is not None:
            self.global_variable_map[name].type = v_type

        self.global_variable_map[name].set_path(rearrange_path(self.current_path))

    def add_global_identifier(self, name):
        if name is None or name == '':
            return

        self.total_token_number += 1

    def add_global_type(self, name, role):
        if name is None or name == '':
            return

        self.valid_token_number += 1
        self.total_token_number += 1

        if name not in self.global_type_map.keys():
            self.global_type_map[name] = VariableType(name=name, role=role)
        self.global_type_map[name].update_path(rearrange_path(self.current_path))

    def add_global_method(self, name):
        if name is None or name == '':
            return

        self.valid_token_number += 1
        self.total_token_number += 1

        if name not in self.global_method_map.keys():
            self.global_method_map[name] = Method(name=name)
        self.global_method_map[name].update_path(rearrange_path(self.current_path))

    def add_global_qualifier(self, name):
        if name is None or name == '':
            return

        self.add_global_variable(name=name)
        self.add_union_variable(name)

    def add_global_modifier(self, name):
        if name is None or name == '':
            return

        if type(name) == list:
            for _ in name:
                self.total_token_number += 1
        else:
            self.total_token_number += 1

    def add_global_keyword(self, name):
        if name is None or name == '':
            return

        self.total_token_number += 1
        self.valid_token_number += 1

        if name not in self.global_keyword_map.keys():
            self.global_keyword_map[name] = Keyword(name=name)
        self.global_keyword_map[name].update_path(rearrange_path(self.current_path))

    def add_union_relationship(self, name_arr):  # TODO: pattern in semantic vectors
        new_n_gram = rearrange_path(self.current_path)
        if name_arr is None or type(name_arr) != list:
            self.union_expression_relation_list.append(Relation(name='None', n_gram=new_n_gram))
            return

        related_var_dict = self.get_related_var(name_arr, self.window_size)

        for node, _ in related_var_dict.items():
            if node not in self.global_variable_map.keys():
                continue
            new_n_gram += self.global_variable_map[node].n_gram

        self.union_expression_relation_list.append(Relation(name='-'.join(name_arr), n_gram=new_n_gram))

    def add_union_variable(self, name, related_group=None):  # TODO: pattern in semantic vectors
        if name is None or type(name) != str:
            return

        new_n_gram = rearrange_path(self.current_path)

        if related_group is None or 'member' not in related_group.keys():
            self.union_variable_list.append(Variable(v_type=None, name=name, n_gram=new_n_gram))
            return

        related_var_dict = self.get_related_var(related_group['member'], self.window_size)
        name_arr = [name]

        for node, _ in related_var_dict.items():
            if node not in self.global_variable_map.keys():
                continue
            new_n_gram += self.global_variable_map[node].n_gram
            name_arr.append(node)

        self.union_variable_list.append(Variable(v_type=None, name="-".join(name_arr), n_gram=new_n_gram))

        if name not in self.global_variable_map.keys():
            self.global_variable_map[name] = Variable(v_type=None, name=name, window_size=self.window_size)
        self.global_variable_map[name].add_related_variable(related_group['member'])

    def add_union_method(self, name, related_group):  # TODO: pattern in semantic vectors
        new_n_gram = rearrange_path(self.current_path)

        if related_group is None or 'member' not in related_group.keys():
            self.union_method_list.append(Method(name=name, n_gram=new_n_gram))
            return

        related_var_dict = self.get_related_var(related_group['member'], self.window_size)
        name_arr = [name]

        for node, _ in related_var_dict.items():
            if node not in self.global_variable_map.keys():
                continue
            new_n_gram += self.global_variable_map[node].n_gram
            name_arr.append(node)

        self.union_method_list.append(Method(name="-".join(name_arr), n_gram=new_n_gram))

    def get_related_var(self, related_var_list, depth):
        if depth == 0:
            return {}

        related_var_map = {}
        for var in related_var_list:
            if var not in self.global_variable_map.keys():
                continue

            if var not in related_var_map:
                related_var_map[var] = 1
            else:
                related_var_map[var] += 1

            current_var_list = self.global_variable_map[var].get_related_variables()
            next_var_map = self.get_related_var(current_var_list, depth - 1)
            for key, value in next_var_map.items():
                if key not in related_var_map.keys():
                    related_var_map[key] = value
                else:
                    related_var_map[key] += value

        return related_var_map

    def push_node(self, node_name):
        node_name = transform_node(node_name)
        self.current_path.append(node_name)

    def pop_node(self, node_name):
        if len(self.current_path) == 0:
            return
        # if node_name in self.current_path:
        #     self.current_path.remove(node_name)
        self.current_path.pop()  # TODO: something wrong in original implementation cause commented if doesn't work

    def parse(self, obj, file_path, output_file_path):
        if obj is None:
            return

        self.file_path = file_path
        self.output_file_path = output_file_path

        if isinstance(obj, tree.CompilationUnit):
            if obj is None:
                return None

            if obj.types is not None:
                for declaration in obj.types:
                    self.parse_tree_declaration(declaration)
        elif isinstance(obj, tree.Declaration):
            return self.parse_tree_declaration(obj)
        elif isinstance(obj, tree.Statement):
            return self.parse_tree_statement(obj)
        elif isinstance(obj, tree.Expression):
            return self.parse_tree_expression(obj)

    def parse_block(self, body):
        if body is None:
            return
        if type(body) != list:
            log.error('error input for [parse block]: [{}]'.format(body))
            return

        for body_item in body:
            self.parse_block_statement(body_item)

    def parse_block_statement(self, body):
        if isinstance(body, tree.LocalVariableDeclaration):
            self.parse_tree_local_variable_declaration(body)
        elif isinstance(body, tree.ClassDeclaration):
            self.parse_tree_class_declaration(body)
        elif isinstance(body, tree.EnumDeclaration):
            self.parse_tree_enum_declaration(body)
        elif isinstance(body, tree.InterfaceDeclaration):
            self.parse_tree_interface_declaration(body)
        elif isinstance(body, tree.AnnotationDeclaration):
            self.parse_tree_annotation_declaration(body)
        elif isinstance(body, tree.Statement):
            self.parse_tree_statement(body)
        else:
            log.debug('unknown body type {}'.format(body))

    def parse_expression(self, expression):
        if isinstance(expression, tree.Assignment):
            return self.parse_tree_assignment(expression)
        else:
            return self.parse_expressionl(expression)

    def parse_expressionl(self, expression):
        if isinstance(expression, tree.TernaryExpression):
            return self.parse_tree_ternary_expression(expression)
        elif isinstance(expression, tree.LambdaExpression):
            return self.parse_tree_lambda_expression(expression)
        elif isinstance(expression, tree.MethodReference):
            return self.parse_tree_method_reference(expression)
        else:
            return self.parse_expression_2(expression)

    def parse_expression_2(self, expression):
        if isinstance(expression, tree.BinaryOperation):
            return self.parse_tree_binary_operation(expression)
        else:
            return self.parse_expression_3(expression)

    def parse_expression_3(self, expression):
        if isinstance(expression, tree.Cast):
            return self.pares_tree_cast(expression)
        elif isinstance(expression, tree.LambdaExpression):
            return self.parse_tree_lambda_expression(expression)
        else:
            return self.parse_primary(expression)

    def parse_primary(self, expression):
        if expression is None:
            return

        if isinstance(expression, tree.Literal):
            self.add_global_identifier(expression.value)
        elif isinstance(expression, tree.ExplicitConstructorInvocation):
            return self.parse_tree_explicit_constructor_invocation(expression)
        elif isinstance(expression, tree.This):
            self.add_global_identifier('this')
            self.parse_tree_this(expression)
        elif isinstance(expression, tree.SuperMethodInvocation):
            return self.parse_tree_super_method_invocation(expression)
        elif isinstance(expression, tree.SuperConstructorInvocation):
            return self.parse_tree_super_constructor_invocation(expression)
        elif isinstance(expression, tree.SuperMemberReference):
            return self.parse_tree_super_member_reference(expression)
        elif isinstance(expression, tree.ArrayCreator):
            return self.parse_tree_array_creator(expression)
        elif isinstance(expression, tree.ClassCreator):
            return self.parse_tree_class_creator(expression)
        elif isinstance(expression, tree.MethodInvocation):
            return self.parse_tree_method_invocation(expression)
        elif isinstance(expression, tree.ClassReference):
            return self.parse_tree_class_reference(expression)
        elif isinstance(expression, tree.InnerClassCreator):
            return self.parse_tree_inner_class_creator(expression)
        elif isinstance(expression, tree.VoidClassReference):
            return self.parse_tree_void_class_reference(expression)
        elif isinstance(expression, tree.MemberReference):
            return self.parse_tree_member_reference(expression)
        elif isinstance(expression, tree.Statement):
            return self.parse_tree_statement(expression)
        elif isinstance(expression, tree.Expression):
            return self.parse_expression(expression)
        else:
            log.debug('unknown primary {}'.format(expression))
            return None

    def parse_tree_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.Declaration):
            log.error('error input for [tree declaration]: [{}]'.format(obj))
            return None

        self.add_global_modifier(unpack_modifier(parse_inner_modifiers(obj.modifiers)))

        if isinstance(obj, tree.TypeDeclaration):
            return self.parse_tree_type_declaration(obj)
        elif isinstance(obj, tree.PackageDeclaration):
            return None
        elif isinstance(obj, tree.MethodDeclaration):
            return self.parse_tree_method_declaration(obj)
        elif isinstance(obj, tree.FieldDeclaration):
            return self.parse_tree_field_declaration(obj)
        elif isinstance(obj, tree.ConstructorDeclaration):
            return self.parse_tree_constructor_declaration(obj)
        elif isinstance(obj, tree.ConstantDeclaration):
            return self.parse_tree_constant_declaration(obj)
        elif isinstance(obj, tree.VariableDeclaration):
            return self.parse_tree_variable_declaration(obj)
        elif isinstance(obj, tree.FormalParameter):
            return self.parse_tree_formal_parameter(obj)
        elif isinstance(obj, tree.TryResource):
            return self.parse_tree_try_resource(obj)
        elif isinstance(obj, tree.CatchClauseParameter):
            return self.parse_tree_catch_clause_parameter(obj)
        elif isinstance(obj, tree.EnumConstantDeclaration):
            return self.parse_tree_enum_constant_declaration(obj)
        elif isinstance(obj, tree.AnnotationMethod):
            return self.parse_tree_annotation_method(obj)
        else:
            log.debug('unknown [parse tree declaration]: {}'.format(obj))

    def parse_tree_type_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.TypeDeclaration):
            log.error('error input for [tree type declaration]: [{}]'.format(obj))
            return None

        if isinstance(obj, tree.ClassDeclaration):
            return self.parse_tree_class_declaration(obj)
        elif isinstance(obj, tree.EnumDeclaration):
            return self.parse_tree_enum_declaration(obj)
        elif isinstance(obj, tree.InterfaceDeclaration):
            return self.parse_tree_interface_declaration(obj)
        elif isinstance(obj, tree.AnnotationDeclaration):
            return self.parse_tree_annotation_declaration(obj)
        else:
            log.debug('unknown [parse tree type declaration]: {}'.format(obj))

    def parse_tree_class_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.ClassDeclaration):
            log.error('error input for [tree class declaration]: [{}]'.format(obj))
            return None

        self.add_global_keyword('class')

        self.add_global_type(obj.name, RoleType.REFERENCE_TYPE)
        self.parse_inner_type_parameters(obj.type_parameters)

        self.add_global_type(unpack_type(self.parse_tree_type(obj.extends)), RoleType.REFERENCE_TYPE)
        if obj.implements is not None:
            for impl in obj.implements:
                self.add_global_type(unpack_type(self.parse_tree_type(impl)), RoleType.REFERENCE_TYPE)

        self.parse_inner_class_body(obj.body)

    def parse_tree_enum_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.EnumDeclaration):
            log.error('error input for [tree enum declaration]: [{}]'.format(obj))
            return None

        self.add_global_keyword('enum')

        self.add_global_type(obj.name, RoleType.REFERENCE_TYPE)
        self.parse_tree_enum_body(obj.body)

    def parse_tree_interface_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.InterfaceDeclaration):
            log.error('error input for [tree interface declaration]: [{}]'.format(obj))
            return None

        self.add_global_keyword('interface')
        self.add_global_type(obj.name, RoleType.REFERENCE_TYPE)
        self.parse_inner_type_parameters(obj.type_parameters)
        self.parse_inner_class_body(obj.body)

    def parse_tree_annotation_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.AnnotationDeclaration):
            log.error('error input for [tree annotation declaration]: [{}]'.format(obj))
            return None

        self.add_global_type(obj.name, RoleType.REFERENCE_TYPE)
        self.parse_inner_annotation_type_body(obj.body)

    def parse_tree_type(self, obj):
        if obj is None:
            return None
        if not isinstance(obj, tree.Type):
            log.error('error input for [tree type]: [{}]'.format(obj))
            return

        if isinstance(obj, tree.BasicType):
            return self.parse_tree_basic_type(obj)
        elif isinstance(obj, tree.ReferenceType):
            return self.parse_tree_reference_type(obj)
        else:
            log.debug('unknown parse tree type: {}'.format(obj))
            return None

    def parse_tree_basic_type(self, obj):
        if type(obj) != tree.BasicType:
            log.error('error input for [tree basic type]: [{}]'.format(obj))
            return None

        self.add_global_type(obj.name, RoleType.BASIC_TYPE)
        return {'type_name': obj.name, 'type': RoleType.BASIC_TYPE}

    def parse_tree_reference_type(self, obj):
        if type(obj) != tree.ReferenceType:
            log.error('error input for [tree reference type]: [{}]'.format(obj))
            return None

        self.add_global_type(obj.name, RoleType.REFERENCE_TYPE)
        self.parse_inner_nonwildcard_type_arguments(obj.arguments)
        return {'type_name': obj.name, 'type': RoleType.REFERENCE_TYPE}

    def parse_tree_type_argument(self, obj):
        if type(obj) != tree.TypeArgument:
            log.error('error input for [tree type argument]: [{}]'.format(obj))
            return None

        return self.parse_tree_type(obj.type)

    def parse_tree_type_parameter(self, obj):
        if obj is None or not isinstance(obj, tree.TypeParameter):
            log.error('error input for [tree type parameter]: [{}]'.format(obj))
            return None

        if obj.name is None:
            return None

        extends_list = []
        if obj.extends is not None:
            for refer_type in obj.extends:
                extends_list.append(self.parse_tree_reference_type(refer_type))

        return {'type': [obj.name], 'extends': extends_list}

    def parse_tree_element_array_value(self, obj):
        if obj is None or not isinstance(obj, tree.ElementArrayValue):
            log.error('error input for [tree element array value]: [{}]'.format(obj))
            return None

        if obj.values is not None:
            for value in obj.values:
                self.parse_element_value(value)

    def parse_tree_method_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.MethodDeclaration):
            log.error('error input for [parse tree method declaration]: [{}]'.format(obj))
            return None

        if self.method_depth == 0:
            self.clear()

            if obj.position is not None:
                self.method_start = obj.position[0]
            if obj.end_position is not None:
                self.method_end = obj.end_position[0]

            self.push_node(NodeType.METHOD_DECLARATION)

        self.method_depth += 1

        self.parse_inner_type_parameters(obj.type_parameters)
        self.add_global_method(obj.name)
        self.parse_tree_type(obj.return_type)

        self.parse_inner_formal_parameters(obj.parameters)
        self.parse_block(obj.body)

        self.pop_node(NodeType.METHOD_DECLARATION)

        self.method_depth -= 1

        if self.method_depth == 0:
            with open(self.output_file_path, 'a+') as fileOut:
                fileOut.write(self.dump())
            self.clear()

    def parse_tree_field_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.FieldDeclaration):
            log.error('error input for [tree field declaration]: [{}]'.format(obj))
            return None

        if isinstance(obj, tree.ConstantDeclaration):
            return self.parse_tree_constant_declaration(obj)

        self.parse_tree_type(obj.type)

        if obj.declarators is not None:
            for declarator in obj.declarators:
                self.parse_tree_variable_declarator(declarator)

    def parse_tree_constructor_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.ConstructorDeclaration):
            log.error('error input for [parse tree constructor declaration]: [{}]'.format(obj))
            return None

        if self.method_depth == 0:
            self.clear()
            if obj.position is not None:
                self.method_start = obj.position[0]
            if obj.end_position is not None:
                self.method_end = obj.end_position[0]
        self.method_depth += 1

        self.push_node(NodeType.METHOD_DECLARATION)

        self.parse_inner_type_parameters(obj.type_parameters)
        self.add_global_method(obj.name)
        self.parse_inner_formal_parameters(obj.parameters)
        self.parse_block(obj.body)

        self.pop_node(NodeType.METHOD_DECLARATION)

        self.method_depth -= 1

        if self.method_depth == 0:
            with open(self.output_file_path, 'a+') as fileOut:
                fileOut.write(self.dump())
            self.clear()

    def parse_tree_constant_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.ConstantDeclaration):
            log.error('error input for [tree constant declaration]: [{}]'.format(obj))
            return None

        type_dict = self.parse_tree_type(obj.type)
        self.add_global_type(unpack_type(type_dict), RoleType.REFERENCE_TYPE)

        if obj.declarators is not None:
            for declarator in obj.declarators:
                self.parse_tree_variable_declarator(declarator)

    def parse_tree_array_initializer(self, obj):
        if obj is None:
            return None
        if not isinstance(obj, tree.ArrayInitializer):
            log.error('error input for [tree array initializer]: [{}]'.format(obj))
            return None

        init_list = list()
        if obj.initializers is not None:
            for initializer in obj.initializers:
                if initializer is None:
                    continue
                cur_init = self.parse_inner_variable_initializer(initializer)
                init_list.append(cur_init)

        return merge_dictionaries(init_list)

    def parse_tree_variable_declaration(self, obj):
        if obj is None:
            return None
        if not isinstance(obj, tree.VariableDeclaration):
            log.error('error input for [tree variable declaration]: [{}]'.format(obj))
            return None

        if isinstance(obj, tree.LocalVariableDeclaration):
            return self.parse_tree_local_variable_declaration(obj)

        type_dict = self.parse_tree_type(obj.type)
        var_type = None
        if type_dict is not None:
            var_type = type_dict['type']

        declarators = obj.declarators
        if declarators is not None:
            for declarator in declarators:
                declarator_dict = self.parse_tree_variable_declarator(declarator)
                self.add_global_variable(declarator_dict['var_name'], var_type)

    def parse_tree_local_variable_declaration(self, obj):
        if obj is None or type(obj) != tree.LocalVariableDeclaration:
            log.error('error input for [tree local variable declaration]: [{}]'.format(obj))
            return

        self.push_node(NodeType.LOCAL_VARIABLE_DECLARATION)
        var_type_dict = self.parse_tree_type(obj.type)
        var_type = None
        if var_type_dict is not None:
            var_type = var_type_dict['type_name']

        for declarator in obj.declarators:
            declarator_dict = self.parse_tree_variable_declarator(declarator)
            if declarator_dict is None:
                continue

            self.add_global_variable(name=declarator_dict['var_name'], v_type=var_type)
        self.pop_node(NodeType.LOCAL_VARIABLE_DECLARATION)

    def parse_tree_variable_declarator(self, obj):
        if obj is None or type(obj) != tree.VariableDeclarator:
            log.error('error input for [tree variable declarator]: [{}]'.format(obj))
            return

        var_name = obj.name
        initializer = obj.initializer
        init_dict = None
        if initializer is not None:
            init_dict = self.parse_inner_variable_initializer(initializer)

        self.add_union_variable(var_name, init_dict)

        return {'var_name': var_name, 'init': init_dict, 'member': [var_name]}

    def parse_inner_variable_initializer(self, initializer):
        if isinstance(initializer, tree.ArrayInitializer):
            return self.parse_tree_array_initializer(initializer)
        elif isinstance(initializer, tree.Expression):
            return self.parse_tree_expression(initializer)
        else:
            log.debug('unknown [parse tree variable declarator]->[initializer]: {}'.format(initializer))

    def parse_tree_formal_parameter(self, obj):
        if obj is None or not isinstance(obj, tree.FormalParameter):
            log.error('error input for [tree formal parameter]: [{}]'.format(obj))
            return None

        var_type = self.parse_tree_type(obj.type)
        var_name = obj.name

        self.add_global_variable(var_name, unpack_type(var_type))
        self.add_union_variable(var_name)

        return merge_dictionaries({'member': [var_name]}, var_type)

    def parse_tree_inferred_formal_parameter(self, obj):
        if obj is None or not isinstance(obj, tree.InferredFormalParameter):
            log.error('error input for [inferred formal parameter]: [{}]'.format(obj))
            return None

        self.add_global_variable(obj.name)
        self.add_union_variable(obj.name)

        return {'member': [obj.name]}

    def parse_tree_statement(self, obj):
        if obj is None or not isinstance(obj, tree.Statement):
            log.error('error input for [parse tree statement]: [{}]'.format(obj))
            return None

        if isinstance(obj, tree.IfStatement):
            return self.parse_tree_if_statement(obj)
        elif isinstance(obj, tree.WhileStatement):
            return self.parse_tree_while_statement(obj)
        elif isinstance(obj, tree.DoStatement):
            return self.parse_tree_do_statement(obj)
        elif isinstance(obj, tree.ForStatement):
            return self.parse_tree_for_statement(obj)
        elif isinstance(obj, tree.AssertStatement):
            return self.parse_tree_assert_statement(obj)
        elif isinstance(obj, tree.BreakStatement):
            self.add_global_keyword('break')
            return None
        elif isinstance(obj, tree.ContinueStatement):
            self.add_global_keyword('continue')
            return None
        elif isinstance(obj, tree.ReturnStatement):
            return self.parse_tree_return_statement(obj)
        elif isinstance(obj, tree.ThrowStatement):
            return self.parse_tree_throw_statement(obj)
        elif isinstance(obj, tree.SynchronizedStatement):
            return self.parse_tree_synchronized_statement(obj)
        elif isinstance(obj, tree.TryStatement):
            return self.parse_tree_try_statement(obj)
        elif isinstance(obj, tree.SwitchStatement):
            return self.parse_tree_switch_statement(obj)
        elif isinstance(obj, tree.BlockStatement):
            return self.parse_tree_block_statement(obj)
        elif isinstance(obj, tree.StatementExpression):
            return self.parse_tree_statement_expression(obj)
        elif isinstance(obj, tree.CatchClause):
            return self.parse_tree_catch_clause(obj)
        elif type(obj) == tree.Statement:
            return None
        else:
            log.debug('unknown [parse tree statement]: {}'.format(obj))

    def parse_tree_if_statement(self, obj):
        if obj is None or not isinstance(obj, tree.IfStatement):
            log.error('error input for [tree if statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('if')

        self.push_node(NodeType.IF_CONDITION)
        self.parse_expression(obj.condition)
        self.pop_node(NodeType.IF_CONDITION)

        self.push_node(NodeType.ELSE_BODY)
        self.parse_expression(obj.then_statement)
        self.pop_node(NodeType.ELSE_BODY)

        self.parse_expression(obj.else_statement)

    def parse_tree_while_statement(self, obj):
        if obj is None or not isinstance(obj, tree.WhileStatement):
            log.error('error input for [tree while statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('loop')

        self.push_node(NodeType.WHILE_CONDITION)
        self.parse_expression(obj.condition)
        self.pop_node(NodeType.WHILE_CONDITION)

        self.push_node(NodeType.WHILE_BODY)
        self.parse_tree_statement(obj.body)
        self.pop_node(NodeType.WHILE_BODY)

    def parse_tree_do_statement(self, obj):
        if obj is None or not isinstance(obj, tree.DoStatement):
            log.error('error input for [tree do statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('loop')

        self.push_node(NodeType.DO_BODY)
        self.parse_tree_statement(obj.body)
        self.pop_node(NodeType.DO_BODY)

        self.push_node(NodeType.DO_CONDITION)
        self.parse_expression(obj.condition)
        self.pop_node(NodeType.DO_CONDITION)

    def parse_tree_for_statement(self, obj):
        if obj is None or not isinstance(obj, tree.ForStatement):
            log.error('error input for [tree for statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('loop')

        for_control = obj.control
        if for_control is not None:
            if isinstance(for_control, tree.ForControl):
                self.parse_tree_for_control(for_control)
            elif isinstance(for_control, tree.EnhancedForControl):
                self.parse_tree_enhanced_for_control(for_control)

        self.push_node(NodeType.FOR_BODY)
        self.parse_tree_statement(obj.body)
        self.pop_node(NodeType.FOR_BODY)

    def parse_tree_assert_statement(self, obj):
        if obj is None or not isinstance(obj, tree.AssertStatement):
            log.error('error input for [tree assert statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('assert')

        self.push_node(NodeType.ASSERT_CONDITION)
        self.parse_expression(obj.condition)
        self.pop_node(NodeType.ASSERT_CONDITION)

        self.push_node(NodeType.ASSERT_BODY)
        self.parse_expression(obj.value)
        self.pop_node(NodeType.ASSERT_BODY)

    def parse_tree_return_statement(self, obj):
        if obj is None or not isinstance(obj, tree.ReturnStatement):
            log.error('error input for [tree return statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('return')

        self.push_node(NodeType.RETURN)
        self.parse_expression(obj.expression)
        self.pop_node(NodeType.RETURN)

    def parse_tree_throw_statement(self, obj):
        if obj is None or not isinstance(obj, tree.ThrowStatement):
            log.error('error input for [tree throw statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('throw')

        self.push_node(NodeType.THROW)
        self.parse_expression(obj.expression)
        self.pop_node(NodeType.THROW)

    def parse_tree_synchronized_statement(self, obj):
        if obj is None or not isinstance(obj, tree.SynchronizedStatement):
            log.error('error input for [tree synchronized statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('synchronized')

        self.push_node(NodeType.SYNCHRONIZED_CONDITION)
        self.parse_expression(obj.lock)
        self.pop_node(NodeType.SYNCHRONIZED_CONDITION)

        self.push_node(NodeType.SYNCHRONIZED_BODY)
        self.parse_block(obj.block)
        self.pop_node(NodeType.SYNCHRONIZED_BODY)

    def parse_tree_try_statement(self, obj):
        if obj is None or not isinstance(obj, tree.TryStatement):
            log.error('error input for [tree try statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('try')

        resources = obj.resources
        if resources is not None:
            for resource in resources:
                self.parse_tree_try_resource(resource)

        self.push_node(NodeType.TRY_BODY)
        self.parse_block(obj.block)
        self.pop_node(NodeType.TRY_BODY)

        self.push_node(NodeType.CATCH_BODY)
        catches = obj.catches
        if catches is not None:
            for catch in catches:
                self.parse_tree_catch_clause(catch)
        self.pop_node(NodeType.CATCH_BODY)

        self.push_node(NodeType.FINALLY_BODY)
        self.parse_block(obj.finally_block)
        self.pop_node(NodeType.FINALLY_BODY)

    def parse_tree_switch_statement(self, obj):
        if obj is None or not isinstance(obj, tree.SwitchStatement):
            log.error('error input for [tree switch statement]: [{}]'.format(obj))
            return None

        self.add_global_keyword('switch')

        self.push_node(NodeType.SWITCH_CONDITION)
        self.parse_expression(obj.expression)
        self.pop_node(NodeType.SWITCH_CONDITION)

        self.parse_inner_switch_block_groups(obj.cases)

    def parse_tree_block_statement(self, obj):
        if obj is None or not isinstance(obj, tree.BlockStatement):
            log.error('error input for [tree block statement]: [{}]'.format(obj))
            return None

        return self.parse_block(obj.statements)

    def parse_tree_statement_expression(self, obj):
        if obj is None or not isinstance(obj, tree.StatementExpression):
            log.error('error input for [tree statement expression]: [{}]'.format(obj))
            return None

        self.parse_expression(obj.expression)

    def parse_tree_try_resource(self, obj):
        if obj is None or not isinstance(obj, tree.TryResource):
            log.error('error input for [tree try resource]: [{}]'.format(obj))
            return None

        type_dict = self.parse_tree_reference_type(obj.type)
        self.add_global_variable(obj.name, unpack_type(type_dict))
        expression_dict = self.parse_expression(obj.value)
        self.add_union_variable(obj.name, expression_dict)

    def parse_tree_catch_clause(self, obj):
        if obj is None or not isinstance(obj, tree.CatchClause):
            log.error('error input for [tree catch clause]: [{}]'.format(obj))
            return None

        self.add_global_keyword('catch')

        self.parse_tree_catch_clause_parameter(obj.parameter)

        self.parse_block(obj.block)

    def parse_tree_catch_clause_parameter(self, obj):
        if obj is None or not isinstance(obj, tree.CatchClauseParameter):
            log.error('error input for [tree catch clause parameter]: [{}]'.format(obj))
            return None

        types = obj.types
        last_type = None
        if types is not None:
            for name in types:
                self.add_global_type(name, RoleType.REFERENCE_TYPE)
                last_type = name

        self.add_global_variable(obj.name, last_type)
        self.add_union_variable(obj.name)

    def parse_tree_switch_statement_case(self, obj):
        if obj is None or not isinstance(obj, tree.SwitchStatementCase):
            log.error('error input for [tree switch statement case]: [{}]'.format(obj))
            return None

        self.add_global_keyword('case')

        self.push_node(NodeType.CASE_LABEL)
        if obj.case is not None:
            if isinstance(obj.case, tree.Expression):
                self.parse_expression(obj.case)
            else:
                self.add_global_identifier(obj.case)

        self.pop_node(NodeType.CASE_LABEL)

        self.push_node(NodeType.CASE_BODY)
        if obj.statements is not None:
            for statement in obj.statements:
                self.parse_block_statement(statement)
        self.pop_node(NodeType.CASE_BODY)

    def parse_tree_for_control(self, obj):
        if obj is None or not isinstance(obj, tree.ForControl):
            log.error('error input for [tree for control]: [{}]'.format(obj))
            return None

        init = obj.init
        if init is not None:
            if isinstance(init, tree.VariableDeclaration):
                self.parse_tree_variable_declaration(init)
            elif type(init) == list:
                for expression in init:
                    self.parse_expression(expression)

        condition = obj.condition
        self.push_node(NodeType.FOR_CONDITION)
        self.parse_expression(condition)
        self.pop_node(NodeType.FOR_CONDITION)

        self.push_node(NodeType.FOR_BODY)
        update = obj.update
        if update is not None:
            for expression in update:
                self.parse_expression(expression)
        self.pop_node(NodeType.FOR_BODY)

    def parse_tree_enhanced_for_control(self, obj):
        if obj is None or not isinstance(obj, tree.EnhancedForControl):
            log.error('error input for [tree enhanced for control]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.FOR_CONDITION)
        self.parse_tree_variable_declaration(obj.var)
        self.pop_node(NodeType.FOR_CONDITION)

        self.push_node(NodeType.FOR_BODY)
        self.parse_expression(obj.iterable)
        self.pop_node(NodeType.FOR_BODY)

    def parse_tree_expression(self, obj):
        return self.parse_expression(obj)

    def parse_tree_assignment(self, obj):
        if obj is None or type(obj) != tree.Assignment:
            log.error('error input for [tree assignment]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.EXPRESSION_ASSIGN)
        expressionl = self.parse_expressionl(obj.expressionl)
        value = self.parse_tree_expression(obj.value)
        self.pop_node(NodeType.EXPRESSION_ASSIGN)

        if expressionl is not None and type(expressionl) == dict \
                and 'member' in expressionl.keys() and value is not None and 'member' in value.keys():
            for member in expressionl['member']:
                self.add_union_variable(member, value)

        return {'left': expressionl, 'right': value,
                'member': transform_to_array(expressionl, value)}

    def parse_tree_ternary_expression(self, obj):
        if obj is None or type(obj) != tree.TernaryExpression:
            log.error('error input for [tree ternary expression]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.EXPRESSION_TERNARY)
        condition = self.parse_expression_2(obj.condition)
        if_true = self.parse_expression(obj.if_true)
        if_false = self.parse_expressionl(obj.if_false)
        self.pop_node(NodeType.EXPRESSION_TERNARY)

        return {'condition': condition, 'value': transform_to_array(if_true, if_false),
                'member': transform_to_array(condition, if_true, if_false)}

    def parse_tree_binary_operation(self, obj):
        if obj is None or type(obj) != tree.BinaryOperation:
            log.error('error input for [tree binary operation]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.EXPRESSION_BINARY)
        operation_left = self.parse_expression_2(obj.operandl)
        operation_right = None
        if isinstance(obj.operandr, tree.Type):
            self.parse_tree_type(obj.operandr)
        else:
            operation_right = self.parse_expression_2(obj.operandr)
        self.pop_node(NodeType.EXPRESSION_BINARY)

        member_arr = transform_to_array(operation_left, operation_right)
        operation_type = parse_operation_node_type(obj.operator)
        self.push_node(operation_type)
        self.add_union_relationship(member_arr)
        self.pop_node(operation_type)

        return {'member': transform_to_array(operation_left, operation_right)}

    def pares_tree_cast(self, obj):
        if obj is None or type(obj) != tree.Cast:
            log.error('error input for [tree cast]: [{}]'.format(obj))
            return None

        self.parse_tree_type(obj.type)
        return self.parse_expression_3(obj.expression)

    def parse_tree_method_reference(self, obj):
        if obj is None or type(obj) != tree.MethodReference:
            log.error('error input for [tree method reference]: [{}]'.format(obj))
            return None

        field = self.parse_expression_2(obj.expression)

        if field is None or field == '':
            return

        self.valid_token_number += 1
        self.total_token_number += 1

        if field not in self.global_field_map.keys():
            self.global_field_map[field] = FieldAccess(name=field)

        self.global_field_map[field].update_path(rearrange_path(self.current_path))

        method = obj.method
        if method is not None:
            if isinstance(method, tree.MemberReference):
                self.parse_tree_member_reference(obj.method)
            elif isinstance(method, tree.Expression):
                return self.parse_expression(method)
            else:
                log.debug('unknown [parse tree method reference]-->[obj.method]: [{}]'.format(method))

        self.parse_inner_nonwildcard_type_arguments(obj.type_arguments)

    def parse_tree_lambda_expression(self, obj):
        if obj is None or type(obj) != tree.LambdaExpression:
            log.error('error input for [lambda expression]: [{}]'.format(obj))
            return None

        self.add_global_keyword('lambda')

        self.push_node(NodeType.EXPRESSION_LAMBDA)
        parameters = obj.parameters
        if parameters is not None:
            for param in parameters:
                if type(param) == tree.InferredFormalParameter:
                    self.parse_tree_inferred_formal_parameter(param)
                elif type(param) == tree.FormalParameter:
                    self.parse_tree_formal_parameter(param)
                else:
                    self.parse_expression_2(param)

        self.parse_inner_lambda_method_body(obj.body)

        self.pop_node(NodeType.EXPRESSION_LAMBDA)

    def parse_tree_this(self, obj):
        if obj is None or not isinstance(obj, tree.This):
            log.error('error input for [tree this]: [{}]'.format(obj))
            return None
        return self.parse_inner_primary(obj)

    def parse_tree_member_reference(self, obj):
        if obj is None or type(obj) != tree.MemberReference:
            log.error('error input for [tree member reference]: [{}]'.format(obj))
            return None

        member = obj.member

        selector = self.parse_inner_primary(obj)
        if selector is not None and 'selector' in selector.keys():
            self.push_node(NodeType.ARRAY_SELECTOR)

        if selector is not None and 'qualifier' in selector.keys():
            self.add_global_method(obj.member)
            member = ''.join(selector['qualifier'])

        self.add_global_variable(member)

        if selector is not None and 'member' in selector:
            self.add_union_variable(member, selector)

        if selector is not None and 'selector' in selector.keys():
            self.pop_node(NodeType.ARRAY_SELECTOR)

        return {'member': [member]}

    def parse_tree_invocation(self, obj):
        if obj is None or not isinstance(obj, tree.Invocation):
            log.error('error input for [tree invocation]: [{}]'.format(obj))
            return None

        if isinstance(obj, tree.ExplicitConstructorInvocation):
            return self.parse_tree_explicit_constructor_invocation(obj)
        elif isinstance(obj, tree.SuperConstructorInvocation):
            return self.parse_tree_super_constructor_invocation(obj)
        elif isinstance(obj, tree.MethodInvocation):
            return self.parse_tree_method_invocation(obj)
        elif isinstance(obj, tree.SuperMethodInvocation):
            return self.parse_tree_super_method_invocation(obj)

    def parse_tree_explicit_constructor_invocation(self, obj):
        if obj is None or type(obj) != tree.ExplicitConstructorInvocation:
            log.error('error input for [tree explicit constructor invocation]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.INVOCATION_CONSTRUCTOR)

        self.parse_inner_primary(obj)

        self.parse_inner_nonwildcard_type_arguments(obj.type_arguments)

        arg_list = self.parse_inner_arguments(obj.arguments)
        arg_dict = merge_dictionaries(arg_list)

        self.pop_node(NodeType.INVOCATION_CONSTRUCTOR)

        self.add_union_method('this', arg_dict)

        return arg_dict

    def parse_tree_super_constructor_invocation(self, obj):
        if obj is None or type(obj) != tree.SuperConstructorInvocation:
            log.error('error input for [tree super constructor invocation]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.INVOCATION_CONSTRUCTOR)

        self.parse_inner_primary(obj)
        self.parse_inner_nonwildcard_type_arguments(obj.type_arguments)

        exp_list = self.parse_inner_arguments(obj.arguments)
        arg_dict = merge_dictionaries(exp_list)

        self.pop_node(NodeType.INVOCATION_CONSTRUCTOR)

        self.add_union_method('super', arg_dict)

        return arg_dict

    def parse_tree_method_invocation(self, obj):
        if obj is None or type(obj) != tree.MethodInvocation:
            log.error('error input for [tree method invocation]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.INVOCATION_METHOD)
        primary = self.parse_inner_primary(obj)

        self.parse_inner_nonwildcard_type_arguments(obj.type_arguments)

        self.add_global_method(obj.member)

        arg_list = self.parse_inner_arguments(obj.arguments)
        arg_dict_l = merge_dictionaries(arg_list)

        if arg_dict_l is not None and 'member' in arg_dict_l.keys():
            self.add_union_variable(unpack_member(primary), arg_dict_l)

        arg_dict = merge_dictionaries(arg_list, primary)

        self.pop_node(NodeType.INVOCATION_METHOD)

        self.add_union_method(obj.member, arg_dict)

        return arg_dict

    def parse_tree_super_method_invocation(self, obj):
        if obj is None or type(obj) != tree.SuperMethodInvocation:
            log.error('error input for [tree super method invocation]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.INVOCATION_METHOD)
        self.parse_inner_primary(obj)

        self.parse_inner_nonwildcard_type_arguments(obj.type_arguments)

        self.add_global_method(obj.member)

        self.parse_inner_nonwildcard_type_arguments(obj.type_arguments)

        arg_list = self.parse_inner_arguments(obj.arguments)
        arg_dict = merge_dictionaries(arg_list)

        self.pop_node(NodeType.INVOCATION_METHOD)

        arg_dict['method'] = [obj.member]

        self.add_union_method(obj.member, arg_dict)

        return arg_dict

    def parse_tree_super_member_reference(self, obj):
        if obj is None or type(obj) != tree.SuperMemberReference:
            log.error('error input for [tree super member reference]: [{}]'.format(obj))
            return None

        selector = self.parse_inner_primary(obj)
        if selector is not None and 'selector' in selector.keys():
            self.push_node(NodeType.ARRAY_SELECTOR)

        self.add_global_variable(name=obj.member)
        self.add_union_variable(obj.member, selector)

        if selector is not None and 'selector' in selector.keys():
            self.pop_node(NodeType.ARRAY_SELECTOR)

        return {'member': [obj.member]}

    def parse_tree_array_selector(self, obj):
        if obj is None or type(obj) != tree.ArraySelector:
            log.error('error input for [tree array selector]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.ARRAY_SELECTOR)
        expression_dict = self.parse_expression(obj.index)
        self.pop_node(NodeType.ARRAY_SELECTOR)
        if expression_dict is not None:
            expression_dict['selector'] = 'array'
        else:
            expression_dict = {'selector': 'array'}

        return expression_dict

    def parse_tree_class_reference(self, obj):
        if obj is None or not isinstance(obj, tree.ClassReference):
            log.error('error input for [tree class reference]: [{}]'.format(obj))
            return None

        refer = self.parse_tree_type(obj.type)
        self.parse_inner_primary(obj)

        return refer

    def parse_tree_void_class_reference(self, obj):
        if obj is None or not isinstance(obj, tree.VoidClassReference):
            log.error('error input for [tree void class reference]: [{}]'.format(obj))
            return None

        self.parse_inner_primary(obj)

    def parse_tree_creator(self, obj):
        if obj is None or not isinstance(obj, tree.Creator):
            log.error('error input for [tree creator]: [{}]'.format(obj))
            return None
        if isinstance(obj, tree.ArrayCreator):
            return self.parse_tree_array_creator(obj)
        elif isinstance(obj, tree.ClassCreator):
            return self.parse_tree_class_creator(obj)
        elif isinstance(obj, tree.InnerClassCreator):
            return self.parse_tree_inner_class_creator(obj)
        else:
            log.debug('unknown [tree creator]: [{}]'.format(obj))

    def parse_tree_array_creator(self, obj):
        if obj is None or type(obj) != tree.ArrayCreator:
            log.error('error input for [tree array creator]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.CREATOR_ARRAY)
        self.add_global_type(obj.type, role=RoleType.REFERENCE_TYPE)

        dim_list = []
        if obj.dimensions is not None:
            for dim in obj.dimensions:
                if dim is None:
                    continue
                dim_list.append(self.parse_expression(dim))
        dim_dict = merge_dictionaries(dim_list)
        initializer = self.parse_tree_array_initializer(obj.initializer)

        self.parse_inner_primary(obj)

        self.pop_node(NodeType.CREATOR_ARRAY)
        return merge_dictionaries(dim_dict, initializer)

    def parse_tree_class_creator(self, obj):
        if obj is None or type(obj) != tree.ClassCreator:
            log.error('error input for [tree class creator]: [{}]'.format(obj))
            return None

        self.add_global_keyword('new')

        self.push_node(NodeType.CREATOR_CLASS)
        self.parse_inner_nonwildcard_type_arguments(obj.constructor_type_arguments)
        self.parse_tree_reference_type(obj.type)

        arg_list = self.parse_inner_arguments(obj.arguments)
        self.parse_inner_class_body(obj.body)
        self.pop_node(NodeType.CREATOR_CLASS)

        return merge_dictionaries(arg_list)

    def parse_tree_inner_class_creator(self, obj):
        if obj is None or type(obj) != tree.InnerClassCreator:
            log.error('error input for [tree inner class creator]: [{}]'.format(obj))
            return None

        self.push_node(NodeType.CREATOR_CLASS)
        self.parse_tree_reference_type(obj.type)
        arg_list = self.parse_inner_arguments(obj.arguments)
        self.parse_inner_class_body(obj.body)
        self.pop_node(NodeType.CREATOR_CLASS)

        return merge_dictionaries(arg_list)

    def parse_tree_enum_body(self, obj):
        if obj is None or not isinstance(obj, tree.EnumBody):
            log.error('error input for [tree enum body]: [{}]'.format(obj))
            return None

        enum_constants = obj.constants
        if enum_constants is not None:
            for constant in enum_constants:
                self.parse_tree_enum_constant_declaration(constant)

        self.parse_inner_class_body(obj.declarations)

    def parse_tree_enum_constant_declaration(self, obj):
        if obj is None or not isinstance(obj, tree.EnumConstantDeclaration):
            log.error('error input for [tree enum constant declaration]: [{}]'.format(obj))
            return None

        self.add_global_type(obj.name, RoleType.REFERENCE_TYPE)
        self.parse_inner_arguments(obj.arguments)
        self.parse_inner_class_body(obj.body)

    def parse_tree_annotation_method(self, obj):
        if obj is None or not isinstance(obj, tree.AnnotationMethod):
            log.error('error input for [tree annotation method]: [{}]'.format(obj))
            return None

        self.add_global_type(obj.return_type, RoleType.REFERENCE_TYPE)
        self.add_global_method(obj.name)

        self.parse_element_value(obj.default)

    def parse_inner_lambda_method_body(self, obj):
        if obj is None:
            return

        if isinstance(obj, tree.Expression):
            return self.parse_tree_expression(obj)
        else:
            return self.parse_block(obj)

    def parse_inner_nonwildcard_type_arguments(self, obj):
        if obj is None or type(obj) != list:
            return list()

        arg_list = list()
        for argument in obj:
            arg_list.append(self.parse_tree_type_argument(argument))
        return arg_list

    def parse_inner_arguments(self, obj):
        if obj is None or type(obj) != list:
            return []

        exp_list = list()
        for expression in obj:
            exp_list.append(self.parse_expression(expression))
        return exp_list

    def parse_inner_class_body(self, obj):
        if obj is None or type(obj) != list:
            return
        for declaration in obj:
            if isinstance(declaration, tree.Declaration):
                self.parse_tree_declaration(declaration)
            else:
                self.parse_block(declaration)

    def parse_inner_primary(self, obj):
        if obj is None or not isinstance(obj, tree.Primary):
            return

        self.add_global_qualifier(obj.qualifier)

        return merge_dictionaries(self.parse_inner_selectors(obj.selectors), {"qualifier": [obj.qualifier]})

    def parse_inner_selectors(self, obj):
        if obj is None:
            return

        selector_list = []
        for selector in obj:
            if selector is None:
                continue
            elif isinstance(selector, tree.ArraySelector):
                selector_list.append(self.parse_tree_array_selector(selector))
            elif isinstance(selector, tree.Invocation):
                selector_list.append(self.parse_tree_invocation(selector))
            elif isinstance(selector, tree.InnerClassCreator):
                selector_list.append(self.parse_tree_inner_class_creator(selector))
            elif isinstance(selector, tree.SuperMemberReference):
                selector_list.append(self.parse_tree_super_member_reference(selector))

        return merge_dictionaries(selector_list)

    def parse_inner_formal_parameters(self, obj):
        param_list = []
        if obj is None or type(obj) != list:
            return None
        for params in obj:
            param_list.append(self.parse_tree_formal_parameter(params))

        return merge_dictionaries(param_list)

    def parse_inner_type_parameters(self, obj):
        if obj is None or type(obj) != list:
            return None
        param_list = []
        for type_param in obj:
            param = self.parse_tree_type_parameter(type_param)
            param_list.append(param)

        return merge_dictionaries(param_list)

    def parse_inner_annotation_type_body(self, obj):
        if obj is None or type(obj) != list:
            return None
        for element in obj:
            if isinstance(element, tree.Declaration):
                self.parse_tree_declaration(element)
            else:
                log.debug('unknown [parse inner annotation type body]->[for element in body]: {}'.format(element))

    def parse_inner_switch_block_groups(self, obj):
        if obj is None or type(obj) != list:
            return None
        for switch_case in obj:
            self.parse_tree_switch_statement_case(switch_case)

    def parse_element_value(self, obj):
        if obj is None:
            return None
        if isinstance(obj, tree.Annotation):
            return None
        elif isinstance(obj, tree.ElementArrayValue):
            return self.parse_tree_element_array_value(obj)
        elif type(obj) == list:
            return None
        else:
            return self.parse_expressionl(obj)

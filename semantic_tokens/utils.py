from semantic_tokens.adt.nodetype import NodeType


def transform_to_array(*args):
    output_array = []
    for value in args:
        if value is None:
            continue
        elif type(value) == list:
            output_array.extend(value)
        elif type(value) == dict:
            if 'member' in value.keys() and value['member'] is not None:
                output_array.extend(value['member'])
        else:
            output_array.append(value)
    return output_array


def merge_dictionaries(*args):
    output_dictionary = dict()
    for container in args:
        if container is None:
            continue
        elif type(container) == list:
            for element in container:
                output_dictionary = merge_dictionaries(output_dictionary, element)
        elif type(container) != dict:
            continue
        else:
            for key, value in container.items():
                if type(value) != list:
                    value = [value]

                tmp = []
                for element in value:
                    if element is None or (type(element) == str and len(element) == 0):
                        continue
                    tmp.append(element)

                if len(tmp) == 0:
                    continue

                if key in output_dictionary.keys() and type(output_dictionary[key]) == list:
                    output_dictionary[key].extend(value)
                else:
                    output_dictionary[key] = value
    return output_dictionary


def parse_operation_node_type(operation_name):
    if operation_name in ['>', '<', '>=', '<=', 'instanceof', '==', '!=']:
        return NodeType.EXPRESSION_BINARY_LOGIC
    if operation_name in ['/', '*', '%', '+', '-', '&', '^', '|', '>>', '<<', '>>>']:
        return NodeType.EXPRESSION_BINARY_OPERATION
    if operation_name in ['&&', '||']:
        return NodeType.EXPRESSION_BINARY_CONDITION
    return None

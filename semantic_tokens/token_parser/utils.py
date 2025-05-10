import numpy as np

from semantic_tokens.adt.nodetype import NodeType


def unpack_type(obj):
    if obj is None:
        return None
    return obj['type_name']


def unpack_modifier(obj):
    if obj is None:
        return None
    return obj['modifier']


def unpack_member(obj):
    if obj is None or 'member' not in obj.keys():
        return None
    return "-".join(obj['member'])


def rearrange_path(path):
    path_np = np.zeros(int(NodeType.NODE_TYPE_END))
    for index in path:
        path_np[int(index)] += 1
    return path_np


def init_n_gram():
    return np.zeros(int(NodeType.NODE_TYPE_END))


def transform_node(origin_node):
    if origin_node == NodeType.DO_BODY:
        return NodeType.LOOP_BODY
    if origin_node == NodeType.FOR_BODY:
        return NodeType.LOOP_BODY
    if origin_node == NodeType.WHILE_BODY:
        return NodeType.LOOP_BODY
    if origin_node == NodeType.DO_CONDITION:
        return NodeType.LOOP_CONDITION
    if origin_node == NodeType.FOR_CONDITION:
        return NodeType.LOOP_CONDITION
    if origin_node == NodeType.WHILE_CONDITION:
        return NodeType.LOOP_CONDITION
    return origin_node


def parse_inner_modifiers(obj):
    if obj is None or (type(obj) != set and type(obj) != list):
        return None
    modifier_list = []
    for modifier in obj:
        modifier_list.append(modifier)

    return {'modifier': modifier_list}

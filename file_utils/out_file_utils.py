import ast
import re


def extract_out_block_attributes(attributes_string):
    """Extracts attributes from the <block> tag."""
    attributes = {}
    for attr in attributes_string.split(', '):
        key, value = attr.split(":")
        key = key.strip()
        value = value.strip()
        try:
            attributes[key] = int(value)
        except ValueError:
            attributes[key] = value
    return attributes


def extract_vectors_from_out(out_block_str, out_block_data):
    """Extracts vectors from the OUT block string."""
    sections = {
        "variable": r"<variable>\n(.*?)</variable>",
        "field": r"<field>\n(.*?)</field>",
        "method": r"<method>\n(.*?)</method>",
        "keyword": r"<keyword>\n(.*?)</keyword>",
        "type": r"<type>\n(.*?)</type>",
        "basic_type": r"<basic type>\n(.*?)</basic type>",
        "variable_group": r"<variable group>\n(.*?)</variable group>",
        "method_group": r"<method group>\n(.*?)</method group>",
        "relation": r"<relation>\n(.*?)</relation>"
    }

    line_pattern = r"([\w-]*),(\d+): (\[.*?\])"

    for section_name, pattern in sections.items():
        match = re.findall(pattern, out_block_str, re.DOTALL)
        if match:
            if len(match) == 1:
                vectors = []
                for line in match[0].splitlines():
                    parts = re.search(line_pattern, line.strip())
                    if parts:
                        vectors.append(
                            {"name": parts.group(1), "count": int(parts.group(2)), "vector": ast.literal_eval(
                                parts.group(3))})

                out_block_data[section_name] = vectors
            else:
                print("len(match) is wrong = ", len(match))
                exit(0)
        else:
            print("doesn't find match for section_name = ", section_name)
            exit(0)

    return out_block_data


def extract_action_tokens(out_block_data):
    """Extracts action tokens from the parsed OUT block data."""
    action_tokens = list()
    for section in ["method", "type", "variable"]:
        for item in out_block_data.get(section, []):
            action_tokens.append(item["vector"])
    return sorted(action_tokens)


def process_out_file(file_path):
    """Processes a single .out file, extracting block data."""
    try:
        with open(file_path, 'r') as f:
            out_data = f.read()
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return {}

    blocks = re.findall(r'<block (.*?)>(.*?)</block>', out_data, re.DOTALL)
    block_data_all = {}
    for block_attrs_str, block_content in blocks:
        block_data = extract_out_block_attributes(block_attrs_str)
        block_data = extract_vectors_from_out(block_content, block_data)
        block_id = (block_data['filePath'], block_data['startline'])

        block_data['action_tokens'] = extract_action_tokens(block_data)
        block_data_all[block_id] = block_data
    return block_data_all


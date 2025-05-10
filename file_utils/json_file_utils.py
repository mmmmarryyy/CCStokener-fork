import os


def format_group(group_map):
    return {key: {"count": value.count, "vector": value.output()} for key, value in group_map.items()}


def dump_to_json(string, file_path):
    with open(file_path, 'a') as f:
        if os.stat(file_path).st_size > 0:
            f.write(',\n')
        f.write(string)


def finalize_json(file_path):
    with open(file_path, 'r+') as f:
        content = f.read()
        final_json = '{"blocks": [' + content + ']}\n'
        f.seek(0)
        f.write(final_json)
        f.truncate()

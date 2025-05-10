import os
import re


def get_list_of_files_with_suffix(dir_path, suffix=''):
    file_list = []
    paths = os.walk(dir_path)
    for dir_path, dir_names, file_names in paths:
        for file_name in file_names:
            if file_name.endswith(suffix):
                file_list.append(os.path.abspath(os.path.join(dir_path, file_name)))

    return file_list


def get_list_of_subdirectories(dir_path):
    return [os.path.join(dir_path, o) for o in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, o))]


def get_pure_name(file_path):
    file_name = os.path.basename(file_path)
    dot_position = file_name.rfind('.')
    return file_name if dot_position == -1 else file_name[0:dot_position]


def remove_file_if_exists(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)


def get_common_path(path, pattern):
    match = re.search(pattern, path)
    if match:
        return match.group(0)
    else:
        return None

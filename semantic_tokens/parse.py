import codecs
import os
import shutil
import sys
from multiprocessing import Pool, cpu_count

from file_utils import utils
from logger import log
from semantic_tokens import javalang
from semantic_tokens.token_parser.token_parser import TokenParser

sys.setrecursionlimit(50000)


def parse_file(args):
    file_path, output_file_path = args
    file_path = os.path.abspath(file_path)
    utils.remove_file_if_exists(output_file_path)

    tree = None
    try:
        file_content = None
        with codecs.open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            file_content = file.read()

        tokens = javalang.tokenizer.tokenize(file_content)
        parser = javalang.parser.Parser(tokens)
        tree = parser.parse()
    except Exception as e:
        log.warning('exception when parse file: {}, msg: {}'.format(file_path, e))
        tree = None

    try:
        token_parser = TokenParser()
        token_parser.parse(tree, file_path=file_path, output_file_path=output_file_path)
    except Exception as e:
        log.warning('exception when parse tokens: {}, msg: {}'.format(file_path, e))


def parse_directory(input_directory, output_directory):
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)
    os.makedirs(output_directory)

    file_list = utils.get_list_of_files_with_suffix(dir_path=input_directory, suffix='.java')

    log.info('parse dir: {}'.format(input_directory))
    log.info('parse files num: {}'.format(len(file_list)))

    output_file_list = []
    output_file_counter = {}
    for src_file in file_list:
        pure_name = utils.get_pure_name(src_file)
        if pure_name not in output_file_counter:
            output_file_counter[pure_name] = 1
            output_file_list.append((src_file, os.path.join(output_directory, pure_name + '.out')))
        else:
            output_file_counter[pure_name] += 1
            output_file_list.append((src_file, os.path.join(output_directory, pure_name + '__' + str(
                output_file_counter[pure_name]) + '.out')))

    with Pool(processes=cpu_count()) as pool:
        pool.map(parse_file, output_file_list)


def parse_directories(input_directory, output_directory):
    list_of_subdirectories = utils.get_list_of_subdirectories(input_directory)

    if len(list_of_subdirectories) == 0:
        parse_directory(input_directory, output_directory)
    else:
        for subdirectory in list_of_subdirectories:
            parse_directory(subdirectory, os.path.join(output_directory, utils.get_pure_name(subdirectory)))

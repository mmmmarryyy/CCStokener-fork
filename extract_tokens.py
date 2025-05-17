import os
import sys

from semantic_tokens.parse import parse_file, parse_directories
import argparse

from file_utils import utils
from logger import log


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract semantic tokens from code.')
    parser.add_argument('--input_dir', required=True, help='Input directory with source code')
    parser.add_argument('--output_dir', required=True, help='Output directory for tokens')

    args = parser.parse_args()

    input_dir = os.path.realpath(args.input_dir)
    output_dir = args.output_dir

    os.makedirs(output_dir, exist_ok=True)

    if os.path.isfile(input_dir):
        java_file = os.path.abspath(input_dir)

        base = os.path.splitext(os.path.basename(java_file))[0]
        output_file = os.path.join(output_dir, base + ".out")

        try:
            parse_file((java_file, output_file))
        except Exception as e:
            log.error(f"Error while parse java_file {java_file}: {e}")
            sys.exit(1)

    else:
        try:
            parse_directories(input_dir, output_dir)
        except Exception as e:
            log.error(f"Error while parse directory {input_dir}: {e}")
            sys.exit(1)


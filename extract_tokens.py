import os

from semantic_tokens.parse import parse_directories
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract semantic tokens from code.')
    parser.add_argument('--input_dir', required=True, help='Input directory with source code')
    parser.add_argument('--output_dir', required=True, help='Output directory for tokens')
    args = parser.parse_args()

    input_dir = os.path.realpath(args.input_dir)
    output_dir = args.output_dir

    os.makedirs(output_dir, exist_ok=True)
    parse_directories(input_dir, output_dir)

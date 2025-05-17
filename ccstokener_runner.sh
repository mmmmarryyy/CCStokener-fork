#!/bin/bash

if [ "$#" -lt 6 ]; then
    echo "Использование: $0 <входная_директория> <beta> <theta> <eta> --query_file <путь_до_файла> [--bcb_flag] [<директория_отчета>]"
    exit 1
fi

INPUT_DIR="$1"
BETA="$2"
THETA="$3"
ETA="$4"
shift 4

if [ "$1" != "--query_file" ]; then
    echo "Ошибка: после четырёх обязательных параметров должен идти --query_file <файл>"
    exit 1
fi
shift
QUERY_FILE="$1"
shift

BCB_FLAG=""
if [ "$1" == "--bcb_flag" ]; then
    BCB_FLAG="--bcb_flag"
    shift
fi

REPORT_DIR_ARG=""
if [ -n "$1" ]; then
    REPORT_DIR_ARG="--report_dir $1"
fi

start_time=$SECONDS

TOKENS_DIR="tokens_main_$(date +'%Y_%m_%d_%H_%M_%S')"
python3 extract_tokens.py \
    --input_dir "$INPUT_DIR" \
    --output_dir "$TOKENS_DIR"

TOKENS_DIR_query="tokens_query_$(date +'%Y_%m_%d_%H_%M_%S')"
python3 extract_tokens.py \
    --input_dir "$QUERY_FILE" \
    --output_dir "$TOKENS_DIR_query"

python3 code_clone_detection.py \
    --input_tokens_dir "$TOKENS_DIR" \
    --query_tokens_dir "$TOKENS_DIR_query" \
    --beta "$BETA" \
    --theta "$THETA" \
    --eta "$ETA" \
    $BCB_FLAG \
    --query_file "$QUERY_FILE" \
    $REPORT_DIR_ARG

elapsed=$((SECONDS - start_time))
echo "========================================"
echo "Общее время выполнения: $elapsed"
echo "========================================"

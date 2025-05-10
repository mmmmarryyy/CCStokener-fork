#!/bin/bash

if [ "$#" -lt 4 ]; then
    echo "Использование: $0 <входная_директория> <beta> <theta> <eta> [--bcb_flag] [<директория_отчета>]"
    exit 1
fi

INPUT_DIR="$1"
BETA="$2"
THETA="$3"
ETA="$4"
shift 4

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

TOKENS_DIR="tokens_$(date +'%Y_%m_%d_%H_%M_%S')"

python3 extract_tokens.py \
    --input_dir "$INPUT_DIR" \
    --output_dir "$TOKENS_DIR"

python3 code_clone_detection.py \
    --input_tokens_dir "$TOKENS_DIR" \
    $REPORT_DIR_ARG \
    --beta "$BETA" \
    --theta "$THETA" \
    --eta "$ETA" \
    $BCB_FLAG

elapsed=$((SECONDS - start_time))
echo "========================================"
echo "Общее время выполнения: $elapsed"
echo "========================================"

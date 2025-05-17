import math
import multiprocessing
import os
import glob
from datetime import datetime
import numpy as np
import argparse

from file_utils import utils
from file_utils.out_file_utils import process_out_file
from file_utils.utils import get_list_of_files_with_suffix, get_common_path


def countSameActionTokens_idea10(tokens1, tokens2):
    from collections import Counter

    c1 = Counter(tuple(token) for token in tokens1)
    c2 = Counter(tuple(token) for token in tokens2)

    common = c1 & c2

    return sum(common.values())


def cosine(v1, v2):
    """Calculates the cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    magnitude_v1 = math.sqrt(sum(x ** 2 for x in v1))
    magnitude_v2 = math.sqrt(sum(y ** 2 for y in v2))
    if magnitude_v1 == 0 or magnitude_v2 == 0:
        return 0
    return dot_product / (magnitude_v1 * magnitude_v2)


def verifySim_centroid(P: list[list[float]], Q: list[list[float]]) -> float:
    if not P and not Q:
        return 1.0
    if not P:
        P = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
    if not Q:
        Q = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]

    centroid_P = np.mean(np.array(P), axis=0)
    centroid_Q = np.mean(np.array(Q), axis=0)

    return cosine(centroid_P.tolist(), centroid_Q.tolist())


def extract_semantic_vector_collections(data):
    variable_vectors = [item["vector"] for item in data.get("variable_group", [])]
    expression_vectors = [item["vector"] for item in data.get("relation", [])]
    callee_vectors = [item["vector"] for item in data.get("method_group", [])]
    return variable_vectors, expression_vectors, callee_vectors


def binary_search_left(sorted_list, lower_bound):
    left, right = 0, len(sorted_list)
    while left < right:
        mid = (left + right) // 2
        if sorted_list[mid] < lower_bound:
            left = mid + 1
        else:
            right = mid
    return left


def binary_search_right(sorted_list, upper_bound):
    left, right = 0, len(sorted_list)
    while left < right:
        mid = (left + right) // 2
        if sorted_list[mid] <= upper_bound:
            left = mid + 1
        else:
            right = mid
    return left


def clone_detection_worker(all_block_data, sorted_blocks, candidate_token_nums, sorted_query_pairs,
                           beta, theta, eta, token_count_differ, query_indices,
                           thread_num, subdirectory, report_dir, bcb_flag):
    print(f"[Thread {thread_num}] Обрабатываем {len(query_indices)} query-блоков (всего query-блоков = {len(sorted_query_pairs)})")
    candidate_clones = set()

    output_filename = os.path.join(report_dir, f"clone_pairs_{subdirectory}_thread_{thread_num}.txt")
    file = open(output_filename, 'w+')
    file.close()

    for idx_in_list, index in enumerate(query_indices):
        if idx_in_list % 10 == 0:
            print(f"[{datetime.now()}] [Thread {thread_num}] Обработано {idx_in_list}/{len(query_indices)} query-блоков.")
        
        (file_path, start_line), block_data = sorted_query_pairs[index]
        current_token_number = block_data['totalTokenNum']
        if current_token_number <= 15:
            continue

        inner_token_count_differ = max(token_count_differ, 0.5 * current_token_number)
        lower_bound = current_token_number - inner_token_count_differ
        if lower_bound < 0:
            lower_bound = 0
        upper_bound = current_token_number + inner_token_count_differ

        left_bound = binary_search_left(candidate_token_nums, lower_bound)
        right_bound = binary_search_right(candidate_token_nums, upper_bound)

        filtered_clones = []
        for i in range(left_bound, right_bound):
            (candidate_file_path, candidate_start_line) = sorted_blocks[i][0]
            if (file_path, start_line) == (candidate_file_path, candidate_start_line):
                continue

            candidate_block_data = all_block_data[(candidate_file_path, candidate_start_line)]

            sat = countSameActionTokens_idea10(block_data['action_tokens'], candidate_block_data['action_tokens'])
            ato = sat / min(len(block_data['action_tokens']), len(candidate_block_data['action_tokens']))
            tr = (min(block_data['totalTokenNum'], candidate_block_data['totalTokenNum']) /
                  max(block_data['totalTokenNum'], candidate_block_data['totalTokenNum']))
            if ato >= beta and tr >= theta:
                filtered_clones.append((candidate_file_path, candidate_start_line))

        VT_j, ET_j, CT_j = extract_semantic_vector_collections(block_data)
        for candidate_block_k_id in filtered_clones:
            block_k = all_block_data[candidate_block_k_id]
            pair = ((file_path, start_line), (block_k['filePath'], block_k['startline']))
            if pair in candidate_clones or (pair[1], pair[0]) in candidate_clones:
                continue

            VT_k, ET_k, CT_k = extract_semantic_vector_collections(block_k)
            simVT = verifySim_centroid(VT_j, VT_k)
            simET = verifySim_centroid(ET_j, ET_k)
            simCT = verifySim_centroid(CT_j, CT_k)
            if (simVT + simET + simCT) >= eta * 3:
                candidate_clones.add(pair)

    with open(output_filename, 'a+') as fileOut:
        for ((left_path, left_start_line), (right_path, right_start_line)) in candidate_clones:
            if bcb_flag:
                left_parts = left_path.split(os.sep)
                right_parts = right_path.split(os.sep)
                fileOut.write(f"{left_parts[-2]},{left_parts[-1]},{left_start_line},{all_block_data[(left_path, left_start_line)]['endline']},{right_parts[-2]},{right_parts[-1]},{right_start_line},{all_block_data[(right_path, right_start_line)]['endline']}\n")
            else:
                fileOut.write(f"{left_path},{left_start_line},{all_block_data[(left_path, left_start_line)]['endline']},{right_path},{right_start_line},{all_block_data[(right_path, right_start_line)]['endline']}\n")


def clone_detection(input_tokens_dir, query_tokens_dir,
                    beta, theta, eta, token_count_differ,
                    report_dir, bcb_flag, query_file_abs):
    all_block_data = {}
    for out_file in glob.glob(os.path.join(input_tokens_dir, "*.out")):
        all_block_data.update(process_out_file(out_file))
    
    print(f"[{datetime.now()}] Загружено {len(all_block_data)} candidate-блоков")

    all_queries = {}
    for out_file in glob.glob(os.path.join(query_tokens_dir, "*.out")):
        all_queries.update(process_out_file(out_file))

    all_block_data.update(all_queries)
    print(f"[{datetime.now()}] Всего candidate-блоков после объединения: {len(all_block_data)}")

    sorted_blocks = sorted(all_block_data.items(), key=lambda item: item[1]['totalTokenNum'])
    candidate_token_nums = [block_data['totalTokenNum'] for (_, block_data) in sorted_blocks]

    sorted_query_pairs = sorted(all_queries.items(), key=lambda kv: kv[1]['totalTokenNum'])
    if not sorted_query_pairs:
        print(f"[{datetime.now()}] Ошибка: не найдено ни одного блока для query_файла.")
        return
    print(f"[{datetime.now()}] Query-блоков (из файла {query_file_abs}): {len(sorted_query_pairs)}")

    query_indices = []
    for idx, _ in enumerate(sorted_query_pairs):
        query_indices.append(idx)

    num_threads = min(4, multiprocessing.cpu_count())
    print(f"[{datetime.now()}] have {num_threads} threads")
    chunk_size = len(sorted_blocks) // num_threads
    print(f"chunk_size = {chunk_size}")

    chunk_size = math.ceil(len(query_indices) / num_threads)
    with multiprocessing.Pool(processes=num_threads) as pool:
        results = []
        for i in range(num_threads):
            start_index = i * chunk_size
            end_index = min((i + 1) * chunk_size, len(query_indices))
            sub_query_inds = query_indices[start_index:end_index]
            if not sub_query_inds:
                continue
            results.append(pool.apply_async(clone_detection_worker, (
                all_block_data,
                sorted_blocks,
                candidate_token_nums,
                sorted_query_pairs,
                beta, theta, eta,
                token_count_differ,
                sub_query_inds,
                i,
                os.path.basename(input_tokens_dir),
                report_dir,
                bcb_flag
            )))

        for r in results:
            r.get()


def parse_directory(input_directory, query_directory, report_dir, beta, theta, eta, bcb_flag, query_file_abs):
    print(f"[{datetime.now()}] begin of parse_directories")
    list_of_subdirectories = utils.get_list_of_subdirectories(input_directory)

    if bcb_flag:
        list_of_subdirectories = sorted(list_of_subdirectories, key=lambda x: int(os.path.basename(x)))

    if len(list_of_subdirectories) == 0:
        clone_detection(input_directory, query_directory, beta, theta, eta, token_count_differ=50,
                        report_dir=report_dir, bcb_flag=bcb_flag, query_file_abs=query_file_abs)
    else:
        for subdirectory in list_of_subdirectories:
            parse_directory(subdirectory, query_directory, report_dir, beta, theta, eta, bcb_flag, query_file_abs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Detect code clones from extracted tokens.')
    parser.add_argument('--input_tokens_dir', required=True, help='Directory with extracted tokens')
    parser.add_argument('--query_tokens_dir', required=True, help='Directory with extracted tokens from query-file')
    parser.add_argument('--report_dir', help='Output directory for the report (optional)')
    parser.add_argument('--beta', type=float, required=True, help='Threshold for action-token overlap (beta)')
    parser.add_argument('--theta', type=float, required=True, help='Threshold for token-count ratio (theta)')
    parser.add_argument('--eta', type=float, required=True, help='Threshold for semantic tokens similarity (eta)')
    parser.add_argument('--bcb_flag', action='store_true', help='Use BCB output format if set')
    parser.add_argument('--query_file', required=True, help='Path to file for which we find clones')

    args = parser.parse_args()

    start_timestamp = datetime.now()

    beta = args.beta
    theta = args.theta
    eta = args.eta
    bcb_flag = args.bcb_flag
    query_file_abs = os.path.abspath(args.query_file)

    if args.report_dir:
        report_dir = args.report_dir
    else:
        report_dir = f"report_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"

    os.makedirs(report_dir, exist_ok=True)
    common_result_path = os.path.join(report_dir, "result.txt")
    print(f"[{datetime.now()}] Результаты будут лежать в {common_result_path}")

    parse_directory(
        args.input_tokens_dir, 
        args.query_tokens_dir,
        report_dir,
        beta,
        theta,
        eta,
        bcb_flag,
        query_file_abs
    )

    all_report_files = glob.glob(os.path.join(report_dir, "clone_pairs_*.txt"))

    with open(common_result_path, 'w') as common_file:
        for report_file in all_report_files:
            with open(report_file, 'r') as f:
                common_file.write(f.read())
                common_file.write("\n")

    print(f"[{datetime.now()}] Результаты объединены в {common_result_path}")
    print(f"[{datetime.now()}] Computation takes {datetime.now() - start_timestamp}")


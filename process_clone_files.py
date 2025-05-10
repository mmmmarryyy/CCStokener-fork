import os
from datetime import datetime

def process_clone_files(directory_path):
    unique_clones = set()
    print(f"inside process_clone_files for {directory_path}")
    print(os.listdir(directory_path))
    
    for filename in os.listdir(directory_path):
        if filename.startswith("clonepairs") and filename.endswith(".txt"):
            print(filename)
            file_path = os.path.join(directory_path, filename)
            with open(file_path, 'r') as f:
                for i, line in enumerate(f):
                    if i % 50000 == 0:
                       print(f"{i}")

                    parts = line.strip().split(',')
                    if len(parts) != 6:
                        print(f"parts = {parts}")
                        continue

                    cf1_path, cf1_start, cf1_end, cf2_path, cf2_start, cf2_end = parts

                    _, _, _, _, cf1_dir, cf1_subdir, cf1_filename = cf1_path.split('/')
                    # print(cf1_dir, cf1_subdir, cf1_filename)
                    _, _, _, _, cf2_dir, cf2_subdir, cf2_filename = cf2_path.split('/')
                    # print(cf2_dir, cf2_subdir, cf2_filename)

                    clone1 = (cf1_subdir, cf1_filename, int(cf1_start), int(cf1_end))
                    clone2 = (cf2_subdir, cf2_filename, int(cf2_start), int(cf2_end))

                    sorted_clone_pair = tuple(sorted([clone1, clone2]))

                    unique_clones.add(sorted_clone_pair)

    return unique_clones


def write_result_file(unique_clones, output_path="result.txt"):
    with open(output_path, 'w') as f:
        for clone_pair in unique_clones:
            clone1, clone2 = clone_pair
            f.write(f"{clone1[0]},{clone1[1]},{clone1[2]},{clone1[3]},{clone2[0]},{clone2[1]},{clone2[2]},{clone2[3]}\n")


if __name__ == "__main__":
    directory = ("original_results/results")
    if os.path.isdir(directory):
        clones = process_clone_files(directory)
        file_name = f"original_result_{datetime.now()}.txt"
        write_result_file(clones, file_name)
        print(f"Результат записан в файл {file_name}")
    else:
        print("Указанный путь не является директорией.")

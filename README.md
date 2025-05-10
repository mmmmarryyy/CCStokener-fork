# CCStokener

My implementation of CCStokener algorithm ([article](https://www.sciencedirect.com/science/article/abs/pii/S0164121223000134))

## Использование

### 1. Извлечение токенов
```bash
python3 extract_tokens.py \
  --input_dir <path> \
  --output_dir <path>
```

Параметры:
- input_dir: Директория с исходным кодом
- output_dir: Директория для сохранения токенов

### 2. Поиск клонов кода

```bash
python3 code_clone_detection.py \
  --input_tokens_dir <path> \
  --beta <float> \
  --theta <float> \
  --eta <float> \
  [--bcb_flag] \
  [--report_dir <path>]
```

Параметры:
- input_tokens_dir: Директория с токенами (результат работы extract_tokens.py)
- beta: Пороговое значение для перекрытия action-token
- theta: Пороговое значение для отношения числа токенов 
- eta: Пороговое значение для близости семантических токенов
- bcb_flag (опционально): Использовать формат BCB в отчете
- report_dir (опционально): Директория для отчета и результатов

### 3. Запуск всего пайплайна

```bash
./ccstokener_runner.sh <input_dir> <beta> <theta> <eta> [--bcb_flag] [<report_dir>]
```

Пример:
```bash
./ccstokener_runner.sh ./dataset/java_samples 0.5 0.3 0.8
./ccstokener_runner.sh ./dataset/java_samples 0.6 0.4 0.7 --bcb_flag my_custom_report
```


```bash
mkdir -p cloc_results

# Пройти по всем подпапкам внутри bcb_reduced/
for dir in ../dataset/IJaDataset/bcb_reduced/*/; do
    # Извлечь имя подпапки (без пути)
    dir_name=$(basename "$dir")
    
    echo "Отчёт для $dir_name:"
    cloc "$dir" --skip-uniqueness --report-file="cloc_results/${dir_name}_report.txt"
    echo "-------------------"
done

# Суммировать все отчёты
cloc --sum-reports cloc_results/*.txt --out=cloc_results/total_report.txt
```

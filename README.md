# CCStokener

Реализация алгоритма CCStokener ([article](https://www.sciencedirect.com/science/article/abs/pii/S0164121223000134)), адаптированная под задачу code search

## Использование

### 1. Извлечение токенов
```bash
python3 extract_tokens.py \
  --input_dir <path> \
  --output_dir <path>
```

Параметры:
- input_dir: Директория или файл с исходным кодом
- output_dir: Директория для сохранения токенов

### 2. Поиск клонов кода

```bash
python3 code_clone_detection.py \
  --input_tokens_dir <path> \
  --query_tokens_dir <path> \
  --query_file <absolute_path_to_query.java> \
  --beta <float> \
  --theta <float> \
  --eta <float> \
  [--bcb_flag] \
  [--report_dir <path>]
```

Параметры:
- input_tokens_dir: Директория с токенами (результат работы extract_tokens.py)
- query_tokens_dir: Директория с токенами query_file
- query_file — абсолютный путь до .java-файла, для которого нужно найти все клоны
- beta: Пороговое значение для перекрытия action-token
- theta: Пороговое значение для отношения числа токенов 
- eta: Пороговое значение для близости семантических токенов
- bcb_flag (опционально): Использовать формат BCB в отчете
- report_dir (опционально): Директория для отчета и результатов

### 3. Запуск всего пайплайна

```bash
./ccstokener_runner.sh <input_dir> <beta> <theta> <eta> --query_file <path_to_query.java> [--bcb_flag] [<report_dir>]
```

Пример:
```bash
./ccstokener_runner.sh ./dataset/java_samples 0.5 0.3 0.8 --query_file ./dataset/java_samples/example/Foo.java
./ccstokener_runner.sh ./dataset/java_samples 0.6 0.4 0.7 --query_file ./dataset/java_samples/example/Foo.java --bcb_flag my_custom_report
```

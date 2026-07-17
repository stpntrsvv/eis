# Архитектура

Архитектура намеренно разделена на четыре понятные части: чтение данных, вычислительное ядро, пользовательские интерфейсы и экспорт.

## Карта модулей

```mermaid
flowchart TD
    CLI[eis_cli.py] --> IO[eis_io.py]
    GUI[eis_qt.py] --> IO
    CLI --> Pipeline[eis_pipeline.py]
    Pipeline --> IO
    Pipeline --> Core[eis_core.py]
    GUI --> Core[eis_core.py]
    CLI --> Core
    IO --> Dataset[EisDataset]
    Core --> FitResult[FitResult]
    GUI --> Export[CSV / XLSX / TXT / PNG]
    GUI --> PresetStore[Local pro_presets.json]
```

## Ответственность файлов

| Файл | Ответственность |
|---|---|
| `eis_core.py` | Семейства схем, начальные значения, границы, фитинг, AIC/BIC и диагностические флаги |
| `eis_io.py` | Чтение текстовых файлов и BioLogic, поиск каналов, очистка набора данных |
| `eis_qt.py` | Основной настольный интерфейс, фоновая обработка, графики, экспорт и локализация |
| `eis_cli.py` | Интерфейс командной строки для воспроизводимых запусков и диагностики |
| `eis_pipeline.py` | Независимый конвейер анализа, пакетная обработка и сериализуемый `AnalysisResult` |
| `eis_utils.py` | Слой совместимости со старыми импортами |
| `eis_app.py` | Устаревшая точка запуска, перенаправляющая в `eis_qt.py` |
| `cycling.py` | Старый экспериментальный файл, не относящийся к действующей архитектуре EIS |

## Основные типы данных

```mermaid
classDiagram
    class EisDataset {
        file_path
        frequencies
        z
        source_format
        columns
        metadata
    }

    class DatasetScale {
        r0
        r_transfer
        capacitance
    }

    class FitResult {
        circuit_string
        success
        model
        mean_fit_error
        max_param_error
        rss_weighted
        aic
        bic
        n_params
        status
        flags
        error_message
    }

    class AnalysisCase {
        file_path
        frequencies
        z_experimental
        scale
        source_format
        metadata
        selected_channel
        results
        best_result
    }

    EisDataset --> AnalysisCase
    DatasetScale --> AnalysisCase
    FitResult --> AnalysisCase
```

## Фоновая работа GUI

Фитинг выполняется в рабочем потоке Qt. Поэтому окно продолжает отвечать во время обработки серии файлов, а пользователь видит ход выполнения и может запросить отмену.

```mermaid
sequenceDiagram
    participant User
    participant GUI as EisQtApp
    participant Worker as FitWorker/QThread
    participant Core as eis_core

    User->>GUI: Run auto-fit / selected / manual
    GUI->>Worker: start(cases, circuits, overrides)
    loop per file
        Worker->>Core: fit_circuits(...)
        Core-->>Worker: list[FitResult]
        Worker->>Core: choose_best_result(...)
        Worker-->>GUI: finished_case(index, results, best)
        Worker-->>GUI: progress(completed, total)
    end
    Worker-->>GUI: finished(cancelled)
```

## Локальные данные пользователя

Пользовательские пресеты расширенного режима не хранятся в репозитории.

Основной путь в Windows:

```text
%APPDATA%\EIS Solver\pro_presets.json
```

Запасной путь:

```text
.eis_solver_user/pro_presets.json
```

Запасная папка исключена из Git.

# Frequency-window identifiability gate

Дата: 2026-07-17.

## Проблема

Стратифицированный interval benchmark показал, что узкий условный интервал
не гарантирует идентифицируемость. У слабого CPE характерная частота лежит
ниже измеренного диапазона, но covariance и bootstrap всё равно часто
возвращают `identified`.

## Замороженное правило

Benchmark-only gate не меняет fit и доверительный интервал. Он проверяет две
дополнительные оси:

1. Fit повторяется после удаления 10% и 20% точек отдельно с низкочастотного
   и высокочастотного края. Параметр устойчив, если все четыре fit допустимы
   и максимальный fold-change не превышает `1,5`.
2. Для связки `R-CPE` и элемента `Wo` вычисляется характерная частота. Она
   должна лежать внутри реально измеренного диапазона.

Узкий интервал получает `identified` только при прохождении обеих проверок.
Иначе он понижается до `weak`; `unbounded` всегда сохраняется.

## Результат

Использованы те же 20 заранее замороженных сценариев и те же interval rows.
Завершены `16/20`; четыре отказа остаются weak-`Wo`.

| Группа и метод | Identified до | Identified после | Retention |
|---|---:|---:|---:|
| CPE observable, covariance | 15 | 15 | 100% |
| CPE observable, residual bootstrap | 15 | 15 | 100% |
| CPE observable, parametric bootstrap | 15 | 15 | 100% |
| CPE weak, covariance | 14 | 0 | 0% |
| CPE weak, residual bootstrap | 14 | 0 | 0% |
| CPE weak, parametric bootstrap | 13 | 0 | 0% |
| Wo observable, covariance | 10 | 10 | 100% |
| Wo observable, parametric bootstrap | 2 | 2 | 100% |

Residual bootstrap уже считал все наблюдаемые `Wo` слабыми, поэтому
сохранять там было нечего. Единственный прошедший weak-`Wo` также не получил
ни одного `identified`.

Gate полностью устранил заранее известный false-identified класс weak CPE,
не потеряв identified-параметры observable-групп. Однако coverage
сохранившихся residual-bootstrap интервалов observable CPE равно только
`80%`; сам интервал всё ещё не является калиброванным nominal-95%.

## Решение

- frequency-window diagnostics и characteristic support реализованы;
- правило остаётся benchmark-only;
- в основной decision/JSON-контракт оно пока не переносится;
- `calibrated=true` по-прежнему запрещён;
- перед production нужны новые seeds, несколько уровней шума и положения
  характерной частоты около обоих краёв диапазона;
- profile likelihood остаётся отдельным незакрытым провалом.

## Воспроизведение

```powershell
.\.venv\Scripts\python.exe eis_window_benchmark.py `
  validation_data\artifacts\parameter_interval_stratified\truth.jsonl `
  validation_data\artifacts\parameter_interval_stratified\results.jsonl `
  --output validation_data\artifacts\parameter_interval_stratified\window_results.jsonl `
  --trim-fraction 0.10 --trim-fraction 0.20 `
  --max-fold-change 1.5 --restarts 3 `
  --max-evaluations 2000 --seed 20260717
```

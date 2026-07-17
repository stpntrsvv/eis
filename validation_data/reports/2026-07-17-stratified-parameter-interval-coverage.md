# Стратифицированная калибровка интервалов параметров

Дата: 2026-07-17.

## Дизайн

Корпус заранее разделён на четыре группы: наблюдаемый CPE, слабый CPE,
наблюдаемый `Wo` и слабый `Wo`. Использованы 61 частота от `100 кГц` до
`10 мГц`, относительный комплексный Gaussian noise `1%` и пять повторов на
группу. Для каждого допустимого fit выполнено 20 residual и 20 parametric
bootstrap-повторов. Profile likelihood посчитан на одном заранее отмеченном
представителе каждой группы.

Параметрический bootstrap генерирует независимый комплексный шум вокруг
fitted spectrum. `BAD`-минимум теперь считается отказом benchmark, а не
источником интервала. Fit выполнялся с тремя стартами.

## Результат

Завершены `16/20` спектров. Все четыре отказа находятся в слабом `Wo`:
`4/5` fit честно остались `BAD`. Coverage для этой группы нельзя оценивать
по единственному прошедшему fit.

| Метод | Все интервалы | Coverage |
|---|---:|---:|
| covariance | 82 | 92,7% |
| residual bootstrap | 82 | 90,2% |
| parametric bootstrap | 82 | 86,6% |
| representative profile | 8 | 37,5% |

Для заранее заданных целевых параметров:

| Группа | Covariance | Residual bootstrap | Parametric bootstrap |
|---|---:|---:|---:|
| CPE observable | 13/15 | 12/15 | 14/15 |
| CPE weak | 14/15 | 11/15 | 9/15 |
| Wo observable | 10/10 | 10/10 | 10/10 |
| Wo weak | 1/2 | 1/2 | 2/2 |

Высокое coverage само по себе не доказывает идентифицируемость. Residual
bootstrap пометил все 10 наблюдаемых `Wo`-интервалов как `weak`, parametric
bootstrap — 8 из 10. Слабый CPE, напротив, почти всегда ошибочно помечен
`identified`: эвристика ширины не видит bias и конфундацию за пределом
частотного окна. Profile likelihood накрыл только `3/8` параметров.

## Решение

- parametric bootstrap остаётся benchmark-инструментом;
- multi-start обязателен перед оценкой интервалов сложной схемы;
- `BAD` является корректным отказом;
- `identified/weak/unbounded` не прошли проверку селективности;
- `calibrated=true` и эти статусы не переносятся в production contract;
- `confidence` остаётся локальной fit-ошибкой, не 95%-интервалом.

Следующий шаг — проверять чувствительность к частотному окну и bias:
удерживать/расширять края диапазона и требовать стабильности оценки. Profile
likelihood требует log-параметризации положительных параметров и адаптивного
расширения сетки до пересечения порога.

## Воспроизведение

```powershell
.\.venv\Scripts\python.exe eis_interval_corpus.py `
  validation_data\artifacts\parameter_interval_stratified `
  --replicates 5 --noise-fraction 0.01 --seed 20260717

.\.venv\Scripts\python.exe eis_interval_benchmark.py `
  validation_data\artifacts\parameter_interval_stratified\truth.jsonl `
  --output validation_data\artifacts\parameter_interval_stratified\results.jsonl `
  --bootstrap-samples 20 --parametric-bootstrap-samples 20 `
  --profile-parameter R1 --profile-parameter CPE0_1 `
  --profile-parameter Wo0_0 --profile-parameter Wo0_1 `
  --profile-grid-points 41 --profile-representatives-only `
  --seed 20260717 --restarts 3 --max-evaluations 2000
```

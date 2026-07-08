import numpy as np
import re


def load_any_eis_file(file_path):
    """
    Универсальный загрузчик: ищет первые 3 числовые колонки в файле.
    Сам корректирует знак мнимой части, если она записана как отрицательная.
    """
    data_lines = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Регулярка ищет числа, включая экспоненциальную форму (1.23e-4)
            matches = re.findall(r'[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|\b[-+]?\d+\b', line)
            if len(matches) >= 3:
                data_lines.append([float(x) for x in matches[:3]])

    if not data_lines:
        raise ValueError(f"❌ Ошибка: Не удалось найти 3 колонки с числами в файле {file_path}")

    data = np.array(data_lines)
    frequencies = data[:, 0]
    re_parts = data[:, 1]

    # В электрохимии принято строить -Im(Z) как положительную величину.
    # Если в файле Im уже идет со знаком минус, берем как есть, иначе инвертируем.
    mean_im = np.mean(data[:, 2])
    im_parts = data[:, 2] if mean_im < 0 else -data[:, 2]

    # Возвращаем частоту и комплексный импеданс Z_experimental
    Z_experimental = re_parts + 1j * im_parts
    return frequencies, Z_experimental


def estimate_dataset_scale(frequencies, Z_experimental):
    """
    Быстро анализирует геометрию годографа и выдает базовые физические оценки
    для R0, R_transfer и емкости C, чтобы guess адаптировался под новые данные.
    """
    re_parts = Z_experimental.real
    im_parts = -Z_experimental.imag

    R0_est = float(np.min(re_parts))
    R_max_est = float(np.max(re_parts))
    R1_est = float(R_max_est - R0_est) if R_max_est > R0_est else 100.0

    # Ищем частоту на вершине самой высокой дуги
    idx_mid = np.argmax(np.abs(im_parts))
    f_mid = frequencies[idx_mid]
    C_est = float(1.0 / (2 * np.pi * f_mid * R1_est)) if R1_est > 0 else 1e-4

    return R0_est, R1_est, C_est
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def parse_battery_log(file_path):
    data = []
    current_cycle = None
    current_step = None
    inside_data = False

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Ловим маркеры цикла и шага
            if line.startswith('Cycle'):
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    current_cycle = int(parts[1])
                continue

            # Защита от строчки "Physical Cycle 1" и прочего мусора с буквами
            if 'Physical' in line or 'Cycle' in line:
                continue

            if line.startswith('Step'):
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    current_step = int(parts[1])
                inside_data = False
                continue

            # Пропускаем шапку таблицы
            if 'Time (s)' in line:
                inside_data = True
                continue

            # Если мы внутри блока данных, парсим цифры с защитой от ошибок
            if inside_data:
                try:
                    row = [float(x) for x in line.replace(',', ' ').split() if x]
                    if len(row) == 3:
                        data.append([current_cycle, current_step, row[0], row[1], row[2]])
                except ValueError:
                    # Если вдруг проскочила какая-то строка с текстом, просто игнорим её
                    continue

    # ВОТ ЭТОТ КУСОК ПРОПАЛ: Собираем и возвращаем DataFrame
    df = pd.DataFrame(data, columns=['Cycle', 'Step', 'Time_s', 'Voltage_V', 'Current_A'])
    return df


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Предполагаем, что функция parse_battery_log определена выше
file_path = 'data_cycling.txt'
df = parse_battery_log(file_path)

if df.empty:
    print("Ошибка: DataFrame пустой!")
else:
    # 1. Сквозное время
    df['Local_Delta_s'] = df['Time_s'].diff().fillna(0)
    df.loc[df['Local_Delta_s'] < 0, 'Local_Delta_s'] = 0
    df['Continuous_Time_h'] = df['Local_Delta_s'].cumsum() / 3600.0

    # ФИЛЬТРАЦИЯ ДАННЫХ (Только CV режим)
    df_cv = df[df['Step'].isin([2, 4])].copy()

    # --- РАСЧЕТ СМОДЕЛИРОВАННОГО OCV ---
    R_internal = 850  # Задаем среднее сопротивление в Омах
    df_cv['OCV_predicted'] = df_cv['Voltage_V'] - (df_cv['Current_A'] * R_internal)

    # --- РАСЧЕТ КУЛОНОВСКОЙ ЭФФЕКТИВНОСТИ ---
    df_cv['Delta_Time_h'] = df_cv['Local_Delta_s'] / 3600.0
    df_cv['Capacity_mAh'] = abs(df_cv['Current_A'] * 1000.0 * df_cv['Delta_Time_h'])

    step_capacities = df_cv.groupby(['Cycle', 'Step'])['Capacity_mAh'].sum().unstack(fill_value=0)
    q_dis = step_capacities.get(2, 0)
    q_ch = step_capacities.get(4, 0)
    ce = (q_dis / q_ch) * 100.0
    ce = ce.replace([np.inf, -np.inf], np.nan).fillna(0)

    # --- СТРОИМ МАТРИЦУ ГРАФИКОВ 2х2 ---
    fig, axs = plt.subplots(2, 2, figsize=(15, 10))

    # Разворачиваем оси в плоский список для удобства обращения: [0, 0], [0, 1] -> [0, 1, 2, 3]
    ax_volt, ax_curr, ax_ocv, ax_ce = axs.ravel()

    # 1. График: Потенциал со стенда
    ax_volt.plot(df_cv['Continuous_Time_h'], df_cv['Voltage_V'], color='darkviolet', lw=2)
    ax_volt.axhline(0, color='gray', linestyle=':', lw=1.2)  # Линия нуля
    ax_volt.set_xlabel('Общее время эксперимента (ч)', fontsize=10)
    ax_volt.set_ylabel('Потенциал (В)', fontsize=10)
    ax_volt.set_title('1. Измеренный потенциал на клеммах', fontsize=11, fontweight='bold')
    ax_volt.grid(True, linestyle='--', alpha=0.3)

    # 2. График: Динамика тока
    ax_curr.plot(df_cv['Continuous_Time_h'], df_cv['Current_A'] * 1000.0, color='teal', lw=1.5)
    ax_curr.axhline(0, color='gray', linestyle=':', lw=1.2)  # Линия нуля
    ax_curr.set_xlabel('Общее время эксперимента (ч)', fontsize=10)
    ax_curr.set_ylabel('Ток (мА)', fontsize=10)
    ax_curr.set_title('2. Динамика тока (Только CV)', fontsize=11, fontweight='bold')
    ax_curr.grid(True, linestyle='--', alpha=0.3)

    # 3. График: Расчетный прогноз OCV
    ax_ocv.plot(df_cv['Continuous_Time_h'], df_cv['OCV_predicted'], color='firebrick', lw=1.5)
    ax_ocv.axhline(0, color='gray', linestyle=':', lw=1.2)  # Линия нуля
    ax_ocv.set_xlabel('Общее время эксперимента (ч)', fontsize=10)
    ax_ocv.set_ylabel('Потенциал OCV (В)', fontsize=10)
    ax_ocv.set_title(f'3. Модель истинного OCV (R = {R_internal} Ом)', fontsize=11, fontweight='bold')
    ax_ocv.grid(True, linestyle='--', alpha=0.3)

    # 4. График: Кулоновская эффективность
    cycles = ce.index
    ax_ce.bar(cycles, ce.values, color='royalblue', alpha=0.7, edgecolor='black', width=0.4)
    ax_ce.plot(cycles, ce.values, 'o--', color='black', lw=1.5)
    ax_ce.set_xlabel('Номер цикла', fontsize=10)
    ax_ce.set_ylabel('Эффективность (%)', fontsize=10)
    ax_ce.set_title('4. Эволюция кулоновской эффективности', fontsize=11, fontweight='bold')
    ax_ce.set_xticks(cycles)
    ax_ce.grid(True, linestyle='--', alpha=0.5)
    ax_ce.set_ylim(0, 110)

    plt.tight_layout()
    plt.show()
import numpy as np
import matplotlib.pyplot as plt
from impedance.models.circuits import CustomCircuit
import warnings

# ИМПОРТИРУЕМ НАШ НАШ ПАРСЕР
from eis_utils import load_any_eis_file, estimate_dataset_scale

warnings.filterwarnings('ignore')

# === ПРОСТОУКАЖИ ПУТЬ К НОВОМУ ФАЙЛУ ТУТ ===
# Скрипт сам всё распарсит, выровняет знаки и подстроит guess
FILE_PATH = "double very good eis.txt"

try:
    frequencies, Z_experimental = load_any_eis_file(FILE_PATH)
    R0_est, R1_est, C_est = estimate_dataset_scale(frequencies, Z_experimental)
    print(f"📊 Датасет успешно загружен!")
    print(f"-> Автооценка: R0 ≈ {R0_est:.1f} Ом, R_transfer ≈ {R1_est:.1f} Ом, C ≈ {C_est:.2e} Ф\n")
except Exception as e:
    print(str(e))
    exit()

# === УНИВЕРСАЛЬНЫЙ АВТОПАРСЕР ГРАНИЦ С УЧЕТОМ МАСШТАБА ДАННЫХ ===
import re


def build_bounds_and_guess(circuit_string):
    clean_str = re.sub(r'[p()\s,]', '-', circuit_string)
    elements = [e for e in clean_str.split('-') if e]

    low_b, high_b, initial_guess = [], [], []
    r_idx, cpe_idx, c_idx, w_idx = 0, 0, 0, 0

    for el in elements:
        el_type = re.match(r'([a-zA-Z]+)', el).group(1)

        if el_type == 'R':
            r_val = R0_est if r_idx == 0 else R1_est / max(1, r_idx)
            initial_guess.append(r_val)
            low_b.append(1e-3);
            high_b.append(1e8)
            r_idx += 1
        elif el_type == 'CPE':
            q_val = C_est * (10 ** cpe_idx)
            initial_guess.extend([q_val, 0.75])
            low_b.extend([1e-10, 0.501])  # alpha > 0.5
            high_b.extend([10.0, 1.0])
            cpe_idx += 1
        elif el_type == 'C':
            initial_guess.append(C_est)
            low_b.append(1e-10);
            high_b.append(10.0)
            c_idx += 1
        elif el_type in ['Wo', 'Ws']:
            initial_guess.extend([R1_est * 1.5, 5.0])
            low_b.extend([1e-2, 1e-3]);
            high_b.extend([1e7, 1e5])
            w_idx += 1
        elif el_type == 'W':
            initial_guess.append(R1_est * 0.5)
            low_b.append(1e-2);
            high_b.append(1e7)
            w_idx += 1

    return low_b, high_b, initial_guess


# Наш расширенный пул под любые задачи
universal_circuits = [
    'R0-p(R1,C1)', 'R0-p(R1,CPE0)',
    'R0-p(R1,CPE0)-W0', 'R0-p(R1,CPE0)-Wo0', 'R0-p(R1,CPE0)-Ws0',
    'R0-p(R1-W0,CPE0)', 'R0-p(R1-Wo0,CPE0)', 'R0-p(R1-Ws0,CPE0)',
    'R0-p(R1,CPE0)-p(R2,CPE1)', 'R0-p(R1,CPE0)-p(R2,CPE1)-W0',
    'R0-p(R1,CPE0)-p(R2,CPE1)-Wo0', 'R0-p(R1,CPE0)-p(R2,CPE1)-Ws0',
    'R0-p(R1-p(R2,CPE1),CPE0)', 'R0-p(R1-p(R2,CPE1)-W0,CPE0)'
]

results = []
print("=== ЗАПУСК СЕЛЕКТОРА СХЕМ ===")

for circuit_str in universal_circuits:
    try:
        low_b, high_b, guess = build_bounds_and_guess(circuit_str)
        safe_guess = np.clip(guess, np.array(low_b) + 1e-4, np.array(high_b) - 1e-4).tolist()

        circuit = CustomCircuit(circuit_str, initial_guess=safe_guess)
        circuit.fit(frequencies, Z_experimental, bounds=(low_b, high_b), weight_by_modulus=True)

        Z_pred = circuit.predict(frequencies)
        mean_fit_error = np.mean(np.abs(Z_experimental - Z_pred) / np.abs(Z_experimental)) * 100

        param_errors = []
        for p, conf in zip(circuit.parameters_, circuit.conf_):
            if p != 0 and conf is not None:
                param_errors.append(abs(conf / p) * 100)
            else:
                param_errors.append(np.inf)
        max_param_error = np.max(param_errors) if param_errors else np.inf

        results.append({
            'circuit_string': circuit_str,
            'model': circuit,
            'mean_fit_error': mean_fit_error,
            'max_param_error': max_param_error
        })
        print(f"[OK] {circuit_str:35} -> Трек: {mean_fit_error:.2f}%, Худший параметр: {max_param_error:.1f}%")
    except:
        pass

print("\n=== ВЫБОР ФИЗИЧЕСКИ КОРРЕКТНОГО ПОБЕДИТЕЛЯ ===")
valid_circuits = [r for r in results if r['max_param_error'] < 40.0]
best_match = min(valid_circuits if valid_circuits else results, key=lambda x: x['mean_fit_error'])

print(f"\n🏆 ОФИЦИАЛЬНЫЙ ПОБЕДИТЕЛЬ: {best_match['circuit_string']}")
print(f"-> Средняя ошибка трека: {best_match['mean_fit_error']:.3f}%")
print(f"-> Худшая погрешность параметров: {best_match['max_param_error']:.2f}%")
print("\nИтоговые параметры схемы:")
print(best_match['model'])

# Отрисовка
f_grid = np.logspace(np.log10(frequencies.min()), np.log10(frequencies.max()), 500)
Z_best_pred = best_match['model'].predict(f_grid)

fig, ax = plt.subplots(figsize=(10, 7))
ax.plot(Z_experimental.real, -Z_experimental.imag, 'o', color='royalblue', label='Эксперимент')
ax.plot(Z_best_pred.real, -Z_best_pred.imag, '-', color='crimson', lw=2.5, label=f"Fit: {best_match['circuit_string']}")
ax.set_xlabel('Re(Z) [Ом]')
ax.set_ylabel('-Im(Z) [Ом]')
ax.set_title(f"Автоподбор схемы для файла: {FILE_PATH}", fontweight='bold')
ax.grid(True, linestyle='--', alpha=0.5)
ax.axis('equal')
ax.legend()
plt.show()
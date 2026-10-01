#!/bin/zsh
set -u

project_dir="${0:A:h}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
touchhle_dir="$project_dir/vendor/touchHLE"
touchhle_bin="$touchhle_dir/target/release/touchHLE"
reports_dir="$project_dir/reports"
mkdir -p "$reports_dir" || exit 1
log_file="$reports_dir/manual-run-$(date '+%Y-%m-%d_%H-%M-%S')-$$.log"

{
  print -r -- "Начало запуска: $(date '+%Y-%m-%d %H:%M:%S %z')"
  print -r -- "Лог: $log_file"
  ipa_file="${BEBELLION_IPA:-$project_dir/input/8Bit Rebellion v1.4.5.ipa}"

  if [[ ! -f "$ipa_file" ]]; then
    print -u2 "IPA не найден: $ipa_file"
    exit 1
  fi

  if [[ ! -x "$touchhle_bin" ]]; then
    print -u2 "Сборка touchHLE не найдена: $touchhle_bin"
    print -u2 "Соберите её командой: cd vendor/touchHLE && CMAKE_POLICY_VERSION_MINIMUM=3.5 cargo build --release --locked"
    exit 1
  fi

  if ! command -v ffmpeg >/dev/null 2>&1; then
    print -u2 "ffmpeg не найден: видеоролики будут пропускаться. Установите FFmpeg и повторите запуск."
  elif ! command -v ffplay >/dev/null 2>&1; then
    print -u2 "ffplay не найден: видеоролики будут воспроизводиться без звука."
  fi

  print -r -- "IPA: ${ipa_file##*/}"
  print -r -- "Управление: A/D или ←/→ — движение; пробел — удар; W или ↑ — вход в доступную дверь; Esc — боковое меню"
  cd "$touchhle_dir" || exit 1
  unset ALSOFT_DRIVERS
  "$touchhle_bin" "$ipa_file" \
    --landscape-right --landscape-content-layout --tolerate-nil-dictionary-keys --no-error-popup \
    --keyboard-game-controls --button-to-touch=DPadLeft,40,290 \
    --button-to-touch=DPadRight,135,290 --button-to-touch=A,455,290
  run_status=$?
  print -r -- "Завершение: $(date '+%Y-%m-%d %H:%M:%S %z'); код: $run_status"
  exit "$run_status"
} 2>&1 | tee "$log_file"

exit ${pipestatus[1]}

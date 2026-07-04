#!/usr/bin/env bash
set -eu

grep -R "안전합니다\|문제 없습니다\|계약해도 됩니다\|법적으로 문제없습니다\|보증금을 반드시 지킬 수 있습니다\|등기부상 위험이 없습니다\|이 집은 거래해도 됩니다\|이 특약을 넣으면 됩니다" . \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude=grep_risk_terms.sh \
  --exclude=guardrails.py \
  --exclude=test_guardrails.py \
  --exclude=test_tools.py || true

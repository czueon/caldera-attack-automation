# 실험 실행 가이드

각 TTPs 시나리오별 실행 방법 요약

---

## TTPs 1

### .env 수정 사항
```env
VBOX_VM_NAME=ttps1
VBOX_SNAPSHOT_NAME=ttps1
VBOX_VM_NAME_lateral=ttps1_2
VBOX_SNAPSHOT_NAME_lateral=ttps1_2
# VBOX_VM_NAME_ad=
# VBOX_SNAPSHOT_NAME_ad=
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_1.pdf" --env "environment_ttps1.md"
```

---

## TTPs 2

### .env 수정 사항
```env
VBOX_VM_NAME=ttps2
VBOX_SNAPSHOT_NAME=ttps2
# VBOX_VM_NAME_lateral=
# VBOX_SNAPSHOT_NAME_lateral=
# VBOX_VM_NAME_ad=
# VBOX_SNAPSHOT_NAME_ad=
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_2.pdf" --env "environment_ttps2.md"
```

---

## TTPs 3

### .env 수정 사항
```env
VBOX_VM_NAME=ttps3
VBOX_SNAPSHOT_NAME=ttps3
# VBOX_VM_NAME_lateral=
# VBOX_SNAPSHOT_NAME_lateral=
# VBOX_VM_NAME_ad=
# VBOX_SNAPSHOT_NAME_ad=
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_3.pdf" --env "environment_ttps3.md"
```

---

## TTPs 4

### .env 수정 사항
```env
VBOX_VM_NAME=ttps4
VBOX_SNAPSHOT_NAME=ttps4
# VBOX_VM_NAME_lateral=
# VBOX_SNAPSHOT_NAME_lateral=
# VBOX_VM_NAME_ad=
# VBOX_SNAPSHOT_NAME_ad=
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_4.pdf" --env "environment_ttps4.md"
```

---

## TTPs 5

### .env 수정 사항
```env
VBOX_VM_NAME=ttps5
VBOX_SNAPSHOT_NAME=ttps5
VBOX_VM_NAME_lateral=ttps5_2
VBOX_SNAPSHOT_NAME_lateral=ttps5_2
VBOX_VM_NAME_ad=ttps5_ad
VBOX_SNAPSHOT_NAME_ad=ttps5_ad
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_5.pdf" --env "environment_ttps5.md"
```

---

## TTPs 6

### .env 수정 사항
```env
VBOX_VM_NAME=ttps6
VBOX_SNAPSHOT_NAME=ttps6
# VBOX_VM_NAME_lateral=
# VBOX_SNAPSHOT_NAME_lateral=
# VBOX_VM_NAME_ad=
# VBOX_SNAPSHOT_NAME_ad=
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_6.pdf" --env "environment_ttps6.md"
```

---

## TTPs 7

### .env 수정 사항
```env
VBOX_VM_NAME=ttps7
VBOX_SNAPSHOT_NAME=ttps7
VBOX_VM_NAME_lateral=ttps7_2
VBOX_SNAPSHOT_NAME_lateral=ttps7_2
# VBOX_VM_NAME_ad=
# VBOX_SNAPSHOT_NAME_ad=
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_7.pdf" --env "environment_ttps7.md"
```

---

## TTPs 8

### .env 수정 사항
```env
VBOX_VM_NAME=ttps8
VBOX_SNAPSHOT_NAME=ttps8
VBOX_VM_NAME_lateral=ttps8_2
VBOX_SNAPSHOT_NAME_lateral=ttps8_2
VBOX_VM_NAME_ad=ttps8_ad
VBOX_SNAPSHOT_NAME_ad=ttps8_ad
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_8.pdf" --env "environment_ttps8.md"
```

---

## TTPs 9

### .env 수정 사항
```env
VBOX_VM_NAME=ttps9
VBOX_SNAPSHOT_NAME=ttps9
# VBOX_VM_NAME_lateral=
# VBOX_SNAPSHOT_NAME_lateral=
# VBOX_VM_NAME_ad=
# VBOX_SNAPSHOT_NAME_ad=
```

### 전체 파이프라인 실행 명령어
```bash
python main.py --step all --pdf "data/raw/KISA_TTPs_9.pdf" --env "environment_ttps9.md"
```

---
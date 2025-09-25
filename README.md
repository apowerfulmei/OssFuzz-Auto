# DataGenerator

**Author:** apowerfulmei

---

## Usage

### 1. Reproduce Vulnerability Automatically with OSS-Fuzz

- Obtain vulnerability-related information and testcases
- Automatically roll back OSS-Fuzz to a specific version to correctly build the target program
- Automatically build the target program and reproduce vulnerabilities using testcases

### 2. Detect Commits that Introduce Vulnerabilities
- Generate diff files for the relevant code

---

## Project Structure

```
.
├── main.py
└── tools/
```

---

## How to Use

### Reproduce Specific Bug

```bash
python3 main.py -c config_path repro -n project_name -v bug_name -u url
```

For example:

```
python3 main.py -c ./config/template.json repro -n libxml2 -v OSV-2023-969 -u https://github.com/GNOME/libxml2
```

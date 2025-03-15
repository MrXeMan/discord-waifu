import os.path


def call(log_file: str):
    if not os.path.exists(log_file):
        return ["failed", "Failed to read the file. Check if log exist."]
    with open(log_file, "r", encoding="utf-8") as file:
        return file.readlines()
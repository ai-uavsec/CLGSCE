import re
import time

code_block_regex = re.compile(r"```(.*?)```", re.DOTALL)
def extract_python_code(content):
    code_blocks = code_block_regex.findall(content)
    if code_blocks:
        full_code = "\n".join(code_blocks)

        if full_code.startswith("python"):
            full_code = full_code[7:]

        return full_code
    else:
        return None

# log response/code 
def log(response, task_name, string = ""):
    file_name = "log/" + task_name + ".txt"
    
    if str(response):
        with open(file_name, "a", encoding="utf-8") as file:
            file.write(str(response) + string)

def overwrite_log(name):
    logfile_name = "log/" + name + ".txt"
    try:
        with open(logfile_name, 'w') as file:
            pass
    except FileNotFoundError:
        open(logfile_name, 'a').close()
        print(f"{logfile_name} not found. An empty file has been created.")

# remove comments, whitespace, empty lines   
def prune_code(code):
    # Remove comments (both single line and multi-line)
    code = re.sub(r'//.*?(\n|$)', '\n', code)  # Remove single-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)  # Remove multi-line comments
    code = re.sub(r"\s*#.*", "", code)
    # Remove leading and trailing whitespace from each line
    code = '\n'.join(line.strip() for line in code.split('\n'))

    # Optionally, remove empty lines
    code = '\n'.join(line for line in code.split('\n') if line)

    return code

# remove comments only
def remove_comments(code):
    # Remove single-line comments
    code = re.sub(r'#.*', '', code)
    
    # Remove multi-line comments (triple quotes)
    code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
    
    return code
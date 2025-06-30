import argparse
from openai import OpenAI
import os.path


# arguments for configuration selection
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--configuration",
                    type = str, default = "4", 
                    help = "Please select from \"1\", \"2\", \"3\", and \"4\", the default is \"4\" (roles, rules, references)."
                    )
args = parser.parse_args()

configuration = args.configuration

# read all trajectories from file (each line is a trajectory)
with open("trajectories.txt", "r") as f:
	trajectories = f.readlines()

# load system prompt based on the configuration argument
if configuration == "1":
    with open("system_prompts/role.txt", "r") as f:
        evaluator_sysprompt = f.read()
elif configuration == '2':
    with open("system_prompts/role_rule.txt", "r") as f:
        evaluator_sysprompt = f.read()
elif configuration == '3':
    with open("system_prompts/role_reference.txt", "r") as f:
        evaluator_sysprompt = f.read()
elif configuration == '4':
    with open("system_prompts/role_rule_reference.txt", "r") as f:
        evaluator_sysprompt = f.read()
else:
    print('Unknown configuration. Please select from \"1\", \"2\", \"3\", and \"4\", the default is \"4\" (roles, rules, references).')

print("Initializing GPT...")
client = OpenAI()

chat_history = [
    {
        "role": "system",
        "content": evaluator_sysprompt
    }
]

# log response/code 
def log(response, task_name, string = ""):
    file_name = "log/" + task_name + ".txt"
    
    if str(response):
        with open(file_name, "a", encoding="utf-8") as file:
            file.write(str(response) + string)

# the LLM generate response without considering chat history (for evaluation/feedback).
def request_single_step(prompt, model_name):
    chat = chat_history.copy()
    chat.append(
		{
			"role": "user",
			"content": prompt
		}
	)
    completion = client.responses.create(
		model = model_name, 
		input = chat
	)
    response = completion.output_text
    
    return response

# set parameters
task_name = "advanced"
feedback_model_name = "o3-mini" # the model is "o3-mini-2025-01-31" when conducting the experiment
repeat = 3

# read task prompt text file with respect to task name

with open(os.path.dirname(os.path.dirname(__file__)) + "/task_sets/" + task_name + ".txt", 'r') as file:
    tasks = file.readlines()
len_tasks = len(tasks)

# for each repeat and each trajectory, generate feedback and log it
for i in range(repeat):
    for idx, trajectory in enumerate(trajectories):
        task_prompt = tasks[idx % len_tasks] # cycle through task prompts if fewer than trajectories
        prompt = "Task description: " + task_prompt + "\n" + "Action steps: " + trajectory
        feedback = request_single_step(prompt, feedback_model_name)
        log(f"task {idx % len_tasks + 1}: " + feedback + '\n', 'evaluation')
        print(f'task {idx % len_tasks + 1} repeat {i+1} feedback: {feedback}')
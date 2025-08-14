import argparse
import datetime
from openai import OpenAI

from my_utils import *
from evaluate import *

# -------------------- Argument Parsing --------------------
# command-line arguments for method and task selection
parser = argparse.ArgumentParser()
parser.add_argument("-m", "--method",
                    type = str, default = "NL", 
					choices=["GSCE", "self-refine", "numerical", "NL"],
                    help = "Choose method from \"GSCE\", \"self-refine\", \"numerical\", or \"NL\". The default method is \"NL\"."
                    )
parser.add_argument("-t","--task", 
                    type = str, default = "advanced",
					choices=["basic", "advanced"],
                    help = "Choose task set from \"basic\" or \"advanced\". The default task set is \"advanced\".")
args = parser.parse_args()

method = args.method
task_name = args.task

print("Initializing GPT...")
client = OpenAI() # initialize OpenAI client

# -------------------- Load Prompt Files --------------------
# load system prompts for code generator
with open("system_prompts/airsim_drone.txt", "r") as f:
	sysprompt = f.read()
with open("system_prompts/airsim_drone_API.txt", "r") as f:
    API_prompt = f.read()

# load system prompts for evaluator
if method == "numerical":
	with open("system_prompts/numerical_evaluator.txt", "r") as f:
		evaluator_sysprompt = f.read()
else:
	with open("system_prompts/evaluator.txt", "r") as f:
		evaluator_sysprompt = f.read()

# read task prompt text file with respect to task name
with open("task_sets/" + task_name + ".txt", 'r') as file:
	tasks = file.readlines()


# -------------------- Initialize GPT Chat Histories --------------------
# initialize history for code generation
code_history = [
    {
        "role": "system",
        "content": sysprompt
    },
    {
        "role": "user",
        "content": API_prompt
    }
]

# initialize history for feedback
feedback_history = [
    {
        "role": "system",
        "content": evaluator_sysprompt
    }
]

# -------------------- OpenAI Request Functions --------------------
# the LLM generate response according to all chat history (for code generation and refinement).
def request(prompt, model_name):
    code_history.append(
		{
			"role": "user",
			"content": prompt
		}
	)
    completion = client.chat.completions.create(
		model = model_name,
		messages = code_history
	)
    response = completion.choices[0].message.content
    code_history.append(
        {
            "role": "assistant",
            "content": response,
        }
    )
    
    return response

# the LLM generate response without considering chat history (for evaluation/feedback).
def request_single_step(history, prompt, model_name):
    chat = history.copy()
    chat.append(
		{
			"role": "user",
			"content": prompt
		}
	)
    completion = client.chat.completions.create(
		model = model_name, 
		messages = chat
	)
    response = completion.choices[0].message.content
    
    return response

# -------------------- Experiment Parameters --------------------
repeat = 3	# code generation repeat times
evaluate = 1 # flag for whether evaluating generated code within this script
refinement_time = 6	# correction times for each task
model_name = "o3-mini" # the model is "o3-mini-2025-01-31" when conducting the experiment
feedback_model_name = "o3-mini" # the model is "o3-mini-2025-01-31" when conducting the experiment

print(f"Repeat {repeat} times for {task_name}, using {model_name} for code generation and {feedback_model_name} for evaluation.")
print(f"Generating code for {task_name} set ...")

overwrite_log(task_name)	# delete previously generated code

# -------------------- Code Generation Loop --------------------
for it in range(repeat):
	for i, task_prompt in enumerate(tasks):
		print(f"Generating code for task {i} on the {it}th repeat.")

		# generate initial code
		response = request(task_prompt, model_name)
		if model_name != "o3-mini":
			response = extract_python_code(response)

		# for  NL, numerical, or self-refine methods
		if method == "NL" or method == "numerical" or method == "self-refine":
			if not response:
				print(f"Failed to generate code for task {i} on the {it} repeat.")
				observation = "No code generated."
			
			# get observation from generated code
			if method == "numerical":
				observation = numerical_observation(response)
			else:
				observation = NL_observation(response, task_prompt)
			
			print(observation)
			# feedback loop: refine code if feedback is negative
			for correction in range(refinement_time + 1):
				if not observation:
					print(f"Failed to generate trajectory for task {i} on the {it} repeat.")
				
				## get evaluation feedback
				# for self-refine, ask the code generator, other methods ask a secondary LLM-agent(evaluator)
				if method == "self-refine":
					prompt = "The code you generated control the drone flies the following action steps: " + observation + "\n" + evaluator_sysprompt
					feedback = request(prompt, feedback_model_name)
				else:
					prompt = "Task description: " + task_prompt + "\n" + "Action steps: " + observation
					feedback = request_single_step(feedback_history, prompt, feedback_model_name)
				
				# if feedback is YES, end the feedback loop
				if "YES" in feedback:
					break
				# if feedback is NO, refine the code
				elif "NO" in feedback:
					if correction == refinement_time and "NO" in feedback:
						print(f"****No further correction for task {i} on the {it} repeat, human intervention needed****")
						break
					
					# refinement prompt for code generator
					correction_prompt = "\n The differences between actions and task description: " \
										+ feedback.replace("NO", "") + " \n Please reason where you did wrong and refine the code based on the differences. "

					print(f" repeat {it}, task {i}, the {correction + 1}th feedback: ---", correction_prompt)

					# For self-refine, ask the code generator
					if method == "self-refine":
						response = request("Please reason where you did wrong and regenerate the code that correct the errors, generate code only.", model_name)
					else:
						response = request(correction_prompt, model_name)

					if model_name != "o3-mini":
						response = extract_python_code(response)

					# Update observation after refinement for the iterative process
					if method == "numerical":
						observation = numerical_observation(response)
					else:
						observation = NL_observation(response, task_prompt)
		
		# no feedback for GSCE, since it's an open-loop method
		elif method == "GSCE":
			pass
		
		else:
			print("Unknown method. Please choose method from \"GSCE\", \"self-refine\", \"numerical\", and \"NL\". The default method is \"NL\". ")
		
		# log the generated code to under /log
		log(response, task_name + '_' + method, "\n\n---------\n")
		# reset code history for next task
		code_history = [
			{
				"role": "system",
				"content": sysprompt
			},
			{
				"role": "user",
				"content": API_prompt
			}
		]

# -------------------- Get Evaluation Result --------------------
	result = evaluate_task(task_name, method)
else:
	print(f"No evaluation for {task_name}!")


print("*** See log/xxx_result.txt for results ***")
now = datetime.datetime.now()
print("Current date and time:", now.strftime("%Y-%m-%d %H:%M:%S"))

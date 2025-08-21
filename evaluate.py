import math
import numpy as np
import datetime
from my_utils import *
from airsim_wrapper import *

aw = AirSimWrapper()

'''
evaluate code
'''
def evaluate_task(task_name, method):
    print(f"Evaluating {task_name} ...")
    # read task prompt text file with respect to task name
    with open("task_sets/" + task_name + ".txt", 'r') as file:
        tasks = file.readlines()
    len_tasks = len(tasks)
    
    overwrite_log(task_name + '_' + method + '_result')	# clear history result log

    if task_name == "basic" or "advanced":
        # read generated code from log
        with open("log/" + task_name + '_' + method + ".txt", 'r', encoding="utf-8") as file:
            lines = file.readlines()

        # load ground truth state changes for each task
        changes = np.loadtxt("ground_truth/" + task_name + ".txt")
        state_changes = []
        seperate = 0
        for idx, state_change in enumerate(changes):
            if state_change[0] == 2:
                state_changes.append(changes[seperate:idx].tolist())
                seperate = idx + 1
        
        # initialize parameters
        code = "" # initial code as an empty string
        len_state_changes = len(state_changes)
        index = 0
        success = 0
        overall_completeness = 0
        overall_success = 0
        i = 0
        state_change = np.asarray(state_changes[i])
        
        # initialize drone position to [0 0 -10] to prevent collision to the ground caused by incorrect code 
        aw.reset_airsim()
        time.sleep(1)
        aw.fly_to([0, 0, -10])
        time.sleep(1)
        
        # iterate through lines of generated code
        for idx, line in enumerate(lines):
            
            if line == "---------\n":
                # compute completeness
                completeness = success/len(state_change)
                overall_completeness += completeness
                log(str(completeness) + " " +str(i), task_name + '_' + method + '_result', "\n")
                # compute success rate (SR)
                if completeness == 1:
                    overall_success += 1

                # reset for next task's code script
                code = ""
                index = 0
                success = 0
                i += 1
                state_change = np.asarray(state_changes[i%len_state_changes]) # cycle through ground truth for the following repeat

                aw.reset_airsim()
                aw.fly_to([0, 0, -10])
                time.sleep(1)

            else:
                if line == "python\n":
                    pass
                elif line == "None\n":
                    success = 0
                else:

                    initial_state = aw.get_state() # get last drone state

                    # handling multi-line by transforming multi-line into one line 
                    try:
                        if code != "":
                            exec(code)
                            code = ""
                        
                        exec(line)
                            
                    except SyntaxError:
                        code += line

                    # check through all the state changes
                    if len(state_change) > index:
                        current_state = aw.get_state() # get updated state
                        differences = np.asarray(current_state) - np.asarray(initial_state) # difference between last state and updated state 
                        differences[3] = ((differences[3] + 180) % 360) - 180 # map yaw angle differences to [-180, 180]
                        
                        # check if a significant movement occurred (an action)
                        if abs(differences[0]) > 2 or abs(differences[1]) > 2 or abs(differences[2]) > 1 or abs(differences[3]) > 30:
                            if round(abs(differences[3])/10) == 18:
                                differences[3] = 180
                            
                            check_equality = differences - state_change[index][1:5]
                            
                            # if movement matches ground truth within tolerance, count as success action
                            if state_change[index][0] == 1 and abs(check_equality[0]) < 1.5 and abs(check_equality[1]) < 1.5 and abs(check_equality[2]) < 1.5 and abs(check_equality[3]) < 6:
                                success += 1
                            
                            # update index
                            if len(state_change) > 1:
                                index += 1
                            else:
                                index = 0
        
        # compute overall results
        result = [overall_success/i, overall_completeness/i]

    else:
        print("Unkown task name")
        result = np.nan
    
    # store result to result.txt
    if isinstance(result, list):
        result = ' '.join(map(str, result))	# converts a list of elements into a single string, with each element separated by a space.
        log(result, task_name + '_' + method + '_result', "  " + task_name + "\n")
    else:
        log(result, task_name + '_' + method + '_result', "  " + task_name + "\n")
    print(f"{task_name} result: {result}")

    # store how many times tasks are repeated
    repeat = i/len_tasks
    log("repeat times: ", task_name + '_' + method + '_result', str(repeat) + "\n")
    
    # store date & time to .txt for reference 
    now = datetime.datetime.now()
    log(now.strftime("%Y-%m-%d %H:%M:%S"), task_name + '_' + method + '_result', "\n")	# transfrom to human-readable format
    
    return result

'''
NL State Observation Transformation Implementation
Converts a sequence of code lines (response) into a natural language description of the drone's actions.
'''
def NL_observation(response, task_prompt):
    # initialize
    description = ""
    shape = ""
    code = ""
    action_idx = 1
    reset_height = -10
    aw.reset_airsim()
    aw.fly_to([0, 0, reset_height])
    time.sleep(1)
    
    # iterate through lines of generated code
    for idx, line in enumerate(response.splitlines()):

        if line == "python\n":
            pass
        elif line == "None\n":
            pass
        else:
            last_state = aw.get_state() # get last drone state
            
            # handling multi-line by transforming multi-line into one line 
            try:
                if code != "":
                    exec(code)
                    code = ""
                
                exec(line)
                    
            except SyntaxError:
                code += line
            
            # log runtime errors into the NL observation
            except NameError as e:
                description = "NameError occurred: " + f" {e}"
                return  description
                
            current_state = aw.get_state() # get updated state
            differences = np.asarray(current_state) - np.asarray(last_state)

            # state transformation
            if abs(differences[0]) > 2 or abs(differences[1]) > 2 or abs(differences[2]) > 1 or abs(differences[3]) > 20:
                
                x = differences[0]
                y = differences[1]
                z = differences[2]
                yaw = differences[3]
                
                # take round result to mitigate "AirSim" simulator state observation error
                x_round = round(x)
                y_round = round(y)
                z_round = round(z)
                yaw_round = round(yaw/15)*15
                
                yaw_current = current_state[3]
                current_yaw_round = round(yaw_current/15)*15
                
                # body frame differences
                theta = -current_state[3]
                theta = math.radians(theta)
                x_body = x * math.cos(theta) - y * math.sin(theta)
                y_body = x * math.sin(theta) + y * math.cos(theta)
                z_body = -z
                x_body_round = round(x_body)
                y_body_round = round(y_body)
                z_body_round = -z_round
                
                # add ID for each action
                description += f"Action {action_idx}: "
                action_idx += 1

                ## movement only in z axis
                if x_round == 0 and y_round == 0 and z_round != 0 and yaw_round == 0:
                    # when height difference exceeds 12 meters will see as landing
                    if z > 12:
                            description += "Landing."
                    elif z < 0:
                        if -z_round == 2:
                            description += "Take off."  # take off flies up 2 meters
                        else:
                            description += f"Fly {-z_round} meters up. " # fly uo
                    elif z > 0 and z <= 15:
                        description += f"Fly {z_round} meters down. " # fly down
                    else:
                        pass

                ## yaw rotation 
                elif abs(yaw_round) > 20:
                    yaw_180map = ((yaw_round + 180) % 360) - 180 # map yaw_round to [-180, 180]
                    if yaw_180map == -180:
                        yaw_180map = 180
                    if yaw_180map < 0:
                        description += f"Turn {-yaw_180map} degrees counterclockwise. "
                    elif yaw_180map > 0:
                        description += f"Turn {yaw_180map} degrees clockwise. "                        
                    else:
                        pass
                
                elif (x_round != 0 or y_round != 0) and yaw_round == 0:
                    if "drone's body frame" not in task_prompt:
                        # orientation in movement
                        if current_yaw_round == 90:
                            orientation = "east"
                        elif current_yaw_round == -90:
                            orientation = "west"
                        elif current_yaw_round == -180 or current_yaw_round == 180:
                            orientation = "south"
                        elif current_yaw_round == 0:
                            orientation = "north"
                        else:
                            orientation = f"{current_yaw_round} degrees"

                        ## movement in x axis of world frame
                        if abs(x_round) > 1 and abs(y_round) <= 1:
                            if x_round < 0:
                                movement =  f"Fly {-round(x_round/5)*5} meters South in the world axis while facing {orientation}. The drone moves to[{round(current_state[0]/5)*5}, {round(current_state[1]/5)*5}, {round(current_state[2]/5)*5}]. "
                            else:
                                movement = f"Fly {round(x_round/5)*5} meters North in the world axis while facing {orientation}. The drone moves to [{round(current_state[0]/5)*5}, {round(current_state[1]/5)*5}, {round(current_state[2]/5)*5}]. "
                        elif abs(x_round) <= 1 and abs(y_round) > 1:
                            ## movement in y axis of world frame
                            if y_round < 0:
                                movement = f"Fly {-round(y_round/5)*5} meters West in the world axis while facing {orientation}. The drone moves to [{round(current_state[0]/5)*5}, {round(current_state[1]/5)*5}, {round(current_state[2]/5)*5}]. "
                            else:
                                movement = f"Fly {round(y_round/5)*5} meters East in the world axis while facing {orientation}. The drone moves to [{round(current_state[0]/5)*5}, {round(current_state[1]/5)*5}, {round(current_state[2]/5)*5}]. "
                        else:
                            movement = f"The drone moves to [{round(current_state[0])}, {round(current_state[1])}] while facing {orientation}."
                        description += movement
                        
                    else:
                        
                        ## body frame movement in x-y plane
                        if z_round == 0:
                            if abs(x_body_round) > 1 and abs(y_body_round) <= 1:
                                if x_body_round < 0:
                                    description += f"Fly {-x_body_round} meters backward in drone's body frame. "
                                elif x_body_round > 0:
                                    description += f"Fly {x_body_round} meters forward in drone's body frame. "
                            elif abs(x_body_round) <= 1 and abs(y_body_round) > 1:
                                if y_body_round < 0:
                                    description += f"Fly {-y_body_round} meters left in drone's body frame. "
                                elif y_body_round > 0:
                                    description += f"Fly {y_body_round} meters right in drone's body frame. "
                            else:
                                pass
                                # description += "unknown movement in xy plane" # waiting for comprehensive movement implementation.
                        
                        ## body frame movement in y-z or x-z plane
                        else:
                            move = round((x ** 2 + y ** 2 + z ** 2) ** 0.5)
                            if move > 15:
                                description += "Landing."
                            # body frame movement in y-z plane
                            elif x_body_round == 0:
                                degree = math.degrees(math.atan(abs(z_body)/abs(y_body)))
                                degree = round(degree/15)*15
                                # top right
                                if y_body_round > 0 and z_body_round > 0:
                                    description += f"Fly the drone in the top-right direction at an angle of {degree} degrees from the horizontal axis, in the YZ plane of drone's body frame for a distance of {move} meters. "
                                # bottom right
                                if y_body_round > 0 and z_body_round < 0:
                                    description += f"Fly the drone in the bottom-right direction at an angle of {degree} degrees from the horizontal axis, in the YZ plane of drone's body frame for a distance of {move} meters. "
                                # top left
                                if y_body_round < 0 and z_body_round > 0:
                                    description += f"Fly the drone in the top-left direction at an angle of {degree} degrees from the horizontal axis, in the YZ plane of drone's body frame for a distance of {move} meters. "
                                # bottom left
                                if y_body_round < 0 and z_body_round < 0:
                                    description += f"Fly the drone in the bottom-left direction at an angle of {degree} degrees from the horizontal axis, in the YZ plane of drone's body frame for a distance of {move} meters. "
                            # body frame movement in x-z plane
                            elif y_body_round == 0:
                                degree = math.degrees(math.atan(abs(z_body)/abs(x_body)))
                                degree = round(degree/15)*15
                                # top forward
                                if x_body_round > 0 and z_body_round > 0:
                                    description += f"Fly the drone in the top-forward direction at an angle of {degree} degrees from the horizontal axis, in the XZ plane of drone's body frame for a distance of {move} meters. "
                                # bottom forward
                                if x_body_round > 0 and z_body_round < 0:
                                    description += f"Fly the drone in the bottom-forward direction at an angle of {degree} degrees from the horizontal axis, in the XZ plane of drone's body frame for a distance of {move} meters. "
                                # top backward
                                if x_body_round < 0 and z_body_round > 0:
                                    description += f"Fly the drone in the top-backward direction at an angle of {degree} degrees from the horizontal axis, in the XZ plane of drone's body frame for a distance of {move} meters. "
                                # bottom backward
                                if x_body_round < 0 and z_body_round < 0:
                                    description += f"Fly the drone in the bottom-backward direction at an angle of {degree} degrees from the horizontal axis, in the XZ plane of drone's body frame for a distance of {move} meters. "
            
    return description

'''
Convert code lines (response) into a numerical representation of the drone's actions, based on observed state changes.
'''
def numerical_observation(response):
    # initialize
    observation = ""
    code = ""
    action_idx = 1
    # reset drone position
    aw.reset_airsim()
    aw.fly_to([0, 0, -10])
    time.sleep(1)

    state = np.zeros(4) # initialize state vector [x, y, z, yaw]

    for idx, line in enumerate(response.splitlines()):

        if line == "python\n":
            pass
        elif line == "None\n":
            pass
        else:
            last_state = aw.get_state()
            # handle multi-line code execution
            try:
                if code != "":
                    exec(code)
                    code = ""
                
                exec(line)
                    
            except SyntaxError:
                code += line

            # log runtime errors into the NL observation
            except NameError as e:
                description = "NameError occurred: " + f" {e}"
                return  description
            current_state = aw.get_state()
            differences = np.asarray(current_state) - np.asarray(last_state)
            

            if abs(differences[0]) > 2 or abs(differences[1]) > 2 or abs(differences[2]) > 1 or abs(differences[3]) > 20:
                
                x = differences[0]
                y = differences[1]
                z = differences[2]
                yaw = differences[3]
                
                # take round result to mitigate "AirSim" simulator state observation error
                x_round = round(x)
                y_round = round(y)
                z_round = round(z)
                yaw_round = round(yaw/15)*15

                # mitigate drone drift in "AirSim" simulation
                if abs(x_round) <= 1:
                    x_round = 0
                if abs(y_round) <= 1:
                    y_round = 0

                yaw_round = ((yaw_round + 180) % 360) - 180 # map yaw_round to [-180, 180]
                if yaw_round == -180:
                    yaw_round = 180

                differences = np.asarray([x_round, y_round, z_round, yaw_round])
                state += differences # update numerical state observation

                if z_round == -2:
                    observation += f"{action_idx}, take off. " # case for take off
                else:
                    observation += f"{action_idx}, [{x_round}, {y_round}, {z_round}, {yaw_round}]. "

                action_idx += 1

    return observation


if __name__ == "__main__":
    # run evaluation for 'advanced' task if script is executed directly
    result = evaluate_task("advanced", "GSCE")
    print(f"***Evaluate via evaluate.py***    success rate: {result}")
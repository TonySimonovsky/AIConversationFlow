import json
import copy
import time
import os
import inspect
import logging





class AIConversationFlow():


    def __init__(self, logs_folder="aiconversationflow_logs/", log_on=True):
        self.__version__ = '0.0.4'
        self.logs_folder = logs_folder
        self.log_on = log_on

        # setting up logging

        # Check if logs_folder exists and create it if it doesn't
        if not os.path.exists(self.logs_folder):
            os.makedirs(self.logs_folder)

        # Create a logger for step-by-step logs
        self.sbs_logger = logging.getLogger('step_by_step')
        self.sbs_logger.setLevel(logging.INFO)  # Or whatever level you want

        # Remove all handlers associated with the logger object.
        for handler in self.sbs_logger.handlers[:]:
            self.sbs_logger.removeHandler(handler)

        # Create a file handler
        sbs_handler = logging.FileHandler(f'{self.logs_folder}step_by_step.log')
        sbs_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.sbs_logger.addHandler(sbs_handler)


    def log(self, level, class_instance, message, user_id=None):

        # print(f"""TMP inside log method: self.log_on: {self.log_on}""")

        if self.log_on:
            current_frame = inspect.currentframe()
            frame_info = inspect.getframeinfo(current_frame.f_back)
            
            file_name = os.path.basename(frame_info.filename)  # Get only the base filename, not the full path
            line_number = frame_info.lineno
            class_name = class_instance.__class__.__name__
            func_name = current_frame.f_back.f_code.co_name

            # Check if the logging level is valid
            if level not in ['debug', 'info', 'warning', 'error', 'critical']:
                level = 'info'

            log_func = getattr(self.sbs_logger, level)
            log_message = f'{file_name}:{line_number} - {class_name} - {func_name} - {message}'

            # Add user ID to the log message if it's provided
            if user_id is not None:
                log_message += f' - user {user_id}'

            log_func(log_message)
        else:
            return





class MacroFlow(AIConversationFlow):

    """

    Short: MAF

    """


    # ----------------------------------------
    # 
    # MAF initiation and running methods
    #



    def __init__(self, system_prompt:str=None, log_on=True):

        super().__init__(log_on=log_on)

        # initialize MAF system prompt; this prompt should serve as a basis of the bot personality
        self.system_prompt = system_prompt

        # this is the storage for all of the chat history
        self.messages = [{ "role": "system", "content": self.system_prompt }]

        # status of the MAF
        self.maf_status = "pending"

        # indication if a mif was just completed (? needed)
        self.just_finished_mif = False

        # # current mif name
        # self.cur_step = None

        # stack of mif's, similar to chat history, but contains the states and the data
        self.steps = []

        # library of preset mif objects, used as templates to create steps from
        self.miflib = {}



    def register_mif(self, microflow:'MicroFlow'):
        """
        Method to add a new mif to the library of MAF. Library is then used to create new steps from.
        """

        microflow.macroflow = self

        # add to the MIF library of MAF
        self.miflib[microflow.name] = microflow



    def add_step(self, step):
        """
        Method to add a mif to the steps stack. Steps stack is the history of statuses.

        step: name of a MicroFlow()
        """
        
        # add to the stack
        self.steps.append(self.miflib[step].clone())



    def run(self, user_message=None, state=None):
        """
        Method to run MAF, which orchestrates mif's.
        """

        if state:
            self.log("info", self, f"Loading previous state...")

            try:
                self.maf_init_from_state(state=state)
                self.log("info", self, f"State loaded: {state}")
            except Exception as e:
                self.log("error", self, f"Couldn't load previous state: {e}")

        self.log("info", self, f"STARTED MAF run with user message '{user_message}'")

        if self.maf_status == "pending":
            self.log("info", self, f"This is the initiation of the MAF")
            self.maf_status = "in_progress"
        


        current_microflow = self.steps[-1]
        self.log("info", self, f"current_microflow: {current_microflow}")


        # if this was the last mif in the maf, so we are finishing the maf
        if current_microflow.mif_status == "completed":
            ai_message = "Flow completed"
            self.maf_status = "completed"

            self.log("info", self, f"""Last mif and MAF completed""")


        else:

            ai_message = current_microflow.run(user_message)

            # if we just finiashed a microflow, do not need to return any ai message
            if self.just_finished_mif:
                ai_message = None


        self.log("info", self, f"""RETURNING ai_message: {ai_message}""")

        return ai_message



    # ----------------------------------------
    # 
    # MAF navigation methods
    #


    def prev_step(self):
        """
        What is the previous step?
        """
        if len(self.steps) > 2:
            return self.steps[-2]
        else:
            return None



    def cur_step(self):
        """
        What is the current step?
        """
        return self.steps[-1]



    # ----------------------------------------
    # 
    # Serializaion and representation methods
    #



    def _serializer(self,obj):
        if isinstance(obj, MicroFlow):
            return obj.mif_state_serialized()
        return str(obj)



    def maf_state_serialized(self):
        return json.dumps({
            "messages": self.messages,
            "maf_status": self.maf_status,
            "just_finished_mif": self.just_finished_mif,
            # "cur_step": self.cur_step,
            "steps": self.steps,
        }, default=self._serializer)



    def maf_init_from_state(self, state:dict):
        self.system_prompt = state["system_prompt"]
        self.messages = state["messages"]
        self.maf_status = state["status"]
        self.just_finished_mif = state["just_finished_mif"]
        # # current step
        # self.cur_step = state["cur_step"]

        self.steps = []# self.miflib[step] for step in state["steps"] ]
        for step in state["steps"]:
            self.steps.append(self.miflib[step["name"]].clone(step))



    def __str__(self):
        """

        What we show when the object is used as a string.
        
        """

        return f"""\n\n
            MacroFlow Status: {self.maf_status}\n
            Steps: {self.steps}\n
            Previous Microflow: {self.prev_step()}\n
            Current: {self.cur_step()}
            Just Finished MIF: {self.just_finished_mif}
        \n\n"""
    

    # def serialize(self):
    #     return json.dumps(vars(self), default=str)

    



class MicroFlow(AIConversationFlow):

    """

    Short: mif

    """



    # ----------------------------------------
    # 
    # mif initiation and running methods
    #



    def __init__(self,
                 name:str,
                 llm,
                 llm_params:dict,
                 system_prompt:str,
                 start_with:str,
                 completion_condition:dict,
                 next_steps:list,
                 ai_message:str=None,
                 data_to_collect:list=[],
                 goodbye_message=None,
                 callback=None,
                 macroflow:MacroFlow=None):
        
        super().__init__(log_on=macroflow.log_on)
        
        self.id = time.time()
        self.name = name
        self.mif_status = "pending"

        # indication of who starts the mif: "user" or "AI"
        self.start_with = start_with

        # link to the parent MAF
        self.macroflow = macroflow

        # system prompt of this mif; here you store the instructions of the current step of the dialogue
        self.system_prompt = system_prompt

        # this sets the conditions to complete the prompt and also collects the data from the user;
        #   for now, we have 2 types of completion conditions: "answer" and "llm_reasoning"
        self.completion_condition = completion_condition

        # (potentially to remove and use reasoning as a router) indicate possible steps we go to after completing the current one
        self.next_steps = next_steps

        # message we send in the end of the mif (if required by settings)
        self.goodbye_message = goodbye_message

        self.callback = callback

        # LLM we use for this mif
        self.llm = llm
        # LLM settings
        self.llm_params = llm_params

        # self.goto = None

        self.ai_message = ai_message

        self.data = {
            "data_to_collect": data_to_collect
        }



    def run(self, user_message=None):
        """
        This orchestrates the MIF.
        """

        self.log("info", self, f"STARTING a run of {self.name} (status {self.mif_status}, llm {self.llm.vendor})")
        self.log("info", self, f"INPUT: user_message: {user_message}")

        ai_message = None

        cbres = None
        if self.callback:
            cbres = self.callback()
            self.log("info", self, f"cbres: {cbres}")


        just_started = False

        if self.mif_status == "pending":

            self.log("info", self, f"Initiating the mif {self.name}")

            sp = self.system_prompt
            if cbres:
                sp = sp.format(cbres=cbres)
            
            # self.log("info", self, f"TMP data: {self.data}")
            # self.log("info", self, f"TMP sp before adding data: {sp}")

            # if there are any data variables in the prompt, include their values
            sp = sp.format(**self.data)

            # self.log("info", self, f"TMP sp after adding data: {sp}")
            

            if self.macroflow.messages:
                self.macroflow.messages[0]["content"] = self.macroflow.system_prompt + sp

            if self.llm.requires_user_message and self.start_with != "user":
                self.macroflow.messages.append({ "role": "user", "content": "[ignore this message and continue following your instructions]" })


            self.mif_status = "in_progress"
            self.macroflow.just_finished_mif = False
            just_started = True


        self.log("info", self, f"""user_message: {user_message}, just_started: {just_started}, self.start_with: {self.start_with}""")

        # if there is a user message but unless we are just starting
        if user_message and not (just_started and "AI" not in self.start_with):

            self.macroflow.messages.append({ "role": "user", "content": user_message })

            # if the completion condition is first user's answer
            if self.completion_condition["type"] == "answer":

                self.log("info", self, f"""completion_condition: {self.completion_condition}""")
                self.log("info", self, f"""self.completion_condition.get("details"): {self.completion_condition.get("details")}""")
                

                if "details" in self.completion_condition:
                    if user_message.lower() in self.completion_condition["details"].keys():
                        self.log("info", self, f"""user_message: {user_message}, completion_condition: {self.completion_condition['details'].keys()}""")
                        if self.completion_condition["details"][user_message.lower()].get("goto"):
                            next_step = self.completion_condition["details"][user_message.lower()]["goto"]
                            self.log("info", self, f"""ENDING a run of {self.name}, going to {next_step} (status {self.mif_status}, llm {self.llm.vendor})""")
                            return self.finish(goto=next_step)
                        else:
                            self.log("info", self, f"""ENDING a run of {self.name} (status {self.mif_status}, llm {self.llm.vendor})""")
                            return self.finish()

                elif len(self.next_steps)>0:
                    self.log("info", self, f"""! ENDING a run of {self.name}, going to {self.next_steps[0]} (status {self.mif_status}, llm {self.llm.vendor})""")

                    return self.finish(goto=self.next_steps[0])

                
                # print(f"next_step: {next_step}")

            # if the completion condition requires LLM reasoning
            elif self.completion_condition["type"] == "llm_reasoning":

                attempts = 5

                for i in range(attempts):
                    self.log("info", self, f'{i+1} attempt to get json-reasoning')

                    newline = "\n"
                    chat_history_for_reasoning = newline.join([ f"{m['role']}: {m['content']}" for m in self.macroflow.messages ])
                    llm_reasoning_response = self.completion_condition["details"]["llm"].create_completion(
                        messages=[
                            {"role":"system","content":f"Here's the previous conversation with the Human (User):\n----\n{chat_history_for_reasoning}\n----\n\n"+self.completion_condition["details"]["system_prompt"]},
                        ],
                        llm_params=self.completion_condition["details"]["llm_params"]
                    )
                    try:
                        llm_reasoning = json.loads(llm_reasoning_response['choices'][0]['message']['content'])
                        self.log("info", self, f'Reasoning received: {llm_reasoning}')
                    except:
                        self.log("error", self, f"""Attempt failed because of the invalid json output: {llm_reasoning_response["choices"][0]["message"]["content"]}""")
                        continue

                    self.mif_status = llm_reasoning["status"]
                    ai_message = llm_reasoning["comment"]

                    # saving data collected in the session datastore
                    for k,v in llm_reasoning.items():
                        if k in ("reasoning","status","comment"):
                            continue
                        if k not in self.data["data_to_collect"]:
                            self.data["data_to_collect"] = { "details": "", "data": "" }
                        self.data["data_to_collect"][k]["data"] = v
                    break

                if self.mif_status == "completed":
                    next_step = None
                    if len(self.next_steps)>0:
                        next_step = self.next_steps[0]

                    return self.finish(goto=next_step)


        # just started the mif and the first message is predefined AI message
        if just_started and self.ai_message:
            ai_message = self.ai_message

        else:
            ai_message = self.llm.create_completion(messages=self.macroflow.messages,llm_params=self.llm_params)['choices'][0]['message']['content']

        self.macroflow.messages.append({"role":"assistant","content":ai_message})

        self.log("info", self, f"RETURNING ai_message: {ai_message}")

        return ai_message



    def finish(self, goto=None):

        self.log("info", self, f"""START (mif {self.name}, status {self.mif_status})""")

        self.mif_status = "completed"
        self.macroflow.just_finished_mif = True

        # finalizing the flow
        if not goto:
            self.macroflow.maf_status = "completed"

        # going to the next step
        else:
            self.macroflow.add_step(goto)
        
        return self.goodbye_message

    

    # ----------------------------------------
    # 
    # mif initiation and running methods
    #



    def clone(self, state:dict=None):
        cloned = copy.deepcopy(self)
        cloned.id = time.time()
        cloned.macroflow = self.macroflow

        if state:
            cloned.id = state["id"],
            cloned.name = state["name"],
            cloned.mif_status = state["mif_status"],
            cloned.data = state["data"],

        return cloned



    def __deepcopy__(self, memo):
        # Create a new instance of the class including required params
        init_arg_names = inspect.getfullargspec(self.__init__).args[1:]  # Exclude 'self'
        new_obj = type(self)(**{k: v for k, v in vars(self).items() if k in init_arg_names})
        memo[id(self)] = new_obj

        # Copy all non-OpenAI attributes
        for name, value in self.__dict__.items():
            if name == 'completion_condition':
                if value.get('details') and value['details'].get('llm'):
                    # Create a copy of the value dictionary
                    value_copy = value.copy()
                    llm = value_copy['details']['llm']
                    value_copy['details']['llm'] = type(llm)(api_key=llm.api_key,log_on=self.log_on)  # replace with the updated value
                    # Set the attribute to the updated copy
                    setattr(new_obj, name, value_copy)
            elif name != 'llm':
                try:
                    setattr(new_obj, name, copy.deepcopy(value, memo))
                except Exception as e:
                    self.log("error", self, f"""Couldn't copy {name}, error: {e}""")
                    self.log("error", self, f"""Value: {value}""")
                    self.log("error", self, f"""Value type: {type(value)}""")
                    # print(f"""TMP Couldn't copy {name}, error: {e}""")
                    # print(f"""TMP Value: {value}""")
                    # print(f"""TMP Value type: {type(value)}""")

        new_obj.llm = type(self.llm)(api_key=self.llm.api_key,log_on=self.log_on)

        return new_obj



    def __str__(self):
        # Create a copy of the object's dictionary
        obj_dict = vars(self).copy()

        # Remove the 'macroflow' key from the copy
        obj_dict.pop('macroflow', None)

        # Serialize the copy
        return json.dumps(obj_dict, default=str)



    def mif_state_serialized(self):
        return json.dumps({
            "id": self.id,
            "name": self.name,
            "mif_status": self.mif_status,
            "data": self.data
        }, default=str)




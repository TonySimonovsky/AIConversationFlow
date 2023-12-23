import json
import copy
import time
import os
import inspect
import logging





class AIConversationFlow():


    def __init__(self, logs_folder="aiconversationflow_logs/"):
        self.__version__ = '0.0.4'
        self.logs_folder = logs_folder

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





class MacroFlow(AIConversationFlow):

    """

    Short: MAF

    """

    def __init__(self, system_prompt:str=None, state:dict=None):

        super().__init__()

        if not state:
            self.system_prompt = system_prompt
            self.messages = [{ "role": "system", "content": self.system_prompt }]
            self.status = "pending"
            self.just_finished_mif = False
            # current step
            self.cur_step = None
            # stack of MIF's, that defines their order
            self.steps = []
            # library of MIF's, to copy from
            self.miflib = {}

        else:
            self.system_prompt = state["system_prompt"]
            self.messages = state["messages"]
            self.status = state["status"]
            self.just_finished_mif = state["just_finished_mif"]
            # current step
            self.cur_step = state["cur_step"]
            # in serialized version, we are storing just the names of the mif's, so we need to convert from strings to the actual objects
            self.steps = [ self.miflib[step] for step in state["steps"] ]



    def prev_mif(self):
        if len(self.steps) > 2:
            return self.steps[-2]
        else:
            return None



    def cur_mif(self):
        return self.steps[-1]



    def __str__(self):
        """

        What we show when the object is used as a string.
        
        """

        return f"""\n\n
            MacroFlow Status: {self.status}\n
            Steps: {self.steps}\n
            Previous Microflow: {self.prev_mif()}\n
            Current: {self.cur_mif()}
            Just Finished MIF: {self.just_finished_mif}
        \n\n"""
    

    
    def register_microflow(self, microflow):
        """
        Method to add a MIF to MAF.
        """

        microflow.macroflow = self
        # add to the MIF library of MAF
        self.miflib[microflow.name] = microflow



    def add_step(self, step):
        """

        step: name of a MicroFlow()

        """
        
        # add to the stack
        self.steps.append(self.miflib[step].clone())



    def serialize(self):
        return json.dumps(vars(self), default=str)

    

    def run(self, user_message=None, state=None):
        """
        Method to run MAF, which orchestrates MIF's.
        """

        if state:
            self.log("info", self, f"Loading previous state")
            self.__init__(state=state)

        self.log("info", self, f"STARTED MAF run with user message '{user_message}'")

        if self.status == "pending":
            self.log("info", self, f"This is the initiation of the MAF")
            self.status = "in_progress"
        


        current_microflow = self.steps[-1]
        self.log("info", self, f"current_microflow: {current_microflow}")


        # if this was the last mif in the maf, so we are finishing the maf
        if current_microflow.status == "completed":
            ai_message = "Flow completed"
            self.status = "completed"

            self.log("info", self, f"""Last mif and MAF completed""")


        else:

            ai_message = current_microflow.run(user_message)

            if self.just_finished_mif:
                ai_message = None


        self.log("info", self, f"""RETURNING ai_message: {ai_message}""")

        return ai_message



class MicroFlow(AIConversationFlow):

    """

    Short: MIF

    """

    
    def __init__(self, name, llm, llm_params, system_prompt, start_with, completion_condition, next_steps, goodbye_message=None, callback=None, macroflow=None):
        super().__init__()
        
        self.id = time.time()
        self.name = name
        self.status = "pending"
        self.start_with = start_with
        self.macroflow = macroflow
        self.system_prompt = system_prompt
        self.completion_condition = completion_condition
        self.next_steps = next_steps
        self.goodbye_message = goodbye_message
        self.callback = callback
        self.llm = llm
        self.llm_params = llm_params
        self.goto = None
        self.data = {}




    def clone(self):
        cloned = copy.deepcopy(self)
        cloned.id = time.time()
        cloned.macroflow = self.macroflow
        return cloned



    def __deepcopy__(self, memo):
        # Create a new instance of the class including required params
        init_arg_names = inspect.getfullargspec(self.__init__).args[1:]  # Exclude 'self'
        new_obj = type(self)(**{k: v for k, v in vars(self).items() if k in init_arg_names})
        memo[id(self)] = new_obj

        # Copy all non-OpenAI attributes
        for name, value in self.__dict__.items():
            if name != 'llm':
                setattr(new_obj, name, copy.deepcopy(value, memo))

        # Create a 
        new_obj.llm = type(self.llm)()  

        return new_obj



    def __str__(self):
        return self.name



    def finish(self, goto=None):

        self.log("info", self, f"""START (mif {self.name}, status {self.status})""")

        self.status = "completed"
        self.macroflow.just_finished_mif = True

        # finalizing the flow
        if not goto:
            self.macroflow.status = "completed"

        # going to the next step
        else:
            self.macroflow.add_step(goto)
        
        return self.goodbye_message



    

    def run(self, user_message=None):
        """
        This orchestrates the MIF.
        """

        self.log("info", self, f"STARTING a run of {self.name} (status {self.status}, llm {self.llm.vendor})")
        self.log("info", self, f"INPUT: user_message: {user_message}")

        ai_message = None

        cbres = None
        if self.callback:
            cbres = self.callback()
            self.log("info", self, f"cbres: {cbres}")


        just_started = False

        if self.status == "pending":

            self.log("info", self, f"Initiating the mif {self.name}")

            sp = self.system_prompt
            if cbres:
                sp = sp.format(cbres=cbres)

            if self.macroflow.messages:
                self.macroflow.messages[0]["content"] = self.macroflow.system_prompt + sp

            if self.llm.requires_user_message and self.start_with != "user":
                self.macroflow.messages.append({ "role": "user", "content": "[ignore this message and continue following your instructions]" })


            self.status = "in_progress"
            self.macroflow.just_finished_mif = False
            just_started = True



        # if there is a user message but unless we are just starting
        if user_message and not (just_started and self.start_with == "AI"):

            self.macroflow.messages.append({ "role": "user", "content": user_message })

            # if the completion condition is first user's answer
            if self.completion_condition["type"] == "answer":

                self.sbs_logger.info(f"completion_condition: {self.completion_condition}")
                self.sbs_logger.info(f'self.completion_condition.get("details"): {self.completion_condition.get("details")}')

                if "details" in self.completion_condition:
                    if user_message.lower() in self.completion_condition["details"].keys():
                        self.sbs_logger.info(f"user_message: {user_message}, completion_condition: {self.completion_condition['details'].keys()}")
                        if self.completion_condition["details"][user_message.lower()].get("goto"):
                            next_step = self.completion_condition["details"][user_message.lower()]["goto"]
                            self.sbs_logger.info(f"ENDING a run of {self.name}, going to {next_step} (status {self.status}, llm {self.llm.vendor})")
                            return self.finish(goto=next_step)
                        else:
                            self.sbs_logger.info(f"ENDING a run of {self.name} (status {self.status}, llm {self.llm.vendor})")
                            return self.finish()

                elif len(self.next_steps)>0:
                    self.sbs_logger.info(f"! ENDING a run of {self.name}, going to {self.next_steps[0]} (status {self.status}, llm {self.llm.vendor})")

                    return self.finish(goto=self.next_steps[0])

                
                # print(f"next_step: {next_step}")

            # if the completion condition requires LLM reasoning
            elif self.completion_condition["type"] == "llm_reasoning":

                attempts = 5

                for i in range(attempts):
                    self.log("info", self, f'{i+1} attempt to get json-reasoning')

                    llm_reasoning_response = self.completion_condition["details"]["llm"].create_completion(
                        messages=[
                            {"role":"system","content":f"Here's the previous conversation with the Human (User):\n----\n{self.macroflow.messages}\n----\n\n"+self.completion_condition["details"]["system_prompt"]},
                        ],
                        llm_params=self.completion_condition["details"]["llm_params"]
                    )
                    try:
                        llm_reasoning = json.loads(llm_reasoning_response['choices'][0]['message']['content'])
                        self.log("info", self, f'Reasoning received: {llm_reasoning}')
                    except:
                        self.log("error", self, f"""Attempt failed because of the invalid json output: {llm_reasoning_response["choices"][0]["message"]["content"]}""")
                        continue

                    self.status = llm_reasoning["status"]
                    ai_message = llm_reasoning["comment"]
                    break

                if self.status == "completed":
                    next_step = None
                    if len(self.next_steps)>0:
                        next_step = self.next_steps[0]

                    return self.finish(goto=next_step)


        self.log("info", self, f"RETURNING ai_message: {ai_message}")

        ai_message = self.llm.create_completion(messages=self.macroflow.messages,llm_params=self.llm_params)['choices'][0]['message']['content']
        self.macroflow.messages.append({"role":"assistant","content":ai_message})

        self.log("info", self, f"RETURNING ai_message: {ai_message}")

        return ai_message


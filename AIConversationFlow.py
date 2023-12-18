from openai import OpenAI, APITimeoutError
import json
import copy
import threading
import logging
import time
import inspect



# Create a logger for step-by-step logs
sbs_logger = logging.getLogger('step_by_step')
sbs_logger.setLevel(logging.INFO)  # Or whatever level you want

# Remove all handlers associated with the logger object.
for handler in sbs_logger.handlers[:]:
    sbs_logger.removeHandler(handler)

# Create a file handler
sbs_handler = logging.FileHandler(f'logs/step_by_step.log')
sbs_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'))
sbs_logger.addHandler(sbs_handler)



__version__ = '0.0.2.1'






# class LLM():
#     """
#     2023.12.12: temp LLM wrapper
#     [ ] separate wrappers for different LLM's
#     """

#     openai_client = OpenAI()

#     def run(self, messages, llm_params):
#         try:
#             llm_response = self.openai_client.chat.completions.create(**llm_params, messages=messages)
#             llm_response = json.loads(llm_response.model_dump_json())
#         except APITimeoutError:
#             print("The function took too long to complete, so it was aborted.")
#             return
#         except Exception as e:
#             print(f"Some error when getting response from AI: {e}.\n\n")
#             return
        
#         return llm_response



class MacroFlow():

    """

    Short: MAF

    """

    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        self.messages = [{ "role": "system", "content": self.system_prompt }]
        self.status = "pending"
        self.previous_mif = None
        # self.current_mif = None
        self.next_mif = None
        self.just_finished_mif = False

        # current step
        self.cur_step = None

        # stack of MIF's, that defines their order
        self.steps = []
        # library of MIF's, to copy from
        self.miflib = {}



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

    

    def run(self, user_message=None):
        """
        Method to run MAF, which orchestrates MIF's.
        """

        sbs_logger.info("STARTED")


        if self.status == "pending":
            self.status = "in_progress"

        current_microflow = self.steps[-1]
        sbs_logger.info(f"Steps: {self.steps}")
        sbs_logger.info(f"current_microflow (type {type(current_microflow)}): {current_microflow}")


        # if this was the last mif in the maf, so we are finishing the maf
        if current_microflow.status == "completed":

            sbs_logger.info(f"Flow completed")

            ai_message = "Flow completed"
            self.status = "completed"

        else:
            sbs_logger.info(f"just_finished_mif before: {self.just_finished_mif}")

            ai_message = current_microflow.run(user_message)

            sbs_logger.info(f"just_finished_mif after: {self.just_finished_mif}")

            if self.just_finished_mif:
                ai_message = None

            # if current_microflow.status == "completed":
            #     ai_message = "Microflow completed"

        # # if no MIF was found (meaning we are done with the whole flow)
        # else:
        #     ai_message = "Flow completed"
        #     self.status = "completed"


        sbs_logger.info("FINISHED")
        sbs_logger.info(f"state: {self}")
        sbs_logger.info(f"return: ai_message: {ai_message}")

        sbs_logger.info(f"just_finished_mif end: {self.just_finished_mif}")

        return ai_message



class MicroFlow():

    """

    Short: MIF

    """

    
    def __init__(self, name, llm, llm_params, system_prompt, start_with, completion_condition, next_steps, goodbye_message=None, callback=None, macroflow=None):
        self.id = time.time()
        self.name = name
        self.status = "pending"
        self.start_with = start_with
        self.macroflow = macroflow
        self.system_prompt = system_prompt
        self.completion_condition = completion_condition
        self.next_mif = None
        self.next_steps = next_steps
        self.goodbye_message = goodbye_message
        self.callback = callback
        self.llm = llm
        self.llm_params = llm_params
        self.goto = None




    def clone(self):
        cloned = copy.deepcopy(self)
        cloned.id = time.time()
        cloned.macroflow = self.macroflow
        # print(f"Cloned: {cloned}")
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

        sbs_logger.info(f"Finishing the mif {self.name} (status {self.status})")

        self.status = "completed"
        self.macroflow.just_finished_mif = True

        # finalizing the flow
        if not goto:
            self.macroflow.status = "completed"

        # going to the next step
        else:
            self.macroflow.add_step(goto)
        
        return self.goodbye_message



    
    # def __str__(self):
    #     return f"{self.id} - {self.name} - {self.status}"
        


    def run(self, user_message=None):
        """
        This orchestrates the MIF.
        """

        sbs_logger.info(f"STARTING a run of {self.name} (status {self.status}, llm {self.llm.vendor})")

        cbres = None
        if self.callback:
            cbres = self.callback()

        sbs_logger.info(f"cbres: {cbres}")

        just_started = False

        if self.status == "pending":
            
            sp = self.system_prompt
            if cbres:
                sp = sp.format(cbres=cbres)

            sbs_logger.info(f"sp: {sp}")

            if self.macroflow.messages:
                self.macroflow.messages[0]["content"] += sp
            # self.macroflow.messages.append({ "role": "system", "content": sp })
            self.macroflow.messages.append({ "role": "user", "content": "hi" })

            sbs_logger.info(f"Current message history: {self.macroflow.messages}")

            self.status = "in_progress"
            # self.macroflow.current_mif = self
            self.macroflow.just_finished_mif = False
            just_started = True



        # if there is a user message but unless we are juststarting
        if user_message and not (just_started and self.start_with == "AI"):
        # if user_message and not self.start_with == "AI":

            self.macroflow.messages.append({ "role": "user", "content": user_message })

            sbs_logger.info(f"Current message history: {self.macroflow.messages}")

            # if the completion condition is first user's answer
            if self.completion_condition["type"] == "answer":

                sbs_logger.info(f"completion_condition: {self.completion_condition}")
                sbs_logger.info(f'self.completion_condition.get("details"): {self.completion_condition.get("details")}')

                if "details" in self.completion_condition:
                    if user_message.lower() in self.completion_condition["details"].keys():
                        sbs_logger.info(f"user_message: {user_message}, completion_condition: {self.completion_condition['details'].keys()}")
                        if self.completion_condition["details"][user_message.lower()].get("goto"):
                            next_step = self.completion_condition["details"][user_message.lower()]["goto"]
                            sbs_logger.info(f"ENDING a run of {self.name}, going to {next_step} (status {self.status}, llm {self.llm.vendor})")
                            return self.finish(goto=next_step)
                        else:
                            sbs_logger.info(f"ENDING a run of {self.name} (status {self.status}, llm {self.llm.vendor})")
                            return self.finish()

                elif len(self.next_steps)>0:
                    sbs_logger.info(f"! ENDING a run of {self.name}, going to {self.next_steps[0]} (status {self.status}, llm {self.llm.vendor})")

                    return self.finish(goto=self.next_steps[0])

                
                # print(f"next_step: {next_step}")

                

            

            # if the completion condition requires LLM reasoning
            if self.completion_condition["type"] == "llm_reasoning":

                attempts = 5

                for i in range(attempts):
                    sbs_logger.info(f'{i+1} attempt to get json-reasoning')

                    llm_reasoning_response = self.completion_condition["details"]["llm"].create_completion(
                        messages=[
                            {"role":"system","content":f"Here's the previous conversation with the Human (User):\n----\n{self.macroflow.messages}\n----\n\n"+self.completion_condition["details"]["system_prompt"]},
                            {"role": "user", "content": ""}
                        ],
                        llm_params=self.completion_condition["details"]["llm_params"]
                    )
                    try:
                        llm_reasoning = json.loads(llm_reasoning_response['choices'][0]['message']['content'])
                    except:
                        sbs_logger.info(f'Attemt failed because of the invalid json output: {llm_reasoning_response["choices"][0]["message"]["content"]}')
                        continue

                    self.status = llm_reasoning["status"]
                    ai_message = llm_reasoning["comment"]
                    break

                if self.status == "completed":
                    next_step = None
                    if len(self.next_steps)>0:
                        next_step = self.next_steps[0]

                    return self.finish(goto=next_step)
                
                return ai_message

        

        # print(f"\n\n\n{self.macroflow.messages}\n\n\n")
        ai_message = self.llm.create_completion(messages=self.macroflow.messages,llm_params=self.llm_params)['choices'][0]['message']['content']
        self.macroflow.messages.append({"role":"assistant","content":ai_message})

        return ai_message


from openai import OpenAI, APITimeoutError
import json
import copy
import logging
import time



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



__version__ = '0.0.2'






class LLM():
    """
    2023.12.12: temp LLM wrapper
    [ ] separate wrappers for different LLM's
    """

    openai_client = OpenAI()

    def run(self, messages, llm_params):
        try:
            llm_response = self.openai_client.chat.completions.create(**llm_params, messages=messages)
            llm_response = json.loads(llm_response.model_dump_json())
        except APITimeoutError:
            print("The function took too long to complete, so it was aborted.")
            return
        except Exception as e:
            print(f"Some error when getting response from AI: {e}.\n\n")
            return
        
        return llm_response



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




    

    def run(self, user_message=None):
        """
        Method to run MAF, which orchestrates MIF's.
        """

        sbs_logger.info("STARTED")


        if self.status == "pending":
            self.status = "in_progress"

        current_microflow = self.steps[-1]
        sbs_logger.info(f"Steps: {self.steps}")
        sbs_logger.info(f"current_microflow: {current_microflow}")


        if current_microflow.status == "completed":
            ai_message = "Flow completed"
            self.status = "completed"

        else:
            ai_message = current_microflow.run(user_message)
            # if current_microflow.status == "completed":
            #     ai_message = "Microflow completed"

        # # if no MIF was found (meaning we are done with the whole flow)
        # else:
        #     ai_message = "Flow completed"
        #     self.status = "completed"


        sbs_logger.info("FINISHED")
        sbs_logger.info(f"state: {self}")
        sbs_logger.info(f"return: ai_message: {ai_message}")


        return ai_message



class MicroFlow():

    """

    Short: MIF

    """

    llm = LLM()
    llm_params = {
        "model": "gpt-3.5-turbo",
        "temperature": 0,
        "timeout": 5
    }

    
    def __init__(self, name, system_prompt, start_with, completion_condition, next_steps, goodbye_message=None, macroflow=None):
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
        # self._initial_state = self._get_state()
        # here we set the name of the MIF we need to go to once current one has finished
        self.goto = None





    def clone(self):
        cloned = copy.deepcopy(self)
        cloned.id = time.time()
        cloned.macroflow = self.macroflow
        # print(f"Cloned: {cloned}")
        return cloned

    # def _get_state(self):
    #     return copy.deepcopy({attr: getattr(self, attr) for attr in vars(self)})


    # def reset_to_initial_state(self):
    #     for attr, value in self._initial_state.items():
    #         setattr(self, attr, value)


    def finish(self, goto=None):
        self.status = "completed"
        self.macroflow.just_finished_mif = True

        # print(f"steps before: {self.macroflow.steps}")

        # finalizing the flow
        if not goto:
            self.macroflow.status = "completed"

        # going to the next step
        else:
            self.macroflow.add_step(goto)
        
        return self.goodbye_message

        # print(f"steps after: {self.macroflow.steps}")

        # self.macroflow.previous_mif(self)
        # self.macroflow.previous_mif = self
        # self.macroflow.just_finished_mif = True

        # if go_to:
            
        #     self.macroflow.current_mif = self.macroflow.next_mif
        # else:
        #     self.macroflow.current_mif = self.macroflow.next_mif

        # # if not self.next_mif:
        # #     self.macroflow.status = "completed"


    
    def __str__(self):
        return f"{self.id} - {self.name} - {self.status}"
        


    def run(self, user_message=None):
        """
        This orchestrates the MIF.
        """

        # print(f"MACROFLOW FROM INSIDE MIF: {self.macroflow}")

        if self.status == "pending":
            self.macroflow.messages.append({ "role": "system", "content": self.system_prompt })
            self.status = "in_progress"
            # self.macroflow.current_mif = self
            self.macroflow.just_finished_mif = False


        if user_message and not (self.macroflow.just_finished_mif and self.start_with == "AI"):
            self.macroflow.messages.append({ "role": "user", "content": user_message })
        
            # if the completion condition is first user's answer
            if self.completion_condition["type"] == "answer":

                if self.completion_condition.get("details"):
                    if user_message.lower() in self.completion_condition["details"].keys():
                        if self.completion_condition["details"][user_message.lower()].get("goto"):
                            next_step = self.completion_condition["details"][user_message.lower()]["goto"]
                            return self.finish(goto=next_step)
                        else:
                            return self.finish()

                if len(self.next_steps)>0:
                    return self.finish(goto=self.next_steps[0])

                
                # print(f"next_step: {next_step}")

                

            

            # if the completion condition requires LLM reasoning
            if self.completion_condition["type"] == "llm_reasoning":
                
                llm_reasoning_response = self.llm.run(messages=[{"role":"system","content":f"Here's the previous conversation with the Human (User):\n----\n{self.macroflow.messages}\n----\n\n"+self.completion_condition["details"]["system_prompt"]}],llm_params=self.completion_condition["details"]["llm_params"])
                llm_reasoning = json.loads(llm_reasoning_response['choices'][0]['message']['content'])
                # print(llm_reasoning)
                self.status = llm_reasoning["status"]
                ai_message = llm_reasoning["comment"]

                if self.status == "completed":
                    next_step = None
                    if len(self.next_steps)>0:
                        next_step = self.next_steps[0]

                    self.finish(goto=next_step)
                
                return ai_message

        
        # print(f"\n\n\n{self.macroflow.messages}\n\n\n")
        ai_message = self.llm.run(messages=self.macroflow.messages,llm_params=self.llm_params)['choices'][0]['message']['content']
        self.macroflow.messages.append({"role":"assistant","content":ai_message})

        return ai_message


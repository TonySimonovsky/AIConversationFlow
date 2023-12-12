from openai import OpenAI, APITimeoutError
import json



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
        self.microflows = []
        self.status = "pending"
        self.previous_mif = None
        self.current_mif = None
        self.next_mif = None
        self.just_finished_mif = False

    

    def __str__(self):
        """
        What we show when the object is used as a string.
        """
        return f"\n\nMacroFlow Status: {self.status}\nPrevious Microflow: {self.previous_mif}\nCurrent: {self.current_mif}\nNext: {self.next_mif}\n\n"
    
    
    def add_microflow(self, microflow):
        """
        Method to add a MIF to MAF.
        """
        self.microflows.append(microflow)
        microflow.macroflow = self

    
    def run(self, user_message=None):
        """
        Method to run MAF, which orchestrates MIF's.
        """
        if self.status == "pending":
            self.status = "in_progress"

        current_microflow = None

        # looking for the first un-completed MIF in the stack
        while not current_microflow:
            for i, mif in enumerate(self.microflows):
                # print(mif)
                if mif.status != "completed":
                    current_microflow = mif
                    # print(f"i: {i}")
                    # print(f"microflows len: {len(self.microflows)}")
                    # print(f"microflows: {self.microflows}")
                    if len(self.microflows)>=(i+2):
                        current_microflow.next_mif = self.next_mif = self.microflows[i+1]
                    else:
                        current_microflow.next_mif = self.next_mif = None
                    break

        # if a MIF was found
        if current_microflow:
            ai_message = current_microflow.run(user_message)
            # if current_microflow.status == "completed":
            #     ai_message = "Microflow completed"

        # if no MIF was found (meaning we are done with the whole flow)
        else:
            ai_message = "Flow completed"
            self.status = "completed"
        
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

    
    def __init__(self, name, system_prompt, start_with, completion_condition, macroflow=None):
        self.name = name
        self.status = "pending"
        self.start_with = start_with
        self.macroflow = macroflow
        self.system_prompt = system_prompt
        self.completion_condition = completion_condition
        self.next_mif = None


    def finish(self):
        self.status = "completed"
        
        self.macroflow.previous_mif = self
        self.macroflow.current_mif = self.macroflow.next_mif
        self.macroflow.just_finished_mif = True

        if not self.next_mif:
            self.macroflow.status = "completed"


    
    def __str__(self):
        return f"{self.name} - {self.status}"
        


    def run(self, user_message=None):
        """
        This orchestrates the MIF.
        """

        if self.status == "pending":
            self.macroflow.messages.append({ "role": "system", "content": self.system_prompt })
            self.status = "in_progress"
            self.macroflow.current_mif = self
            self.macroflow.just_finished_mif = False


        if user_message and not (self.macroflow.just_finished_mif and self.start_with == "AI"):
            self.macroflow.messages.append({ "role": "user", "content": user_message })
        
            # if the completion condition is first user's answer
            if self.completion_condition["type"] == "answer":
                self.finish()
                ai_message = "Thank you!"
                return ai_message

            # if the completion condition requires LLM reasoning
            if self.completion_condition["type"] == "llm_reasoning":
                
                llm_reasoning_response = self.llm.run(messages=[{"role":"system","content":f"Here's the previous conversation with the Human (User):\n----\n{self.macroflow.messages}\n----\n\n"+self.completion_condition["details"]["system_prompt"]}],llm_params=self.completion_condition["details"]["llm_params"])
                llm_reasoning = json.loads(llm_reasoning_response['choices'][0]['message']['content'])
                # print(llm_reasoning)
                self.status = llm_reasoning["status"]
                ai_message = llm_reasoning["comment"]

                if self.status == "completed":
                    self.finish()
                
                return ai_message

        
        ai_message = self.llm.run(messages=self.macroflow.messages,llm_params=self.llm_params)['choices'][0]['message']['content']

        return ai_message


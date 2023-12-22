# AI Conversation Flow Library
Current Version: 0.0.3. A very early version, for presentation purposes. Use at your own risk.

This library provides a framework for managing conversation flows with LLM's, that are composable, controllable and easily testable.


## Inspiration

The idea for this library came from the challenges faced while working on complex and non-linear communication scenarios for several client projects. An example scenario could be a tech interview where the user has the option to ask clarifying questions or answer the main question, with each option potentially involving multiple back-and-forth messages.

Initial attempts to handle these scenarios involved using a single prompt to guide the entire conversation, or breaking the conversation into several stages with separate prompts. However, these approaches had limitations, such as difficulty transitioning between stages and the AI model focusing too much on outputting JSON status information.

The solution was to create an abstraction layer for managing conversation flows, where complex flows can be built using composable, controllable, and easily testable micro-flows. This approach offloads part of the logic from the AI to the application, making it easier to manage the conversation and transition between stages.

## Classes

### MacroFlow

This class represents a high-level conversation flow. It maintains a list of MicroFlows, which are executed in order. The `run` method executes the next pending MicroFlow and returns the AI's response.

### MicroFlow

This class represents a lower-level conversation flow. It has a `run` method that sends a message to the AI and returns its response. The flow can be marked as completed based on certain conditions. The `finish` method allows the flow to transition to any other MicroFlow, including the current one.

Completion Conditions

The `MicroFlow` class supports two types of completion conditions:

1. **Answer**: The MicroFlow is marked as completed when the user provides an answer. This is specified with `completion_condition={"type":"answer"}`.

2. **LLM Reasoning**: The MicroFlow uses another instance of LLM to determine whether it's completed. This is specified with `completion_condition={"type":"llm_reasoning", "details": {...}}`. The `details` dictionary should include a `system_prompt` for the LLM and `llm_params` specifying the parameters for the LLM call.

### LLM

This class is a wrapper for the OpenAI API. It provides a method `run` to send a list of messages to the API and receive a response.

## Usage

First, create an instance of the MacroFlow class with a system prompt:

```
macroflow = MacroFlow("You are an interviewer, collecting information from the Human (User). Collect the data mentioned below from the Human.")
```

Then, build the flow from steps:

```
# Now, build the flow from steps

# Initializing the MicroFlow
microflow_collect_info_job = MicroFlow(
    name="collect_info_job",
    # this indicates who starts the microflow: User or AI
    start_with="AI",
    # this system prompt will be added to the MacroFlow communication messages once thsi MicroFlow starts
    system_prompt="Collect information about the Human's job.",
    # here we indicate the microflow completion condition as the first user's message
    completion_condition={
        "type":"answer"
    },
    next_steps=["collect_info_hobbies"],
    goodbye_message="Thank you!"
)
# Adding the MicroFlow to the MacroFlow library
macroflow.register_microflow(microflow_collect_info_job)

# Initializing another MicroFlow
microflow_collect_info_hobbies = MicroFlow(
    name="collect_info_hobbies",
    start_with="AI",
    system_prompt="Collect information about the person's hobbies. If they are hesitant to share, collect information about what they would love to do as a hobby.",
    # here we have a different type of completion condition:
    #   we want another instance of LLM to reason if the MicroFlow was completed or not
    #   the system prompt will be executed together with the message history
    #   the his type of completion condition requires that we are requesting the model to output
    #   a valid JSON with 2 required fields: 'status', 'comment'
    completion_condition={
        "type": "llm_reasoning",
        "details": {
            "system_prompt": """
                Only answer in valid json format with the following fields:
                - 'hobbies' (list of hobbies the user already shared),
                - 'status', the only possible values:
                    - 'in_progress' until the user collectively provided 3+ hobbies
                    - 'completed' when the Human (User) provided 3+ hobbies
                - 'comment' (your comment to the Human).
            """,
            "llm_params": llm_params_gpt35turbo1106json
        }
    },
    next_steps=["propose_new_hobby"]
)
macroflow.register_microflow(microflow_collect_info_hobbies)

microflow_propose_new_hobby = MicroFlow(
    name="propose_new_hobby",
    start_with="AI",
    system_prompt="""Based on your knowledge about the Human propose new hobbies, one at a time and ask if the person wants another recommedation (instruction for the Human: "answer 'yes' if you want another one, otherwise - 'no'").""",
    completion_condition={
        "type": "answer",
        # another variation of "answer" completion condition
        #   here, we define specific user answers we are monitoring
        #   and different statuses we'll set to the microflow depending on the answer
        #   for the "completed" status we also set the name of the microstep we'll go to
        #   notice how "yes" will trigger another instance of the same step,
        #   while "no" finalizes the flow
        "details": {
            "yes": { "goto": "propose_new_hobby" },
            "no": {  }
        }
    },
    next_steps=["propose_new_hobby","completed"]
)
macroflow.register_microflow(microflow_propose_new_hobby)

# add the step, we'll start our flow with
macroflow.add_step("collect_info_job")
```

Finally, here's a how integration into a front-end would look like (this one is for Jupyter, but you can easily tweak it to use in a real front-end):

```
user_message = None

while 1:
    
    ai_message = macroflow.run(user_message=user_message)

    if macroflow.status == "completed":
        break

    if ai_message:
        print(f"AI: {ai_message}\n")

    # if we just finished previous microflow and the next starts with AI
    if macroflow.just_finished_mif and macroflow.cur_mif().start_with == "AI":
        user_message = None
        continue

    print(f"User:")
    user_message = input()
    print(f"\n")

```

And here's an example of a conversation using the flow above:

> AI: Can you please provide me with information about your current job?
>
> User:
>  I'm a developer
> 
> AI: Thank you!
> 
> AI: What are your hobbies or what would you love to do as a hobby?
> 
> User:
>  hockey
> 
> AI: Great! I see you enjoy hockey. Do you have any other hobbies you'd like to share?
> 
> User:
>  diving
> 
> AI: Great! You've shared two hobbies so far. Can you share one more hobby or interest?
> 
> User:
>  hiking

As you can see, the first MicroFlow only required me to answer, while the second one didn't finish before it collected 3 hobbies from me.

## Video Demo's

The Very First Demo: https://www.loom.com/share/60e0a2f4d6fc47a792f7ec633ad1f8ea

Grumpy CTO quest game: https://www.loom.com/share/5476267a38c4457a873c0e21ded1e709

## Requirements

This library requires the openai Python package. Install it with:

```pip install openai```

## Note

This library is a work in progress and may not handle all possible conversation flows or error conditions. It's recommended to use it as a starting point and customize it to fit your specific needs.

## Changelog

### Version 0.0.3 - 2023-12-22
- Made AIConversationFlow stateful. Now it can be integrated into apps frontends and continue conversations between sessions

### Version 0.0.2.1 - 2023-12-13
- Added very simple functionality to use callbacks in the MicroFlow's.

### Version 0.0.2 - 2023-12-13
- Added the ability to freely transition to any MicroFlow, including the current one, after finishing the current MicroFlow.
- Introduced a new completion condition for MicroFlows.
- Improved the management of the stack of MicroFlows.

### Version 0.0.1 - 2023-12-12
- Initial release of the AI Conversation Flow Library. 

## Roadmap

- Come up with the data format so that the states of the flows can be saved
- Architectureal update: A MAF consists of steps. A step may be a MIF or another MAF.
- Add support for async
- Add support for additional AI models.
- Improve error handling and add more descriptive error messages.
- Implement a GUI for easier testing.

## Contact

For any questions or concerns, please reach out to:

Email: tony@aicha.mp

Telegram: @TonySimonovsky

# AI Conversation Flow Library
Current Version: 0.01. The very first draft version, for presentation purposes. Use at your own risk.

This library provides a framework for managing conversation flows with LLM's, that are composable, controllable and easily testable.


## Inspiration

The idea for this library came from the challenges faced while working on complex and non-linear communication scenarios for several client projects. An example scenario could be a tech interview where the user has the option to ask clarifying questions or answer the main question, with each option potentially involving multiple back-and-forth messages.

Initial attempts to handle these scenarios involved using a single prompt to guide the entire conversation, or breaking the conversation into several stages with separate prompts. However, these approaches had limitations, such as difficulty transitioning between stages and the AI model focusing too much on outputting JSON status information.

The solution was to create an abstraction layer for managing conversation flows, where complex flows can be built using composable, controllable, and easily testable micro-flows. This approach offloads part of the logic from the AI to the application, making it easier to manage the conversation and transition between stages.

## Classes

### LLM

This class is a wrapper for the OpenAI API. It provides a method `run` to send a list of messages to the API and receive a response.

### MacroFlow

This class represents a high-level conversation flow. It maintains a list of MicroFlows, which are executed in order. The `run` method executes the next pending MicroFlow and returns the AI's response.

### MicroFlow

This class represents a lower-level conversation flow. It has a `run` method that sends a message to the AI and returns its response. The flow can be marked as completed based on certain conditions.

## Usage

First, create an instance of the MacroFlow class with a system prompt:

```
macroflow = MacroFlow("You are an interviewer, collecting information from the Human (User). Collect the data mentioned below from the Human.")
```

Then, build the flow from steps:

```
# Initializing the MicroFlow
microflow_collect_info_job = MicroFlow(
    name="collect_info_job",
    # this indicates who starts the microflow: User or AI
    start_with="AI",
    # this system prompt will be added to the MacroFlow communication messages once thsi MicroFlow starts
    system_prompt="Collect information about the Human's job.",
    # here we indicate the microflow completion condition as the first user's message
    completion_condition={"type":"answer"}
)

# Adding the MicroFlow to the MacroFlow
macroflow.add_microflow(microflow_collect_info_job)

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
    }
)
macroflow.add_microflow(microflow_collect_info_hobbies)
```

Finally, here's a how integration into a front-end would look like (this one is for Jupyter, but you can easily tweak it to use in a real front-end):

```
# simple integration of the flow into a front-end 

user_message = None
while 1:
    ai_message = macroflow.run(user_message=user_message)
    if macroflow.status == "completed":
        break

    print(f"AI: {ai_message}\n")

    if not macroflow.current_mif:
        break

    # if we just finished previous microflow and the next starts with AI
    if macroflow.just_finished_mif and macroflow.current_mif.start_with == "AI":
        user_message = None
        continue

    print(f"User:")
    user_message = input()
    print(f"\n")
```

And here's what it would output:

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

## Requirements

This library requires the openai Python package. Install it with:

```pip install openai```

## Note

This library is a work in progress and may not handle all possible conversation flows or error conditions. It's recommended to use it as a starting point and customize it to fit your specific needs.

## Changelog

### Version 0.01 - 2023-12-12
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

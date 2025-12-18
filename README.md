
### AI HACK

 In this repository, there is a file called `merged_all`. It includes all necessary files in this project, along with this README.
 If you provide this file to your own AI and ask it to analyze the contents, the AI can guide you through the entire framework. It takes very little time for it to fully comprehend NexusArbiter.

### NexusArbiter — Compiled Creativity

NexusArbiter is a file-based, deterministic multi-agent framework. By design, it is:

* **Reproducible**
* **Auditable**
* **Predictable**
* **Configurable**

It proposes a structured and explicit way to interact with AI agents, making it an ideal candidate for real-world and enterprise use cases.

## Requirements

* **Python 3.10** or newer
* A valid **API key** for a supported provider (OpenAI or Gemini)
* Windows, macOS, or Linux

## HOW TO USE IT??

* **Step 1**
* Install python dependencies:
python -m pip install --upgrade pip
pip install -r requirements.txt

* **Step 2**
Ready your OPENAI-KEY
https://platform.openai.com/docs/quickstart

Export an environment variable on macOS or Linux systems
On the terminal:

export OPENAI_API_KEY="your_api_key_here"

For Windows:
Create a blank .env file, then create below line 
OPENAI_API_KEY=PASTEYOURKEYHERE

* **Step 3**
Run NexusArbiter: 
In the root folder, where you have cli.py exists, in the terminal, write:
run /example/template/template_run.json

This will start your example workflow. Which on default tasked to generate a Library Manager application.
If you want to change the task, please go to that json and edit the first task description.  

* **THATS IT** 

As your run goes on, you can read the architecture of NexusArbiter. 

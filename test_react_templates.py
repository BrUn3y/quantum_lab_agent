"""Test to understand ReActAgent template structure"""
import os
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import ChatModel
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.template import PromptTemplate

# Create a simple agent
llm = ChatModel.from_name("watsonx:mistralai/mistral-small-3-1-24b-instruct-2503")
agent = ReActAgent(
    llm=llm,
    tools=[],
    memory=UnconstrainedMemory(),
)

# Check what templates are available
print("Agent attributes:")
for attr in dir(agent):
    if not attr.startswith('_'):
        print(f"  {attr}")

# Check if there's a way to set system instructions
import inspect
print("\nReActAgent.run signature:")
sig = inspect.signature(agent.run)
for name, param in sig.parameters.items():
    print(f"  {name}: {param.annotation}")

# Made with Bob

from src.gig_investigator.investigator import GigInvestigator
"""
Dummy AI Band Manager agent using LangChain.
"""

from langchain.llms import OpenAI
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from dotenv import load_dotenv
load_dotenv()


def dummy_band_manager():
	# Dummy tool for demonstration
	def say_hello_tool(input_text: str) -> str:
		return f"Hello from the AI Band Manager! You said: {input_text}"

	tools = [
		Tool(
			name="SayHello",
			func=say_hello_tool,
			description="Replies with a greeting and echoes the input."
		)
	]

	llm = OpenAI(temperature=0)
	agent = initialize_agent(
		tools,
		llm,
		agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
		verbose=True
	)
	return agent

if __name__ == "__main__":
	import sys
	investigator = GigInvestigator()
	if len(sys.argv) > 1 and sys.argv[1] == "clean":
		# Only run the cleaning step
		GigInvestigator.clean_gig_opportunities()
	else:
		# Run the autonomous gig investigation and save results to CSV
		investigator.investigate_and_save()
	# investigator.investigate_and_save()


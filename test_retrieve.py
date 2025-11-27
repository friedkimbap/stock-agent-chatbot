from strands.agent.agent import Agent
import os
import sys
from dotenv import load_dotenv
from strands_tools import retrieve

def test_retrieve():
    """
    Test the retrieve tool functionality independently.
    """
    # Set stdout to utf-8
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    # Load environment variables from .env file
    load_dotenv()
    
    # Check for KNOWLEDGE_BASE_ID
    kb_id = os.environ.get("KNOWLEDGE_BASE_ID")
    if not kb_id:
        print("❌ Error: KNOWLEDGE_BASE_ID environment variable is not set.")
        print("Please ensure your .env file contains KNOWLEDGE_BASE_ID.")
        return

    print(f"✅ Found Knowledge Base ID: {kb_id}")


    # If it is a module, try to find a callable inside it
    if hasattr(retrieve, 'retrieve'):
            
        test_agent = Agent(
                model="us.amazon.nova-lite-v1:0",
                system_prompt="오토데스크에 관한 정보를 retrieve 툴을 사용하여 찾아주세요",
                tools=[retrieve]
            )
        response = test_agent("오토데스크에 대한 정보를 찾아주세요")
        print("\n📄 Result:")
        print(response)

    elif callable(retrieve):
        print("retrieve object is callable. Trying to call it.")
        test_agent = Agent(
            model="us.amazon.nova-lite-v1:0",
            system_prompt="오토데스크에 관한 정보를 retrieve 툴을 사용하여 찾아주세요",
            tools=[retrieve]
        )
        result = test_agent("오토데스크에 대한 정보를 찾아주세요")
        print("\n📄 Result:")
        print(result)
    else:
        print("retrieve is not callable and does not have a 'retrieve' attribute.")

if __name__ == "__main__":
    test_retrieve()

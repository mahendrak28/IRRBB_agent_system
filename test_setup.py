import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import pandas as pd
import numpy as np

# Load environment variables
load_dotenv()

def test_basic_imports():
    """Test if all libraries are installed"""
    print("✓ Pandas version:", pd.__version__)
    print("✓ Numpy version:", np.__version__)
    print("✓ All basic imports successful!")
    return True

def test_ai_connection():
    """Test if AI API is working"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("\n✗ No API key found in .env file!")
            print("Make sure you added OPENAI_API_KEY=your-key to .env")
            return False
            
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0
        )
        
        response = llm.invoke([
            HumanMessage(content="Say 'AI setup successful! Ready to build financial agents.' and nothing else")
        ])
        
        print(f"\n✓ AI Response: {response.content}")
        print("\n💰 API Cost: ~$0.0001 (basically free)")
        return True
    except Exception as e:
        print(f"\n✗ AI Connection failed: {e}")
        print("\nCommon fixes:")
        print("1. Check your API key in .env file")
        print("2. Make sure you added $5 credit to OpenAI account")
        print("3. Verify API key is active at platform.openai.com")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🔧 TESTING YOUR SETUP")
    print("="*60)
    
    all_pass = True
    
    print("\n1️⃣ Testing Basic Libraries...")
    all_pass = test_basic_imports() and all_pass
    
    print("\n2️⃣ Testing AI Connection (OpenAI GPT-4)...")
    all_pass = test_ai_connection() and all_pass
    
    print("\n" + "="*60)
    if all_pass:
        print("✅ ALL TESTS PASSED! YOU'RE READY TO BUILD!")
        print("="*60)
        print("\n🚀 Next: We'll create your first AI financial agent!")
    else:
        print("❌ SOME TESTS FAILED - SEE ERRORS ABOVE")
        print("="*60)
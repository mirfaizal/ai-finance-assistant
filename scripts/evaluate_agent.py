#!/usr/bin/env python
"""
Agent Evaluation Script

This script evaluates the AI Finance Assistant agents using LangSmith QA evaluators.
It defines a small test dataset, creates it in LangSmith, runs the agents against the queries,
and uses an LLM to grade the responses based on correctness and relevance against a reference answer.

Usage:
    export LANGCHAIN_API_KEY="..."
    export OPENAI_API_KEY="..."
    export LANGCHAIN_TRACING_V2="true"
    python scripts/evaluate_agent.py
"""

import os
import sys
import uuid
from dotenv import load_dotenv

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langsmith import Client, evaluate
from langchain_openai import ChatOpenAI

# Import the orchestrator's process_query function which is used by the web app
from src.workflow.orchestrator import process_query

def target_function(inputs: dict) -> dict:
    """
    Wrap the agent's process_query function to match LangSmith's expected target interface.
    """
    question = inputs["question"]
    session_id = str(uuid.uuid4())  # Fresh session for each eval query
    
    print(f"\n[EVAL] Running query: {question}")
    # Call the agent
    response = process_query(question=question, session_id=session_id)
    
    # Return the answer dict. We extract just the "answer" string for the evaluator.
    return {
        "output": response["answer"],
        "agent_used": response["agent"]
    }

def main():
    load_dotenv()
    
    if not os.environ.get("LANGCHAIN_API_KEY") or not os.environ.get("OPENAI_API_KEY"):
        print("Error: LANGCHAIN_API_KEY and OPENAI_API_KEY must be set in the environment or .env file.")
        sys.exit(1)
        
    client = Client()
    
    dataset_name = "Finance_Assistant_Eval_v1"
    
    # Define our evaluation examples (question + reference answer)
    examples = [
        (
            "What is a Roth IRA?",
            "A Roth IRA is an individual retirement account that allows you to contribute after-tax money, and your money grows tax-free. Withdrawals in retirement are also tax-free."
        ),
        (
            "What does P/E ratio mean?",
            "The Price-to-Earnings (P/E) ratio is a valuation metric that compares a company's current stock price to its per-share earnings."
        ),
        (
            "Should I invest everything in a single stock?",
            "No, investing everything in a single stock carries high risk. It is generally recommended to diversify your portfolio across different assets to reduce risk."
        ),
        (
            "What is the difference between a stock and a bond?",
            "A stock represents equity or ownership in a company, meaning you share in its profits and losses. A bond is a debt instrument where you lend money to an entity (corporate or government) in exchange for regular interest payments and the return of principal at maturity."
        ),
        (
            "If the Fed raises interest rates, what generally happens to bond prices?",
            "As interest rates rise, the prices of existing bonds generally fall. This happens because new bonds are issued with higher yields, making older bonds with lower yields less attractive."
        )
    ]
    
    print(f"Checking if dataset '{dataset_name}' exists...")
    if not client.has_dataset(dataset_name=dataset_name):
        print(f"Creating dataset '{dataset_name}'...")
        # Create dataset
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Evaluation dataset for the AI Finance Assistant agents to measure basic finance knowledge correctness."
        )
        # Upload examples
        for q, a in examples:
            client.create_example(
                inputs={"question": q},
                outputs={"expected_answer": a},
                dataset_id=dataset.id
            )
        print("Dataset created successfully.")
    else:
        print(f"Dataset '{dataset_name}' already exists. Reusing it.")
    
    # Set up evaluator using an LLM to judge "correctness" (QA evaluation)
    # The 'qa' evaluator compares the prediction ('output') against the reference ('expected_answer') 
    # to measure if they convey the same analytical correctness.
    eval_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    
    print(f"\nStarting evaluation against dataset: {dataset_name}...")
    
    def ls_qa_evaluator(run, example) -> dict:
        prediction = run.outputs.get("output", "")
        reference = example.outputs.get("expected_answer", "")
        question = example.inputs.get("question", "")
        
        prompt = f"""You are an expert financial evaluator.
Given the user's question, the reference correct answer, and the agent's actual predicted answer, evaluate if the predicted answer is correct and conveys the same analytical truth as the reference answer.
Your response MUST start with either "SCORE: 1" for correct or "SCORE: 0" for incorrect, followed by your reasoning.

QUESTION: {question}
REFERENCE ANSWER: {reference}
PREDICTED ANSWER: {prediction}
"""
        try:
            response = eval_llm.invoke(prompt)
            content = response.content
            score = 1.0 if "SCORE: 1" in content else 0.0
            return {"key": "qa_score", "score": score, "comment": content}
        except Exception as e:
            return {"key": "qa_score", "score": 0.0, "comment": f"Eval failed: {e}"}

    try:
        experiment_results = evaluate(
            target_function,
            data=dataset_name,
            evaluators=[ls_qa_evaluator],
            experiment_prefix="Finance_Agent_Eval_",
            metadata={"version": "1.0", "agent_type": "orchestrator"}
        )
        print("\nEvaluation kicked off successfully!")
        print("You can view the live progress and detailed results in LangSmith.")
    except Exception as e:
        print(f"Evaluation failed: {e}")

if __name__ == "__main__":
    main()

"""
Phoenix Evaluation Script for P&ID Assistant

Evaluates the RAG pipeline using Arize Phoenix with:
- Relevance: Are retrieved chunks relevant to the query?
- QA Correctness: Is the answer correct given the context?
- Hallucination: Does the answer contain info not in context?

Usage:
    # Start Phoenix server first (in separate terminal)
    phoenix serve

    # Run evaluation
    python scripts/eval_phoenix.py

    # View results at http://localhost:6006
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Check for Phoenix
try:
    import phoenix as px
    from phoenix.evals import (
        HallucinationEvaluator,
        QAEvaluator,
        RelevanceEvaluator,
        run_evals,
    )
    from phoenix.evals.models import OpenAIModel, LiteLLMModel
    from phoenix.trace import SpanEvaluations
    import pandas as pd
    PHOENIX_AVAILABLE = True
except ImportError as e:
    PHOENIX_AVAILABLE = False
    print(f"Phoenix not available: {e}")
    print("Install with: pip install arize-phoenix")

# Application imports
from app.rag_engine import RAGEngine
from app.phoenix_tracer import init_tracing


class PhoenixEvaluator:
    """Evaluates RAG pipeline using Phoenix metrics"""

    def __init__(self, dataset_path: str = "tests/eval_dataset.json"):
        self.dataset_path = Path(dataset_path)
        self.rag_engine = None
        self.test_cases = []
        self.results = []
        self.eval_model = None

        print("=" * 60)
        print("  Phoenix Evaluation for P&ID Assistant")
        print("=" * 60)
        print()

    def load_dataset(self) -> bool:
        """Load test cases from JSON file"""
        if not self.dataset_path.exists():
            print(f"Error: Dataset not found at {self.dataset_path}")
            return False

        with open(self.dataset_path, 'r') as f:
            data = json.load(f)

        self.test_cases = data.get('test_cases', [])
        print(f"Loaded {len(self.test_cases)} test cases")
        print(f"Categories: {set(tc['category'] for tc in self.test_cases)}")
        print()
        return True

    def initialize_rag(self) -> bool:
        """Initialize RAG engine with tracing"""
        try:
            # Initialize tracing for this evaluation
            init_tracing(project_name="pid-assistant-eval")

            print("Initializing RAG Engine...")
            self.rag_engine = RAGEngine()
            return True
        except Exception as e:
            print(f"Error initializing RAG engine: {e}")
            return False

    def initialize_eval_model(self) -> bool:
        """Initialize the model used for evaluation judgments"""
        try:
            # Use OpenAI for evaluation (more reliable for judgments)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.eval_model = OpenAIModel(model="gpt-4o-mini")
                print("Using OpenAI gpt-4o-mini for evaluation judgments")
            else:
                # Fallback to LiteLLM with Gemini
                self.eval_model = LiteLLMModel(model="gemini/gemini-1.5-flash")
                print("Using Gemini for evaluation judgments")
            return True
        except Exception as e:
            print(f"Error initializing eval model: {e}")
            return False

    def run_queries(self) -> List[Dict]:
        """Run all test queries through RAG pipeline"""
        print("Running test queries...")
        print("-" * 40)

        results = []
        for i, tc in enumerate(self.test_cases, 1):
            question = tc['question']
            ground_truth = tc['ground_truth']

            print(f"[{i}/{len(self.test_cases)}] {question[:50]}...")

            try:
                # Query RAG engine
                answer, metadata = self.rag_engine.query_rag(question, top_k=3)

                # Get contexts from search
                query_embedding = self.rag_engine.generate_query_embedding(question)
                search_results = self.rag_engine.search_vector_db(query_embedding, top_k=3)
                contexts = [r['text'] for r in search_results]

                results.append({
                    'id': tc['id'],
                    'question': question,
                    'answer': answer,
                    'contexts': contexts,
                    'context_str': "\n\n".join(contexts),  # For Phoenix
                    'ground_truth': ground_truth,
                    'reference': ground_truth,  # Alias for Phoenix
                    'category': tc['category'],
                    'relevance_scores': metadata.get('relevance_scores', [])
                })

            except Exception as e:
                print(f"   Error: {e}")
                results.append({
                    'id': tc['id'],
                    'question': question,
                    'answer': f"Error: {e}",
                    'contexts': [],
                    'context_str': "",
                    'ground_truth': ground_truth,
                    'reference': ground_truth,
                    'category': tc['category'],
                    'relevance_scores': []
                })

        print("-" * 40)
        print(f"Completed {len(results)} queries")
        print()

        self.results = results
        return results

    def evaluate_with_phoenix(self) -> Dict:
        """Evaluate results using Phoenix evaluators"""
        if not PHOENIX_AVAILABLE:
            print("Phoenix not available. Install with: pip install arize-phoenix")
            return self._basic_evaluation()

        if not self.eval_model:
            if not self.initialize_eval_model():
                return self._basic_evaluation()

        print("Evaluating with Phoenix...")
        print("-" * 40)

        # Create DataFrame for Phoenix
        df = pd.DataFrame(self.results)

        # Rename columns for Phoenix compatibility
        df = df.rename(columns={
            'question': 'input',
            'answer': 'output',
            'context_str': 'reference'
        })

        scores = {}

        try:
            # 1. Relevance Evaluation
            print("Running Relevance evaluation...")
            relevance_evaluator = RelevanceEvaluator(self.eval_model)
            relevance_results = run_evals(
                dataframe=df,
                evaluators=[relevance_evaluator],
                provide_explanation=True
            )
            if 'relevance' in relevance_results.columns:
                scores['relevance'] = relevance_results['relevance'].mean()
            print(f"   Relevance: {scores.get('relevance', 'N/A')}")

        except Exception as e:
            print(f"   Relevance evaluation error: {e}")

        try:
            # 2. QA Correctness Evaluation
            print("Running QA Correctness evaluation...")
            qa_evaluator = QAEvaluator(self.eval_model)
            qa_results = run_evals(
                dataframe=df,
                evaluators=[qa_evaluator],
                provide_explanation=True
            )
            if 'qa_correctness' in qa_results.columns:
                scores['qa_correctness'] = qa_results['qa_correctness'].mean()
            print(f"   QA Correctness: {scores.get('qa_correctness', 'N/A')}")

        except Exception as e:
            print(f"   QA evaluation error: {e}")

        try:
            # 3. Hallucination Evaluation
            print("Running Hallucination evaluation...")
            hallucination_evaluator = HallucinationEvaluator(self.eval_model)
            hallucination_results = run_evals(
                dataframe=df,
                evaluators=[hallucination_evaluator],
                provide_explanation=True
            )
            if 'hallucination' in hallucination_results.columns:
                # Lower is better for hallucination
                scores['hallucination'] = hallucination_results['hallucination'].mean()
            print(f"   Hallucination: {scores.get('hallucination', 'N/A')}")

        except Exception as e:
            print(f"   Hallucination evaluation error: {e}")

        # Calculate overall score
        if scores:
            # For overall, we want high relevance/qa, low hallucination
            relevance = scores.get('relevance', 0) or 0
            qa = scores.get('qa_correctness', 0) or 0
            hallucination = scores.get('hallucination', 0) or 0

            # Invert hallucination (1 - hallucination) so higher is better
            scores['overall'] = (relevance + qa + (1 - hallucination)) / 3

        print()
        print("-" * 40)
        print("EVALUATION RESULTS")
        print("-" * 40)
        for metric, value in scores.items():
            if value is not None:
                print(f"  {metric.replace('_', ' ').title()}: {value:.3f}")
        print("-" * 40)
        print()

        return scores

    def _basic_evaluation(self) -> Dict:
        """Fallback basic evaluation without Phoenix"""
        print("Running basic evaluation...")
        print("-" * 40)

        total = len(self.results)
        answered = sum(1 for r in self.results if not str(r['answer']).startswith('Error'))
        has_context = sum(1 for r in self.results if len(r['contexts']) > 0)

        # Keyword matching
        keyword_matches = 0
        for r in self.results:
            gt_terms = r['ground_truth'].lower().split()
            answer_lower = r['answer'].lower()
            key_terms = [t for t in gt_terms if len(t) > 4]
            if key_terms:
                matches = sum(1 for t in key_terms if t in answer_lower)
                if matches / len(key_terms) > 0.3:
                    keyword_matches += 1

        scores = {
            'answer_rate': answered / total if total > 0 else 0,
            'context_retrieval_rate': has_context / total if total > 0 else 0,
            'keyword_match_rate': keyword_matches / total if total > 0 else 0,
        }
        scores['overall'] = sum(scores.values()) / len(scores)

        print(f"Answer Rate:            {scores['answer_rate']:.3f}")
        print(f"Context Retrieval Rate: {scores['context_retrieval_rate']:.3f}")
        print(f"Keyword Match Rate:     {scores['keyword_match_rate']:.3f}")
        print(f"-" * 40)
        print(f"Overall Score:          {scores['overall']:.3f}")
        print()

        return scores

    def generate_report(self, scores: Dict, output_path: str = None) -> Dict:
        """Generate evaluation report"""
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'evaluator': 'phoenix',
                'dataset': str(self.dataset_path),
                'test_cases': len(self.test_cases),
            },
            'scores': scores,
            'per_category': self._scores_by_category(),
            'detailed_results': [
                {
                    'id': r['id'],
                    'question': r['question'],
                    'answer': r['answer'][:200] + '...' if len(r['answer']) > 200 else r['answer'],
                    'ground_truth': r['ground_truth'],
                    'category': r['category'],
                    'num_contexts': len(r['contexts'])
                }
                for r in self.results
            ]
        }

        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to: {output_file}")

        return report

    def _scores_by_category(self) -> Dict:
        """Calculate scores by category"""
        categories = {}
        for r in self.results:
            cat = r['category']
            if cat not in categories:
                categories[cat] = {'count': 0, 'has_answer': 0, 'has_context': 0}

            categories[cat]['count'] += 1
            if not str(r['answer']).startswith('Error'):
                categories[cat]['has_answer'] += 1
            if len(r['contexts']) > 0:
                categories[cat]['has_context'] += 1

        for cat in categories:
            count = categories[cat]['count']
            categories[cat]['answer_rate'] = categories[cat]['has_answer'] / count
            categories[cat]['context_rate'] = categories[cat]['has_context'] / count

        return categories

    def print_summary(self):
        """Print evaluation summary"""
        print()
        print("=" * 60)
        print("  EVALUATION SUMMARY")
        print("=" * 60)
        print()

        print("Results by Category:")
        print("-" * 40)
        categories = self._scores_by_category()
        for cat, stats in categories.items():
            print(f"  {cat}:")
            print(f"    - Tests: {stats['count']}")
            print(f"    - Answer Rate: {stats['answer_rate']:.1%}")
            print(f"    - Context Rate: {stats['context_rate']:.1%}")
        print()

        print("Sample Results:")
        print("-" * 40)
        for r in self.results[:3]:
            print(f"Q: {r['question']}")
            print(f"A: {r['answer'][:100]}...")
            print(f"Contexts: {len(r['contexts'])} chunks retrieved")
            print()

        if PHOENIX_AVAILABLE:
            print("View detailed results in Phoenix UI:")
            print("   http://localhost:6006")
            print()

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Phoenix Evaluation for P&ID Assistant')
    parser.add_argument('--dataset', default='tests/eval_dataset.json',
                        help='Path to test dataset')
    parser.add_argument('--output', default='results/eval_phoenix_results.json',
                        help='Path to save results')
    parser.add_argument('--basic-only', action='store_true',
                        help='Run basic evaluation only (no Phoenix)')
    args = parser.parse_args()

    # Initialize evaluator
    evaluator = PhoenixEvaluator(dataset_path=args.dataset)

    # Load dataset
    if not evaluator.load_dataset():
        sys.exit(1)

    # Initialize RAG
    if not evaluator.initialize_rag():
        sys.exit(1)

    # Run queries
    evaluator.run_queries()

    # Evaluate
    if args.basic_only or not PHOENIX_AVAILABLE:
        scores = evaluator._basic_evaluation()
    else:
        scores = evaluator.evaluate_with_phoenix()

    # Generate report
    evaluator.generate_report(scores, output_path=args.output)

    # Print summary
    evaluator.print_summary()

    print()
    print("Evaluation complete!")
    print()


if __name__ == "__main__":
    main()

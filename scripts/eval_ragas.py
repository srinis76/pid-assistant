"""
RAGAS Evaluation Script for P&ID Assistant

Evaluates the RAG pipeline using RAGAS metrics:
- Faithfulness: Is the answer grounded in the context?
- Answer Relevancy: Is the answer relevant to the question?
- Context Precision: Are retrieved chunks relevant?
- Context Recall: Did we retrieve all needed information?

Usage:
    python scripts/eval_ragas.py
    python scripts/eval_ragas.py --output results/eval_results.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# RAGAS imports
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    print("Warning: RAGAS not installed. Run: pip install ragas datasets")

# Application imports
from app.rag_engine import RAGEngine


class RAGASEvaluator:
    """Evaluates RAG pipeline using RAGAS metrics"""

    def __init__(self, dataset_path: str = "tests/eval_dataset.json"):
        self.dataset_path = Path(dataset_path)
        self.rag_engine = None
        self.test_cases = []
        self.results = []

        print("=" * 60)
        print("  RAGAS Evaluation for P&ID Assistant")
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
        """Initialize RAG engine"""
        try:
            print("Initializing RAG Engine...")
            self.rag_engine = RAGEngine()
            return True
        except Exception as e:
            print(f"Error initializing RAG engine: {e}")
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

                # Extract contexts from retrieved chunks
                contexts = []
                if 'sources' in metadata:
                    for source in metadata['sources']:
                        # Get the chunk text from the search results
                        pass  # We need to modify this

                # Re-query to get full context
                query_embedding = self.rag_engine.generate_query_embedding(question)
                search_results = self.rag_engine.search_vector_db(query_embedding, top_k=3)
                contexts = [r['text'] for r in search_results]

                results.append({
                    'id': tc['id'],
                    'question': question,
                    'answer': answer,
                    'contexts': contexts,
                    'ground_truth': ground_truth,
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
                    'ground_truth': ground_truth,
                    'category': tc['category'],
                    'relevance_scores': []
                })

        print("-" * 40)
        print(f"Completed {len(results)} queries")
        print()

        self.results = results
        return results

    def evaluate_with_ragas(self) -> Dict:
        """Evaluate results using RAGAS metrics"""
        if not RAGAS_AVAILABLE:
            print("RAGAS not available. Returning basic metrics only.")
            return self._basic_evaluation()

        print("Evaluating with RAGAS...")
        print("-" * 40)

        # Prepare data for RAGAS
        data = {
            'question': [r['question'] for r in self.results],
            'answer': [r['answer'] for r in self.results],
            'contexts': [r['contexts'] for r in self.results],
            'ground_truth': [r['ground_truth'] for r in self.results]
        }

        dataset = Dataset.from_dict(data)

        # Run RAGAS evaluation
        try:
            eval_result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                ]
            )

            # Convert to dict
            scores = {
                'faithfulness': float(eval_result['faithfulness']),
                'answer_relevancy': float(eval_result['answer_relevancy']),
                'context_precision': float(eval_result['context_precision']),
                'context_recall': float(eval_result['context_recall']),
            }

            # Calculate overall score
            scores['overall'] = sum(scores.values()) / len(scores)

            print(f"Faithfulness:      {scores['faithfulness']:.3f}")
            print(f"Answer Relevancy:  {scores['answer_relevancy']:.3f}")
            print(f"Context Precision: {scores['context_precision']:.3f}")
            print(f"Context Recall:    {scores['context_recall']:.3f}")
            print(f"-" * 40)
            print(f"Overall Score:     {scores['overall']:.3f}")
            print()

            return scores

        except Exception as e:
            print(f"RAGAS evaluation error: {e}")
            print("Falling back to basic evaluation...")
            return self._basic_evaluation()

    def _basic_evaluation(self) -> Dict:
        """Basic evaluation without RAGAS"""
        print("Running basic evaluation...")
        print("-" * 40)

        # Simple metrics
        total = len(self.results)
        answered = sum(1 for r in self.results if not r['answer'].startswith('Error'))
        has_context = sum(1 for r in self.results if len(r['contexts']) > 0)

        # Check if ground truth terms appear in answer
        keyword_matches = 0
        for r in self.results:
            gt_terms = r['ground_truth'].lower().split()
            answer_lower = r['answer'].lower()
            # Check if key terms from ground truth appear in answer
            key_terms = [t for t in gt_terms if len(t) > 4]  # Skip short words
            if key_terms:
                matches = sum(1 for t in key_terms if t in answer_lower)
                if matches / len(key_terms) > 0.3:  # 30% threshold
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
                'dataset': str(self.dataset_path),
                'test_cases': len(self.test_cases),
                'rag_config': {
                    'embedding_model': self.rag_engine.embedding_model if self.rag_engine else 'unknown',
                    'top_k': 3
                }
            },
            'scores': scores,
            'per_category': self._scores_by_category(),
            'detailed_results': self.results
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
            if not r['answer'].startswith('Error'):
                categories[cat]['has_answer'] += 1
            if len(r['contexts']) > 0:
                categories[cat]['has_context'] += 1

        # Calculate rates
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

        # Per-category breakdown
        print("Results by Category:")
        print("-" * 40)
        categories = self._scores_by_category()
        for cat, stats in categories.items():
            print(f"  {cat}:")
            print(f"    - Tests: {stats['count']}")
            print(f"    - Answer Rate: {stats['answer_rate']:.1%}")
            print(f"    - Context Rate: {stats['context_rate']:.1%}")
        print()

        # Sample results
        print("Sample Results:")
        print("-" * 40)
        for r in self.results[:3]:
            print(f"Q: {r['question']}")
            print(f"A: {r['answer'][:100]}...")
            print(f"Contexts: {len(r['contexts'])} chunks retrieved")
            print()

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='RAGAS Evaluation for P&ID Assistant')
    parser.add_argument('--dataset', default='tests/eval_dataset.json',
                        help='Path to test dataset')
    parser.add_argument('--output', default='results/eval_results.json',
                        help='Path to save results')
    parser.add_argument('--basic-only', action='store_true',
                        help='Run basic evaluation only (no RAGAS)')
    args = parser.parse_args()

    # Initialize evaluator
    evaluator = RAGASEvaluator(dataset_path=args.dataset)

    # Load dataset
    if not evaluator.load_dataset():
        sys.exit(1)

    # Initialize RAG
    if not evaluator.initialize_rag():
        sys.exit(1)

    # Run queries
    evaluator.run_queries()

    # Evaluate
    if args.basic_only or not RAGAS_AVAILABLE:
        scores = evaluator._basic_evaluation()
    else:
        scores = evaluator.evaluate_with_ragas()

    # Generate report
    evaluator.generate_report(scores, output_path=args.output)

    # Print summary
    evaluator.print_summary()

    print()
    print("Evaluation complete!")
    print()


if __name__ == "__main__":
    main()
